import pandas as pd
import json
from datetime import datetime


def get_color(score):
    if score >= 7:
        return "#2d6a4f", "#d8f3dc"
    elif score >= 5:
        return "#b5700a", "#fff3cd"
    else:
        return "#c1121f", "#ffe8e8"


def get_label(score):
    if score >= 9:
        return "Postular inmediatamente"
    elif score >= 7:
        return "Vale la pena revisar"
    elif score >= 5:
        return "Revisar con criterio"
    else:
        return "Descarte"


def build_card(row):
    color_text, color_bg = get_color(row["score"])
    label = get_label(row["score"])
    empresa = row.get("company", "Empresa no especificada") or "Empresa no especificada"
    ubicacion = row.get("location", "") or ""
    reason = row.get("reason", "") or ""
    date_scored = row["date_scored"].strftime("%d/%m/%Y") if pd.notna(row.get("date_scored")) else ""
    categoria = row.get("categoria", "") or ""

    # Dimensiones — solo si existen
    dimensiones_html = ""
    dimensiones_raw = row.get("dimensiones", None)
    if dimensiones_raw and pd.notna(dimensiones_raw):
        try:
            dims = json.loads(dimensiones_raw)
            nombres = {
                    "fit_negocio": "Fit negocio",
                    "fit_tecnico": "Fit técnico",
                    "proximidad_negocio": "Proximidad negocio",
                    "adyacencia_historial": "Adyacencia historial",  # nueva
                    "empresa": "Empresa",
                    "sector": "Sector",
                    "modalidad": "Modalidad",
                    "seniority": "Seniority"
                     }
            filas = ""
            for key, label_dim in nombres.items():
                if key in dims and isinstance(dims[key], dict):
                    score_dim = dims[key].get("score", "-")
                    note_dim = dims[key].get("note", "")
                    color_dim = "#2d6a4f" if score_dim >= 4 else "#b5700a" if score_dim >= 3 else "#c1121f"
                    filas += f"""
                    <tr>
                        <td style="color:#555; font-size:12px; padding:2px 8px 2px 0">{label_dim}</td>
                        <td style="font-size:12px; font-weight:bold; color:{color_dim}">{score_dim}/5</td>
                        <td style="font-size:12px; color:#666; padding-left:8px">{note_dim}</td>
                    </tr>"""
            
            penalizaciones = dims.get("penalizaciones", 0)
            pen_html = f'<p style="font-size:11px; color:#c1121f; margin:4px 0 0 0">⚠️ Penalizaciones: {penalizaciones}</p>' if penalizaciones else ""

            dimensiones_html = f"""
            <details style="margin-top:8px">
                <summary style="font-size:12px; color:#555; cursor:pointer">Ver desglose por dimensión</summary>
                <table style="margin-top:8px; border-collapse:collapse">
                    {filas}
                </table>
                {pen_html}
            </details>"""
        except:
            pass

    categoria_html = f'<span style="font-size:11px; font-weight:700; color:{color_text}; margin-left:8px">{categoria}</span>' if categoria else ""

    return f"""
    <div class="card" style="border-left: 5px solid {color_text}; background: {color_bg}">
        <div class="card-header">
            <span class="score" style="background: {color_text}">{row["score"]}/10</span>
            <span class="label" style="color: {color_text}">{label}</span>
            {categoria_html}
            <span class="date-tag">{date_scored}</span>
        </div>
        <h3>{row["title"]}</h3>
        <p class="empresa">{empresa} · {ubicacion}</p>
        <p class="reason">{reason}</p>
        {dimensiones_html}
        <a href="{row["job_url"]}" target="_blank">Ver oferta →</a>
    </div>
    """


