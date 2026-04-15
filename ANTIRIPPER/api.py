from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from agent_oracle import AgentOracle
import uvicorn
import sqlite3

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "antiripper_v2.db"

def fetch_all(table: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM {table}")
    data = [dict(row) for row in cur.fetchall()]
    conn.close()
    return data

@app.get("/api/dashboard")
def get_dashboard_summary():
    return {
        "driver_families": fetch_all("driver_families"),
        "apu_facts": fetch_all("hardware_facts"),
        "blunders": fetch_all("prevention_patterns")
    }

@app.get("/api/games")
def get_games_status():
    # Fetch evidence and claims, grouped by game_slug theoretically.
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # We derive the game list distinctly from evidence_items and decision_records
    cur.execute("SELECT DISTINCT game_slug FROM evidence_items UNION SELECT DISTINCT game_slug FROM decision_records")
    slugs = [row['game_slug'] for row in cur.fetchall()]
    
    games = []
    for slug in slugs:
        cur.execute("SELECT type, source_path, created_at FROM evidence_items WHERE game_slug = ?", (slug,))
        evidence = [dict(r) for r in cur.fetchall()]
        
        cur.execute("SELECT statement, status, confidence FROM claims WHERE subject_id = ? AND subject_type = 'game'", (slug,))
        claims = [dict(r) for r in cur.fetchall()]
        
        games.append({
            "slug": slug,
            "evidence_count": len(evidence),
            "claims": claims,
            "validation_level": "High" if len(evidence) > 1 else "Pending"
        })
        
    conn.close()
    return games

@app.get("/api/drivers")
def get_drivers():
    return fetch_all("driver_families")

@app.get("/api/agent-logs")
def get_agent_logs():
    return {
        "claims": fetch_all("claims"),
        "decisions": fetch_all("decision_records"),
        "prevention_patterns": fetch_all("prevention_patterns")
    }

if __name__ == "__main__":
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
