import sqlite3

conn = sqlite3.connect("data/jobs_cache.db")
cursor = conn.cursor()
cursor.execute("DELETE FROM jobs_history WHERE date_scored LIKE '2026-05-09%'")
print("Registros eliminados:", cursor.rowcount)
conn.commit()
conn.close()