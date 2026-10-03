import csv
import io
import json
import os
import sqlite3
from contextlib import asynccontextmanager
from datetime import date as date_cls
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import db
from .pricing import RateCard, compute_payment

STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")


@asynccontextmanager
async def lifespan(_app):
    db.init_db()
    yield


app = FastAPI(title="Smart Dairy - Quality-Based Milk Pricing", lifespan=lifespan)


# ---------- schemas ----------
class FarmerIn(BaseModel):
    name: str = Field(min_length=1)
    phone: Optional[str] = None
    village: Optional[str] = None


class ReadingIn(BaseModel):
    litres: float
    fat: float
    snf: float


class EntryIn(ReadingIn):
    farmer_id: int
    entry_date: date_cls
    session: Literal["morning", "evening"]


class RateCardIn(BaseModel):
    fat_rate: float = Field(ge=0)
    snf_rate: float = Field(ge=0)
    density: float = Field(gt=0)
    min_snf: float = Field(ge=0)
    snf_penalty_per_point: float = Field(ge=0)
    premium_fat: float = Field(ge=0)
    fat_bonus_per_point: float = Field(ge=0)
    flat_rate_per_litre: float = Field(ge=0)


def _calc(r: ReadingIn, rc: RateCard) -> dict:
    try:
        return compute_payment(r.litres, r.fat, r.snf, rc)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


# ---------- rate card ----------
@app.get("/api/rate-card")
def get_rate_card():
    return db.load_rate_card().to_dict()


@app.put("/api/rate-card")
def put_rate_card(body: RateCardIn):
    rc = RateCard(**body.model_dump())
    db.save_rate_card(rc)
    return rc.to_dict()


# ---------- calculator (no saving) ----------
@app.post("/api/calculate")
def calculate(body: ReadingIn):
    return _calc(body, db.load_rate_card())


# ---------- farmers ----------
@app.post("/api/farmers", status_code=201)
def add_farmer(body: FarmerIn):
    conn = db.get_conn()
    cur = conn.execute("INSERT INTO farmers (name, phone, village) VALUES (?,?,?)",
                       (body.name.strip(), body.phone, body.village))
    conn.commit()
    fid = cur.lastrowid
    conn.close()
    return {"id": fid, **body.model_dump()}


@app.get("/api/farmers")
def list_farmers():
    conn = db.get_conn()
    rows = [dict(r) for r in conn.execute("SELECT * FROM farmers ORDER BY name")]
    conn.close()
    return rows


@app.delete("/api/farmers/{farmer_id}", status_code=204)
def delete_farmer(farmer_id: int):
    conn = db.get_conn()
    conn.execute("DELETE FROM farmers WHERE id = ?", (farmer_id,))
    conn.commit()
    conn.close()


# ---------- entries ----------
@app.post("/api/entries", status_code=201)
def add_entry(body: EntryIn):
    conn = db.get_conn()
    if conn.execute("SELECT 1 FROM farmers WHERE id = ?", (body.farmer_id,)).fetchone() is None:
        conn.close()
        raise HTTPException(404, "Farmer not found")
    result = _calc(body, db.load_rate_card())  # rates at time of entry are frozen into the record
    try:
        cur = conn.execute(
            "INSERT INTO entries (farmer_id, entry_date, session, litres, fat, snf, total, breakdown)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (body.farmer_id, body.entry_date.isoformat(), body.session,
             body.litres, body.fat, body.snf, result["total"], json.dumps(result)),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(409, "An entry already exists for this farmer, date and session")
    eid = cur.lastrowid
    conn.close()
    return {"id": eid, **result}


def _entry_rows(farmer_id: Optional[int], month: Optional[str]):
    q = ("SELECT e.*, f.name AS farmer_name FROM entries e "
         "JOIN farmers f ON f.id = e.farmer_id WHERE 1=1")
    args = []
    if farmer_id:
        q += " AND e.farmer_id = ?"
        args.append(farmer_id)
    if month:
        q += " AND substr(e.entry_date,1,7) = ?"
        args.append(month)
    q += " ORDER BY e.entry_date DESC, e.session"
    conn = db.get_conn()
    rows = [dict(r) for r in conn.execute(q, args)]
    conn.close()
    for r in rows:
        r["breakdown"] = json.loads(r["breakdown"])
    return rows


@app.get("/api/entries")
def list_entries(farmer_id: Optional[int] = None,
                 month: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}$")):
    return _entry_rows(farmer_id, month)


@app.delete("/api/entries/{entry_id}", status_code=204)
def delete_entry(entry_id: int):
    conn = db.get_conn()
    conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()


# ---------- summary / export ----------
@app.get("/api/summary")
def summary(farmer_id: int, month: str = Query(..., pattern=r"^\d{4}-\d{2}$")):
    rows = _entry_rows(farmer_id, month)
    litres = sum(r["litres"] for r in rows)
    total = sum(r["total"] for r in rows)
    quantity_only = sum(r["breakdown"]["quantity_only_total"] for r in rows)
    daily = {}
    for r in rows:
        d = daily.setdefault(r["entry_date"], {"date": r["entry_date"], "litres": 0.0, "total": 0.0})
        d["litres"] += r["litres"]
        d["total"] += r["total"]
    return {
        "farmer_id": farmer_id,
        "month": month,
        "entries": len(rows),
        "total_litres": round(litres, 2),
        "avg_fat": round(sum(r["fat"] * r["litres"] for r in rows) / litres, 2) if litres else 0,
        "avg_snf": round(sum(r["snf"] * r["litres"] for r in rows) / litres, 2) if litres else 0,
        "total_amount": round(total, 2),
        "avg_rate_per_litre": round(total / litres, 2) if litres else 0,
        "quantity_only_amount": round(quantity_only, 2),
        "quality_gain": round(total - quantity_only, 2),
        "daily": [{**d, "litres": round(d["litres"], 2), "total": round(d["total"], 2)}
                  for d in sorted(daily.values(), key=lambda x: x["date"])],
    }


@app.get("/api/export.csv")
def export_csv(farmer_id: Optional[int] = None,
               month: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}$")):
    rows = _entry_rows(farmer_id, month)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["date", "session", "farmer", "litres", "fat_pct", "snf_pct", "fat_amount",
                "snf_amount", "snf_penalty", "fat_bonus", "total", "rate_per_litre"])
    for r in rows:
        b = r["breakdown"]
        w.writerow([r["entry_date"], r["session"], r["farmer_name"], r["litres"], r["fat"], r["snf"],
                    b["fat_amount"], b["snf_amount"], b["snf_penalty"], b["fat_bonus"],
                    r["total"], b["rate_per_litre"]])
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=milk_entries.csv"})


# ---------- frontend ----------
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))
