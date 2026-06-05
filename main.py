from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
from bs4 import BeautifulSoup
import sqlite3
import re
import json
import os
import traceback

app = FastAPI()
DB_PATH = "combined.db"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CACHE_FILE = "classement_cache.json"

def save_json(data, path=CACHE_FILE):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_json(path=CACHE_FILE):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def parse_performance(perf_str):
    perf_str = str(perf_str).strip().replace(",", ".")
    match = re.match(r"(?:(\d+):)?(\d+)(?:\.(\d+))?", perf_str)
    if match:
        minutes = int(match.group(1)) if match.group(1) else 0
        secondes = int(match.group(2))
        fraction = float("0." + match.group(3)) if match.group(3) else 0.0
        return minutes * 60 + secondes + fraction
    try:
        return float(perf_str)
    except ValueError:
        return None

def get_perf_points(table_name, event, perf_str, db_path="combined.db"):
    perf = parse_performance(perf_str)
    if perf is None:
        return None
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(f"SELECT `{event}`, Points FROM {table_name}")
    rows = cursor.fetchall()
    conn.close()
    valid_rows = []
    for p_str, pts in rows:
        p_val = parse_performance(str(p_str))
        if p_val is not None:
            valid_rows.append((p_val, pts))
    valid_rows.sort(key=lambda x: x[0])
    for i, (p_val, pts) in enumerate(valid_rows):
        if perf == p_val:
            return pts
        if perf < p_val:
            return valid_rows[i][1]
    if valid_rows:
        return valid_rows[-1][1]
    return None

def perf_ms_to_str(ms):
    """Convertit 112680 -> '1:52.68'"""
    total_s = ms / 1000
    minutes = int(total_s // 60)
    secondes = total_s % 60
    if minutes > 0:
        return f"{minutes}:{secondes:05.2f}"
    else:
        return f"{secondes:.2f}"

def scrape_epreuve(epreuve: str):
    print(f"Scraping {epreuve}...")
    
    # Mapping nom fichier -> nom API
    discipline_map = {
        "800m": "800 mètres",
        "1500m": "1500 mètres"
    }
    discipline = discipline_map.get(epreuve, epreuve)
    
    url = "https://www.beathletics.be/api/results/ranking"
    params = {
        "season": "2025 - 2026",
        "venue": "O",
        "discipline": discipline,
        "category": "SCO M"
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": "https://www.beathletics.be/rankings",
    }
    
    try:
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            r = client.get(url, params=params, headers=headers)
        r.raise_for_status()
        results = r.json()
    except Exception as e:
        print(f"[ERREUR] {epreuve} : {e}")
        return []

    data = []
    for row in results[:30]:
        perf_str = perf_ms_to_str(row["perf"])
        # Nom : "Longo-Murit, Mateo" -> "Mateo Longo-Murit"
        nom_parts = row["athlete"].split(", ")
        athlete = f"{nom_parts[1]} {nom_parts[0]}" if len(nom_parts) == 2 else row["athlete"]
        
        date_str = row.get("date", "")[:10]  # "2026-05-01T22:00:00.000Z" -> "2026-05-01"

        data.append({
            "epreuve": epreuve,
            "prestation": perf_str,
            "athlete": athlete,
            "club": row.get("club", ""),
            "annee_naissance": "",  # pas dans l'API
            "date": date_str,
            "lieu": row.get("place", ""),
            "points": get_perf_points("performances_men", epreuve, perf_str)
        })

    print(f"[OK] {len(data)} résultats pour {epreuve}")
    return data

@app.get("/YouthMemorialDemiFond")
def get_classement_commun(update: bool = Query(False)):
    try:
        if not update:
            cached_data = load_json()
            if cached_data is not None:
                return JSONResponse(content=cached_data)
            return JSONResponse(
                content={"error": "Aucune donnée en cache. Veuillez lancer une mise à jour."},
                status_code=404
            )

        data_800m = scrape_epreuve("800m")
        data_1500m = scrape_epreuve("1500m")
        combined = data_800m + data_1500m

        seen = {}
        for row in combined:
            nom = row["athlete"]
            pts = row["points"]
            if pts is None:
                continue
            if nom not in seen or int(pts) > int(seen[nom]["points"]):
                seen[nom] = row

        classement_unique = list(seen.values())
        classement_unique.sort(key=lambda x: int(x["points"]), reverse=True)
        save_json(classement_unique)
        return JSONResponse(content=classement_unique)

    except Exception as e:
        print(traceback.format_exc())
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/get_events")
def get_events(event_type: str, event_cat: str, gender: str):
    table_name = f"performances_{'men' if gender == 'men' else 'women'}"
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    perf_columns = [col[1] for col in columns if col[1].lower() != "points"]
    cursor.execute("""
        SELECT nom_db, nom_display FROM MAP
        WHERE lieu = ? AND cat = ?
        ORDER BY priorite
    """, (event_type, event_cat))
    mapping_entries = cursor.fetchall()
    conn.close()
    return [
        {"nom_db": nom_db, "nom_display": nom_display}
        for nom_db, nom_display in mapping_entries
        if nom_db in perf_columns
    ]


class FromPointsRequest(BaseModel):
    gender: str
    event: str
    points: int

@app.post("/FromPoints")
async def from_points(data: FromPointsRequest):
    gender = data.gender.lower()
    if gender not in ("men", "women"):
        return JSONResponse(status_code=400, content={"error": "Gender must be 'men' or 'women'."})
    table_name = f"performances_{gender}"
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT nom_display FROM MAP WHERE nom_db = ?", (data.event,))
        row = cursor.fetchone()
        display_name = row[0] if row else data.event
        performance = None
        current_points = data.points
        while current_points <= 1400:
            cursor.execute(f"SELECT `{data.event}` FROM {table_name} WHERE Points = ?", (current_points,))
            result = cursor.fetchone()
            if result and result[0]:
                performance = result[0]
                break
            current_points += 1
        conn.close()
        if performance:
            return {"performance": performance, "event_display_name": display_name}
        return {"performance": "No data", "event_display_name": display_name}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


class FromPerfRequest(BaseModel):
    gender: str
    event: str
    perf: str

@app.post("/FromPerf")
async def from_perf(data: FromPerfRequest):
    try:
        gender = data.gender.lower()
        if gender not in ("men", "women"):
            return JSONResponse(status_code=400, content={"error": "Gender must be 'men' or 'women'."})
        table_name = f"performances_{gender}"
        points = get_perf_points(table_name, data.event, data.perf)
        if points is not None:
            return {"points": points}
        return {"points": "No data"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
