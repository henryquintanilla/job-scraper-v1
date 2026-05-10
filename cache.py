import sqlite3
import pandas as pd
from datetime import datetime
import os

DB_PATH = "data/jobs_cache.db"

def init_db():
    """Crea la base de datos y tabla si no existen"""
    os.makedirs("data", exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs_history (
            job_url TEXT PRIMARY KEY,
            title TEXT,
            company TEXT,
            location TEXT,
            site TEXT,
            score INTEGER,
            reason TEXT,
            categoria TEXT,
            dimensiones TEXT,
            date_scored TEXT

        )
    """)
    
    conn.commit()
    conn.close()
    print(f"Base de datos inicializada en {DB_PATH}")


def get_known_urls():
    """Devuelve todas las URLs ya procesadas"""
    if not os.path.exists(DB_PATH):
        return set()
    
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT job_url FROM jobs_history", conn)
    conn.close()
    
    return set(df["job_url"].tolist())


def filter_new_jobs(df):
    """Filtra el DataFrame y devuelve solo ofertas no vistas antes"""
    known_urls = get_known_urls()
    
    df_new = df[~df["job_url"].isin(known_urls)].copy()
    df_known = df[df["job_url"].isin(known_urls)].copy()
    
    print(f"Ofertas ya vistas: {len(df_known)}")
    print(f"Ofertas nuevas: {len(df_new)}")
    
    return df_new


def save_scored_jobs(df_scored):
    """Guarda las ofertas scoreadas en el historial"""
    conn = sqlite3.connect(DB_PATH)
    
    records = []
    for _, row in df_scored.iterrows():
        records.append({
            "job_url": row["job_url"],
            "title": row["title"],
            "company": row.get("company", None),
            "location": row.get("location", None),
            "site": row.get("site", None),
            "score": row.get("score", None),
            "reason": row.get("reason", None),
            "categoria": row.get("categoria", None),
            "dimensiones": row.get("dimensiones", None),
            "date_scored": datetime.now().strftime("%Y-%m-%d %H:%M")
        })
    
    df_records = pd.DataFrame(records)
    
    # INSERT OR IGNORE — si la URL ya existe no la sobreescribe
    df_records.to_sql("jobs_history", conn, if_exists="append", index=False,
                      method="multi")
    
    conn.close()
    print(f"Guardadas {len(records)} ofertas en el historial")


def get_history():
    """Devuelve todo el historial ordenado por score"""
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()
    
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql(
        "SELECT * FROM jobs_history ORDER BY score DESC, date_scored DESC",
        conn
    )
    conn.close()
    return df


if __name__ == "__main__":
    init_db()
    print("Historial actual:")
    df = get_history()
    if len(df) > 0:
        print(df[["title", "company", "score", "date_scored"]].to_string())
    else:
        print("Vacío — primera corrida")