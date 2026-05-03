import pandas as pd
from scorer import score_job
from cache import filter_new_jobs, save_scored_jobs, get_history
import time

start_time = time.time()

USE_OLLAMA = False

# Cargar ofertas con descripción
jobs = pd.read_csv("results/jobs_raw.csv")
print(f"Ofertas totales: {len(jobs)}")

# Filtrar solo las nuevas
print("\nVerificando cache...")
jobs_new = filter_new_jobs(jobs)

if len(jobs_new) == 0:
    print("\nNo hay ofertas nuevas para scorear.")
    print("Generando reporte con historial existente...")
else:
    print(f"\nScoreando {len(jobs_new)} ofertas nuevas...\n")
    
    scores = []
    reasons = []

    for i, row in jobs_new.iterrows():
        print(f"[{i+1}/{len(jobs_new)}] {row['title']} @ {row['company']}")
        resultado = score_job(row["description"], use_ollama=USE_OLLAMA)
        scores.append(resultado["score"])
        reasons.append(resultado["reason"])

    jobs_new["score"] = scores
    jobs_new["reason"] = reasons

    # Guardar en cache
    save_scored_jobs(jobs_new)

# Cargar historial completo para el reporte
history = get_history()
history.to_csv("results/jobs_scored.csv", index=False)

# Resumen
jobs_buenos = history[history["score"] > 5]
print(f"\nOfertas con score > 5 (historial completo): {len(jobs_buenos)}")

print("\n=== TOP 5 OFERTAS ===")
for i, row in jobs_buenos.head(5).iterrows():
    print(f"\n#{i+1} [{row['score']}/10] {row['title']} @ {row['company']}")
    print(f"     {row['reason']}")
    print(f"     {row['job_url']}")

elapsed = time.time() - start_time
minutos = int(elapsed // 60)
segundos = int(elapsed % 60)
print(f"\nTiempo de ejecución: {minutos}m {segundos}s")
print(f"\nResultados completos guardados en results/jobs_scored.csv")