def build_report(csv_path="results/jobs_scored.csv"):
    jobs = pd.read_csv(csv_path)
    jobs = jobs.sort_values("score", ascending=False).reset_index(drop=True)
    jobs["date_scored"] = pd.to_datetime(jobs["date_scored"], errors="coerce")

    # Última corrida = fecha más reciente en el historial
    ultima_corrida = jobs["date_scored"].max()
    ultima_corrida_str = ultima_corrida.strftime("%d/%m/%Y %H:%M") if pd.notna(ultima_corrida) else "N/A"

    # Separar última corrida del historial
    if pd.notna(ultima_corrida):
        mismo_dia = jobs["date_scored"].dt.date == ultima_corrida.date()
        jobs_nuevas = jobs[mismo_dia].copy()
        jobs_historial = jobs[~mismo_dia].copy()
    else:
        jobs_nuevas = jobs.copy()
        jobs_historial = pd.DataFrame()

    fecha_gen = datetime.now().strftime("%d/%m/%Y %H:%M")
    total_nuevas = len(jobs_nuevas)
    buenos_nuevos = len(jobs_nuevas[jobs_nuevas["score"] >= 7])

    # JSON del historial completo para el buscador
    historial_json = jobs[["title", "company", "location", "score",
                            "reason", "job_url", "date_scored"]].copy()
    historial_json["date_scored"] = historial_json["date_scored"].dt.strftime("%d/%m/%Y")
    historial_json = historial_json.fillna("")
    historial_json_str = historial_json.to_json(orient="records", force_ascii=False)

    # Cards de última corrida
    cards_nuevas = "".join(build_card(row) for _, row in jobs_nuevas.iterrows())

    # Agrupar historial por mes
    historial_por_mes = {}
    if not jobs_historial.empty:
        jobs_historial["mes"] = jobs_historial["date_scored"].dt.to_period("M")
        for mes in sorted(jobs_historial["mes"].unique(), reverse=True):
            jobs_mes = jobs_historial[jobs_historial["mes"] == mes]
            fechas_mes = sorted(jobs_mes["date_scored"].dt.date.unique(), reverse=True)
            historial_por_mes[mes] = {
                "total": len(jobs_mes),
                "buenos": len(jobs_mes[jobs_mes["score"] >= 7]),
                "fechas": fechas_mes,
                "jobs": jobs_mes
            }

    # Generar HTML del historial
    meses_html = ""
    for mes, data in historial_por_mes.items():
        mes_str = mes.strftime("%B %Y").capitalize()
        mes_id = str(mes).replace("-", "")

        corridas_html = ""
        for fecha in data["fechas"]:
            jobs_fecha = data["jobs"][data["jobs"]["date_scored"].dt.date == fecha]
            buenos = len(jobs_fecha[jobs_fecha["score"] >= 7])
            cards = "".join(build_card(row) for _, row in jobs_fecha.iterrows())
            fecha_id = str(fecha).replace("-", "")
            corridas_html += f"""
            <div class="historial-grupo">
                <div class="historial-header nivel-2" onclick="toggleGrupo('corrida-{fecha_id}')">
                    <span>📅 {fecha.strftime("%d/%m/%Y")} — {len(jobs_fecha)} ofertas · {buenos} con score ≥ 7</span>
                    <span class="toggle-icon" id="icon-corrida-{fecha_id}">▼</span>
                </div>
                <div class="historial-cards" id="grupo-corrida-{fecha_id}" style="display:none">
                    {cards}
                </div>
            </div>
            """

        meses_html += f"""
        <div class="historial-grupo">
            <div class="historial-header nivel-1" onclick="toggleGrupo('mes-{mes_id}')">
                <span>📆 {mes_str} — {data['total']} ofertas · {data['buenos']} con score ≥ 7</span>
                <span class="toggle-icon" id="icon-mes-{mes_id}">▼</span>
            </div>
            <div class="historial-cards" id="grupo-mes-{mes_id}" style="display:none">
                {corridas_html}
            </div>
        </div>
        """

    historial_seccion = ""
    if meses_html:
        historial_seccion = f"""
        <div class="historial-grupo">
            <div class="historial-header nivel-0" onclick="toggleGrupo('historial-principal')">
                <span>📁 Historial de corridas anteriores</span>
                <span class="toggle-icon" id="icon-historial-principal">▼</span>
            </div>
            <div class="historial-cards" id="grupo-historial-principal" style="display:none">
                {meses_html}
            </div>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Job Scorer — Resultados</title>
    <style>
        body {{ font-family: -apple-system, sans-serif; max-width: 860px;
                margin: 40px auto; padding: 0 20px; background: #f8f9fa; }}
        h1 {{ color: #1a1a2e; margin-bottom: 4px; }}
        h2 {{ color: #1a1a2e; margin-top: 40px; margin-bottom: 16px; }}
        .meta {{ color: #666; margin-bottom: 16px; font-size: 14px; }}
        .badge {{ background: #1a1a2e; color: white; padding: 2px 8px;
                  border-radius: 10px; font-size: 12px; margin-left: 8px; }}
        .card {{ background: white; border-radius: 8px; padding: 20px;
                 margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        .card-header {{ display: flex; align-items: center; gap: 12px;
                        margin-bottom: 8px; flex-wrap: wrap; }}
        .score {{ color: white; padding: 4px 10px; border-radius: 20px;
                  font-weight: bold; font-size: 14px; }}
        .label {{ font-size: 13px; font-weight: 600; }}
        .date-tag {{ font-size: 12px; color: #888; margin-left: auto; }}
        h3 {{ margin: 0 0 4px 0; color: #1a1a2e; font-size: 16px; }}
        .empresa {{ color: #555; font-size: 14px; margin: 0 0 8px 0; }}
        .reason {{ color: #444; font-size: 14px; margin: 0 0 12px 0;
                   font-style: italic; }}
        a {{ color: #2563eb; text-decoration: none; font-size: 14px;
             font-weight: 500; }}
        a:hover {{ text-decoration: underline; }}
        .divider {{ border: none; border-top: 2px solid #e0e0e0; margin: 40px 0; }}
        .historial-grupo {{ margin-bottom: 12px; }}
        .historial-header {{ background: #e9ecef; padding: 12px 16px;
                             border-radius: 8px; cursor: pointer;
                             display: flex; justify-content: space-between;
                             align-items: center; font-weight: 600;
                             color: #1a1a2e; font-size: 14px; }}
        .historial-header:hover {{ background: #dee2e6; }}
        .nivel-0 {{ background: #1a1a2e; color: white; font-size: 15px; }}
        .nivel-0:hover {{ background: #2d2d4e; }}
        .nivel-1 {{ background: #dee2e6; }}
        .nivel-2 {{ background: #f1f3f5; font-weight: normal; }}
        .historial-cards {{ padding-top: 8px; padding-left: 12px; }}
        .toggle-icon {{ font-size: 12px; color: #666; }}
        .search-container {{ margin-bottom: 24px; }}
        .search-input {{ width: 100%; padding: 12px 16px; font-size: 15px;
                         border: 2px solid #dee2e6; border-radius: 8px;
                         outline: none; box-sizing: border-box; }}
        .search-input:focus {{ border-color: #1a1a2e; }}
        .search-results {{ color: #666; font-size: 13px; margin-top: 8px; }}
        #search-cards-container {{ margin-bottom: 20px; }}
    </style>
</head>
<body>
    <h1>Job Scorer <span class="badge">última corrida</span></h1>
    <p class="meta">
        Generado el {fecha_gen} · Última corrida: {ultima_corrida_str} ·
        {total_nuevas} ofertas analizadas · <strong>{buenos_nuevos} con score ≥ 7</strong>
    </p>

    <div class="search-container">
        <input type="text" class="search-input" id="buscador"
               placeholder="🔍 Buscar por título, empresa o razón..."
               oninput="buscar()">
        <p class="search-results" id="search-results"></p>
    </div>

    <div id="search-cards-container" style="display:none;"></div>

    <div id="main-content">
        {cards_nuevas}

        <hr class="divider">

        {historial_seccion}
    </div>

    <script>
        const historialData = {historial_json_str};

        function toggleGrupo(id) {{
            const cards = document.getElementById('grupo-' + id);
            const icon = document.getElementById('icon-' + id);
            if (cards.style.display === 'none') {{
                cards.style.display = 'block';
                icon.textContent = '▲';
            }} else {{
                cards.style.display = 'none';
                icon.textContent = '▼';
            }}
        }}

        function buscar() {{
            const query = document.getElementById('buscador').value.toLowerCase().trim();
            const resultados = document.getElementById('search-results');
            const searchContainer = document.getElementById('search-cards-container');
            const mainContent = document.getElementById('main-content');

            if (query === '') {{
                searchContainer.innerHTML = '';
                searchContainer.style.display = 'none';
                mainContent.style.display = 'block';
                resultados.textContent = '';
                return;
            }}

            const encontradas = historialData.filter(job =>
                (job.title || '').toLowerCase().includes(query) ||
                (job.company || '').toLowerCase().includes(query) ||
                (job.reason || '').toLowerCase().includes(query)
            );

            mainContent.style.display = 'none';

            if (encontradas.length === 0) {{
                searchContainer.innerHTML = '';
                searchContainer.style.display = 'none';
                resultados.textContent = 'No encontrado — este puesto no fue analizado por el scraper.';
            }} else {{
                const plural = encontradas.length !== 1;
                resultados.textContent = encontradas.length + ' oferta' + (plural ? 's' : '') + ' encontrada' + (plural ? 's' : '') + ' en el historial';

                searchContainer.innerHTML = encontradas.map(job => {{
                    const score = job.score || 0;
                    let colorText, colorBg, label;
                    if (score >= 7) {{ colorText = '#2d6a4f'; colorBg = '#d8f3dc'; label = 'Vale la pena revisar'; }}
                    else if (score >= 5) {{ colorText = '#b5700a'; colorBg = '#fff3cd'; label = 'Revisar con criterio'; }}
                    else {{ colorText = '#c1121f'; colorBg = '#ffe8e8'; label = 'Descarte'; }}

                    return `<div class="card" style="border-left: 5px solid ${{colorText}}; background: ${{colorBg}}">
                        <div class="card-header">
                            <span class="score" style="background: ${{colorText}}">${{score}}/10</span>
                            <span class="label" style="color: ${{colorText}}">${{label}}</span>
                            <span class="date-tag">${{job.date_scored || ''}}</span>
                        </div>
                        <h3>${{job.title || ''}}</h3>
                        <p class="empresa">${{job.company || 'Empresa no especificada'}} · ${{job.location || ''}}</p>
                        <p class="reason">${{job.reason || ''}}</p>
                        <a href="${{job.job_url || '#'}}" target="_blank">Ver oferta →</a>
                    </div>`;
                }}).join('');
                searchContainer.style.display = 'block';
            }}
        }}
    </script>
</body>
</html>"""

    output_path = "results/report.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Reporte generado: {output_path}")
    print(f"Última corrida: {total_nuevas} ofertas · {buenos_nuevos} con score ≥ 7")


if __name__ == "__main__":
    build_report()
