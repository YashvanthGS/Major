"""Optional: fills the database with demo farmers and a week of entries.  Run:  python seed_demo.py"""
import random
from datetime import date, timedelta
from app import db
from app.pricing import compute_payment
import json

db.init_db()
conn = db.get_conn()
rc = db.load_rate_card()
farmers = [("Ramesh", "Hunsur"), ("Lakshmi", "Mysuru"), ("Suresh", "Nanjangud")]
ids = [conn.execute("INSERT INTO farmers (name, village) VALUES (?,?)", f).lastrowid for f in farmers]
random.seed(1)
for fid, (lo, hi) in zip(ids, [(3.2, 8.2), (4.2, 8.7), (5.0, 9.0)]):
    for d in range(7):
        day = (date.today() - timedelta(days=d)).isoformat()
        for ses in ("morning", "evening"):
            litres = round(random.uniform(6, 14), 1)
            fat = round(lo + random.uniform(-0.2, 0.3), 1)
            snf = round(hi + random.uniform(-0.2, 0.2), 1)
            r = compute_payment(litres, fat, snf, rc)
            conn.execute("INSERT OR IGNORE INTO entries (farmer_id, entry_date, session, litres, fat, snf, total, breakdown) VALUES (?,?,?,?,?,?,?,?)",
                         (fid, day, ses, litres, fat, snf, r["total"], json.dumps(r)))
conn.commit()
print("Demo data added.")
