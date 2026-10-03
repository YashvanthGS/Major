# Smart Dairy – Quality-Based Milk Pricing

Implements **Enhancement 1 (Pricing Based on Milk Quality)** from the paper.
Payment is computed from milk **quantity and quality** (FAT and SNF), so better milk earns more.

## Setup and Run

Requires Python 3.9+.

### 1) Clone or open the project
```bash
cd E:\Major_Pro\Major
```

### 2) Create a virtual environment

#### Windows (PowerShell)
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

#### Linux / macOS
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3) Install dependencies
```bash
pip install -r requirements.txt
```

### 4) Start the app

#### Windows
```powershell
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

#### Linux / macOS
```bash
uvicorn app.main:app --reload
```

#### Quick script option
```bash
./run.sh
```
On Windows, you can also double-click `run.bat`.

Then open: http://127.0.0.1:8000

### 5) Optional commands
```bash
python seed_demo.py
python -m pytest -v
```

## Run

**Linux / macOS:** `./run.sh`  
**Windows:** double-click `run.bat`  
Then open <http://127.0.0.1:8000>.

Manual: `python -m venv venv`, activate it, `pip install -r requirements.txt`, `uvicorn app.main:app --reload`.

## Formula

```
weight_kg = litres × density (1.03)
fat_kg    = weight_kg × FAT% / 100
snf_kg    = weight_kg × SNF% / 100
base      = fat_kg × fat_rate + snf_kg × snf_rate
SNF penalty = (min_snf − SNF) × penalty_per_point × litres      (only if SNF < min_snf)
Fat bonus   = (FAT − premium_fat) × bonus_per_point × litres    (only if FAT > premium_fat)
total = base − penalty + bonus
```

The `quantity_only_total` (litres × flat rate) is also shown so you can demonstrate the gain from quality-based pricing.

## Features
- Live price calculator with a quality comparison table
- Farmers, and morning/evening session entries (one per farmer/date/session)
- Rates are frozen into each entry, so changing the rate card never alters past payments
- Monthly summary per farmer (weighted FAT/SNF, average rate, quality gain) and CSV export
- Editable rate card

## Structure
```
app/pricing.py   pricing logic (pure functions)
app/db.py        SQLite storage
app/main.py      FastAPI REST API (docs at /docs)
static/          web UI (HTML/CSS/JS, no build step)
tests/           pytest unit + API tests
```

## Important
The default rates, `min_snf` and `premium_fat` are **placeholder values for demonstration**.
Replace them with your dairy's or cooperative's real rate card (e.g. from Karnataka Milk Federation / the local
society) and cite that source in your report. FAT and SNF values are typed in from collection-centre readings;
the app does not measure them (as stated in your paper's scope).

## API
`GET/PUT /api/rate-card`, `POST /api/calculate`, `GET/POST/DELETE /api/farmers`,
`GET/POST/DELETE /api/entries`, `GET /api/summary?farmer_id=&month=YYYY-MM`, `GET /api/export.csv`.
