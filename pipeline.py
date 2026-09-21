import pandas as pd
from scorer import score_job, get_score_simple, get_reason_simple, pre_score, fit_cv
from cache import filter_new_jobs, save_scored_jobs, get_history
import time
import json

start_time = time.time()

USE_OLLAMA = False

jobs = pd.read_csv("results/jobs_raw.csv")
print(f"Ofertas totales: {len(jobs)}")

print("\nVerificando cache...")
jobs_new = filter_new_jobs(jobs)

if len(jobs_new) == 0:
    print("\nNo hay ofertas nuevas para scorear.")
else:
    print(f"\nScoreando {len(jobs_new)} ofertas nuevas...\n")

    scores = []
    reasons = []
    categorias = []
    dimensiones_raw = []
    cv_fit_raw = []
    descartes_rapidos = 0

    for contador, (i, row) in enumerate(jobs_new.iterrows(), start=1):
        print(f"[{contador}/{len(jobs_new)}] {row['title']} @ {row['company']}")

        # Fase 1 — pre-score rápido
        pasa, fit, adj = pre_score(row["description"], use_ollama=USE_OLLAMA)

        if not pasa:
            print(f"  → Descarte rápido (fit_negocio={fit}, adyacencia={adj})")
            scores.append(2)
            reasons.append(f"Descarte fase 1: fit_negocio={fit}, adyacencia={adj}.")
            categorias.append("DESCARTAR")
            dimensiones_raw.append(None)
            cv_fit_raw.append(None)
            descartes_rapidos += 1
            continue

        # Fase 2 — scoring completo
        resultado = score_job(row["description"], use_ollama=USE_OLLAMA)
        scores.append(get_score_simple(resultado))
        reasons.append(get_reason_simple(resultado))
        categorias.append(resultado.get("categoria", ""))
        dimensiones_raw.append(json.dumps(resultado, ensure_ascii=False))

        # Fase 3 — CV fit (solo para score >= 7)
        score_actual = get_score_simple(resultado)
        if score_actual >= 7:
            cv_result = fit_cv(row["description"], row["title"], str(row.get("company", "")))
            cv_fit_raw.append(json.dumps(cv_result, ensure_ascii=False))
            cv_rec = cv_result.get("cv_recomendado", "?")
            print(f"  → CV fit: CV {cv_rec} ({cv_result.get('confianza', '')})")
        else:
            cv_fit_raw.append(None)

    print(f"\nDescartes rápidos (fase 1): {descartes_rapidos}")
    print(f"Scorings completos (fase 2): {len(jobs_new) - descartes_rapidos}")

    jobs_new["score"] = scores
    jobs_new["reason"] = reasons
    jobs_new["categoria"] = categorias
    jobs_new["dimensiones"] = dimensiones_raw
    jobs_new["cv_fit"] = cv_fit_raw

    save_scored_jobs(jobs_new)

history = get_history()
history.to_csv("results/jobs_scored.csv", index=False)

jobs_buenos = history[history["score"] > 5]
print(f"\nOfertas con score > 5 (historial completo): {len(jobs_buenos)}")

print("\n=== TOP 5 OFERTAS ===")
for i, row in jobs_buenos.head(5).iterrows():
    print(f"\n#{i+1} [{row['score']}/10] {row['title']} @ {row['company']}")
    print(f"     {row.get('categoria', '')} | {row['reason']}")
    print(f"     {row['job_url']}")

elapsed = time.time() - start_time
minutos = int(elapsed // 60)
segundos = int(elapsed % 60)
print(f"\nTiempo de ejecución: {minutos}m {segundos}s")
print(f"\nResultados completos guardados en results/jobs_scored.csv")