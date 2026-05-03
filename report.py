import pandas as pd
from datetime import datetime

def get_color(score):
    if score >= 7:
        return "#2d6a4f", "#d8f3dc"    # verde oscuro, verde claro
    elif score >= 5:
        return "#b5700a", "#fff3cd"    # amarillo oscuro, amarillo claro
    else:
        return "#c1121f", "#ffe8e8"    # rojo oscuro, rojo claro

def get_label(score):
    if score >= 9:
        return "Postular inmediatamente"
    elif score >= 7:
        return "Vale la pena revisar"
    elif score >= 5:
        return "Revisar con criterio"
    else:
        return "Descarte"

def build_report(csv_path="results/jobs_scored.csv"):
    jobs = pd.read_csv(csv_path)
    jobs = jobs.sort_values("score", ascending=False).reset_index(drop=True)

    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
    total = len(jobs)
    buenos = len(jobs[jobs["score"] >= 7])

    cards_html = ""
    for _, row in jobs.iterrows():
        color_text, color_bg = get_color(row["score"])
        label = get_label(row["score"])
        empresa = row["company"] if pd.notna(row["company"]) else "Empresa no especificada"
        ubicacion = row["location"] if pd.notna(row["location"]) else ""
        reason = row["reason"] if pd.notna(row["reason"]) else ""

        cards_html += f"""
        <div class="card" style="border-left: 5px solid {color_text}; background: {color_bg}">
            <div class="card-header">
                <span class="score" style="background: {color_text}">{row["score"]}/10</span>
                <span class="label" style="color: {color_text}">{label}</span>
            </div>
            <h3>{row["title"]}</h3>
            <p class="empresa">{empresa} · {ubicacion}</p>
            <p class="reason">{reason}</p>
            <a href="{row["job_url"]}" target="_blank">Ver oferta →</a>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Job Scorer — Resultados</title>
    <style>
        body {{ font-family: -apple-system, sans-serif; max-width: 800px;
                margin: 40px auto; padding: 0 20px; background: #f8f9fa; }}
        h1 {{ color: #1a1a2e; }}
        .meta {{ color: #666; margin-bottom: 30px; }}
        .card {{ background: white; border-radius: 8px; padding: 20px;
                 margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        .card-header {{ display: flex; align-items: center; gap: 12px;
                        margin-bottom: 8px; }}
        .score {{ color: white; padding: 4px 10px; border-radius: 20px;
                  font-weight: bold; font-size: 14px; }}
        .label {{ font-size: 13px; font-weight: 600; }}
        h3 {{ margin: 0 0 4px 0; color: #1a1a2e; font-size: 16px; }}
        .empresa {{ color: #555; font-size: 14px; margin: 0 0 8px 0; }}
        .reason {{ color: #444; font-size: 14px; margin: 0 0 12px 0;
                   font-style: italic; }}
        a {{ color: #2563eb; text-decoration: none; font-size: 14px;
             font-weight: 500; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <h1>Job Scorer</h1>
    <p class="meta">Generado el {fecha} · {total} ofertas analizadas · 
       <strong>{buenos} con score ≥ 7</strong></p>
    {cards_html}
</body>
</html>"""

    output_path = "results/report.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Reporte generado: {output_path}")
    print(f"Abrilo en tu browser para ver los resultados")

if __name__ == "__main__":
    build_report()