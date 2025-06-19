# -*- coding: utf-8 -*-
"""
Created on Wed Jun 11 10:22:33 2025

@author: Thomas
"""

from fastapi import FastAPI, Request
from fastapi import Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from selenium import webdriver
from pydantic import BaseModel
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import undetected_chromedriver as uc
import sqlite3
import re
import time
import json
import os
import traceback
import shutil
import subprocess


app = FastAPI()

DB_PATH="combined.db"

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

def check_chrome():
    result = subprocess.run(["which", "google-chrome"], capture_output=True, text=True)
    print(f"[DEBUG] Résultat which google-chrome : {result.stdout.strip()}")

    try:
        version = subprocess.run(["google-chrome", "--version"], capture_output=True, text=True)
        print(f"[DEBUG] Version Google Chrome : {version.stdout.strip()}")
    except Exception as e:
        print(f"[DEBUG] Impossible de lire la version de Chrome : {e}")


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
            if i == 0:
                return pts
            else:
                return valid_rows[i][1]
    if valid_rows:
        return valid_rows[-1][1]
    return None



def scrape_epreuve(epreuve: str):
    print(f"Démarrage Scrap pour {epreuve}")

    options = uc.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    
    options.binary_location = "/usr/bin/google-chrome"
    print(f"[DEBUG] Chrome binary set to: {options.binary_location}")

    check_chrome()

    driver = uc.Chrome(options=options)

    url = f"https://www.atletiek.nu/ranglijst/belgische-ranglijst/2025/outdoor/scholieren-jongens/{epreuve}/"
    driver.get(url)
    print("Page Chargé")
    wait = WebDriverWait(driver, 60)

    try:
        lang_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn.btn-success[data-dismiss='modal']")))
        lang_button.click()
        print("Language ok")
    except Exception as e:
        print(f"Problème Langue {e}")
        pass

    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(3)

    try:
        table = wait.until(EC.presence_of_element_located((By.ID, "ranglijstDeelnemers_1")))
        print("[INFO] Table de classement détectée")
    except Exception as e:
        print("[ERROR] Table non trouvée (headless) :", str(e))
        driver.save_screenshot(f"headless_error_{epreuve}.png")  # Voir ce que Selenium voit
        raise

    #table = wait.until(EC.presence_of_element_located((By.ID, "ranglijstDeelnemers_1")))
    rows = table.find_elements(By.TAG_NAME, "tr")
    data = []

    for row in rows[:30]:
        cells = row.find_elements(By.TAG_NAME, "td")
        if len(cells) >= 5:
            try:
                prestatie = cells[1].find_element(By.TAG_NAME, "a").text.strip()
            except:
                prestatie = cells[1].text.strip()
            full_atleet = cells[2].text.strip().split('\n')
            atleet = full_atleet[0]
            club = full_atleet[1] if len(full_atleet) > 1 else ''
            geboortejaar = cells[3].text.strip()
            date_lieu = cells[4].text.strip().split('\n')
            datum = date_lieu[0]
            lieu = date_lieu[1] if len(date_lieu) > 1 else ''
            points = get_perf_points("performances_men", epreuve, prestatie)

            data.append({
                "epreuve": epreuve,
                "prestation": prestatie,
                "athlete": atleet,
                "club": club,
                "annee_naissance": geboortejaar,
                "date": datum,
                "lieu": lieu,
                "points": points
            })
    driver.quit()
    return data

@app.get("/YouthMemorialDemiFond")
def get_classement_commun(update: bool = Query(False)):
    try:
        if not update:
            cached_data = load_json()
            if cached_data is not None:
                return JSONResponse(content=cached_data)
            else: return JSONResponse(
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

        save_json(classement_unique)  # Enregistrement dans le cache

        return JSONResponse(content=classement_unique)

    except Exception as e:
        tb = traceback.format_exc()
        print(tb) 
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
        SELECT nom_db, nom_display
        FROM MAP
        WHERE lieu = ? AND cat = ?
        ORDER BY priorite
    """, (event_type, event_cat))
    events = cursor.fetchall()
    mapping_entries = cursor.fetchall()
    conn.close()

    return [
        {"nom_db": nom_db, "nom_display": nom_display}
        for nom_db, nom_display in mapping_entries
        if nom_db in perf_columns
    ]


@app.post("/FromPoints")
async def from_points(request: Request):
    data = await request.json()
    gender = data.get("gender")
    event = data.get("event")
    points = data.get("points")

    if gender not in ("men", "women"):
        return {"error": "Invalid gender, must be 'men' or 'women'"}

    table_name = f"performances_{gender}"
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [col[1] for col in cursor.fetchall()]
        if event not in columns:
            return {"error": f"Event '{event}' not found in table {table_name}"}

        cursor.execute(f"SELECT `{event}` FROM {table_name} WHERE Points = ?", (points,))
        result = cursor.fetchone()

        performance = result[0] if result else "No data, points are between 1 and 1400"
    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()

    return {"performance": performance}
