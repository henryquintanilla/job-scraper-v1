import pandas as pd
from scorer import score_job
import time  # al inicio del archivo, junto a los otros imports

# Justo después de cargar el CSV
start_time = time.time()

USE_OLLAMA = False  # Cambiá a True para usar Ollama local

# Cargar las ofertas scrapeadas
jobs = pd.read_csv("results/jobs_filtered.csv")
print(f"Cargando {len(jobs)} ofertas para scorear...\n")

# Aplicar el scorer a cada oferta
scores = []
reasons = []

for i, row in jobs.iterrows():
    print(f"[{i+1}/{len(jobs)}] Scoreando: {row['title']} @ {row['company']}")
    
    resultado = score_job(row["description"], use_ollama=USE_OLLAMA)
    scores.append(resultado["score"])
    reasons.append(resultado["reason"])

# Agregar columnas al DataFrame
jobs["score"] = scores
jobs["reason"] = reasons

# Ordenar por score descendente
jobs_scored = jobs.sort_values("score", ascending=False).reset_index(drop=True)

# Guardar
jobs_scored.to_csv("results/jobs_scored.csv", index=False)

# Resumen en consola
# Filtrar solo ofertas con score mayor a 5
jobs_buenos = jobs_scored[jobs_scored["score"] > 5]
print(f"\nOfertas con score > 5: {len(jobs_buenos)}")

print("\n=== TOP 5 OFERTAS ===")
for i, row in jobs_buenos.head(5).iterrows():
    print(f"\n#{i+1} [{row['score']}/10] {row['title']} @ {row['company']}")
    print(f"     {row['location']} | {row['reason']}")
    print(f"     {row['job_url']}")



# Al final, antes del último print
elapsed = time.time() - start_time
minutos = int(elapsed // 60)
segundos = int(elapsed % 60)
print(f"\nTiempo de ejecución: {minutos}m {segundos}s")

print(f"\nResultados completos guardados en results/jobs_scored.csv")