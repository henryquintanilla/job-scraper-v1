import anthropic
import json
import re
import os
from dotenv import load_dotenv
from config import SCORING_CRITERIA

load_dotenv()

PESOS = {
    "fit_negocio":        0.22,
    "fit_tecnico":        0.18,
    "proximidad_negocio": 0.18,
    "adyacencia_historial": 0.17,
    "empresa":            0.10,
    "modalidad":          0.07,
    "sector":             0.05,
    "seniority":          0.03,
}

def calcular_score(resultado: dict) -> tuple[int, str]:
    """
    Calcula score_final y categoria en Python — Claude solo evalua dimensiones.
    Retorna (score_final, categoria)
    """
    score_base = sum(
        resultado[dim]["score"] * peso
        for dim, peso in PESOS.items()
        if dim in resultado and isinstance(resultado[dim], dict)
    ) * 2

    penalizaciones = resultado.get("penalizaciones", 0)
    score_final = max(1, min(10, round(score_base) - penalizaciones))

    if score_final >= 9:
        categoria = "PRIORIDAD ALTA"
    elif score_final >= 7:
        categoria = "APLICAR"
    elif score_final >= 5:
        categoria = "SOLO SI HAY POCO PIPELINE"
    else:
        categoria = "DESCARTAR"

    return score_final, categoria

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def pre_score(description: str, use_ollama: bool = False) -> tuple[bool, int, int]:
    """
    Fase 1 — evaluación rápida y barata.
    Retorna (pasa_filtro, fit_negocio, adyacencia)
    """
    prompt = f"""Evaluá estas dos dimensiones del 1 al 5 para un analista semi-senior de analytics comercial en banca (Interbank). Background: segmentación, churn, funnel, dashboards comerciales.

DIMENSIÓN 1 — FIT DE NEGOCIO:
¿El output es influir en decisiones o mantener procesos?
5=propone estrategia/recomienda a gerencia, 3=mix análisis e insumos, 1=reportes fijos/operativo puro
Descarte inmediato si es RRHH, M&A, contabilidad, auditoría, cobranzas.

DIMENSIÓN 2 — ADYACENCIA AL HISTORIAL:
¿Qué tan natural es el movimiento desde analytics comercial en banca?
5=product/growth/pricing/revenue analytics, 3=FP&A ligero/strategy/CX analytics, 1=contabilidad/data engineering/roles ajenos

Devolvé ÚNICAMENTE este JSON sin markdown:
{{"fit_negocio": N, "adyacencia": N}}

DESCRIPCIÓN (primeros 800 chars):
{description[:800]}"""

    try:
        if use_ollama:
            import requests as req
            response = req.post(
                "http://localhost:11434/api/generate",
                json={"model": "llama3.1:8b", "prompt": prompt, "stream": False}
            )
            raw = response.json()["response"].strip()
        else:
            message = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=50,
                temperature=0,
                messages=[{"role": "user", "content": prompt}]
            )
            raw = message.content[0].text.strip()

        clean = re.sub(r"```json\s*|\s*```", "", raw).strip()
        result = json.loads(clean)
        fit = result.get("fit_negocio", 3)
        adj = result.get("adyacencia", 3)

        # Pasa si al menos una es > 2
        pasa = not (fit <= 2 and adj <= 2)
        return pasa, fit, adj

    except Exception as e:
        # En caso de error, pasar al scoring completo por seguridad
        return True, 3, 3

def score_job(description: str, use_ollama: bool = False) -> dict:
    prompt = f"""{SCORING_CRITERIA}

DESCRIPCIÓN DEL TRABAJO:
{description[:2000]}

Recordá: devolvé ÚNICAMENTE el JSON, sin texto adicional ni markdown."""

    if use_ollama:
        import requests
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.1:8b",
                "prompt": prompt,
                "stream": False
            }
        )
        raw = response.json()["response"].strip()
    else:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            temperature=0,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = message.content[0].text.strip()

    # Limpiar markdown
    clean = re.sub(r"```json\s*|\s*```", "", raw).strip()

    try:
        result = json.loads(clean)

        # Verificar que tiene las dimensiones esperadas
        dimensiones = ["fit_negocio", "fit_tecnico", "proximidad_negocio",
                        "adyacencia_historial", "empresa", "sector", 
                        "modalidad", "seniority"]

        if all(d in result for d in dimensiones):
            # Calcular score y categoria en Python
            score_final, categoria = calcular_score(result)
            result["score_final"] = score_final
            result["categoria"] = categoria
            return result
        else:
            return {
                "score": 0,
                "reason": f"JSON incompleto: {list(result.keys())}",
                "error": True
            }

    except json.JSONDecodeError:
        return {
            "score": 0,
            "reason": f"Error al parsear: {raw[:100]}",
            "error": True
        }


def get_score_simple(result: dict) -> int:
    """Extrae el score final del resultado multidimensional o simple"""
    if "score_final" in result:
        return result["score_final"]
    return result.get("score", 0)


def get_reason_simple(result: dict) -> str:
    """Extrae la razón del resultado"""
    return result.get("reason", "")



# ── CV FIT SCORER ─────────────────────────────────────────

CV_RESUMENES = {
    "A": "Analytics & Strategy Analyst. Enfasis en diagnostico de problemas de negocio, SQL y Power BI, recomendaciones accionables. Logros en adopcion digital, reduccion de costos y churn. Para: Data Analyst, BI Analyst, Business Analyst, Commercial Analytics.",
    "B": "Commercial Analytics & Strategy Analyst. Enfasis en impacto comercial: adopcion digital, retencion de alto valor, optimizacion de rentabilidad, business cases. Logro destacado: +40% tipo de cambio (ciclo completo estrategia-ejecucion-resultado). Para: Revenue Analyst, Pricing Analyst, Growth Analyst, Commercial Strategy, Planning Analyst.",
    "C": "Business & Operations Analyst. Enfasis en operaciones con datos: gestion de proyectos cross-funcionales, forecasting, coordinacion tecnica, reporting gerencial. Destaca proyecto Banca Empresa. Para: Operations Analyst, Project Analyst, Planning Analyst, Process Improvement.",
    "D": "Business Analyst Senior. Enfasis en transformacion con IA: identificacion de puntos de dolor, coordinacion negocio-tecnologia, IA generativa. Incluye simulador de forecast. Para: Business Analyst en producto, transformacion digital, PMO analitico, strategy analyst en empresas tech.",
}

CV_FIT_PROMPT = """Eres un asesor de carrera experto. Dado un JD y 4 perfiles de CV, determina cual enviar.

CVs disponibles:
CV A: {cv_a}
CV B: {cv_b}
CV C: {cv_c}
CV D: {cv_d}

JD:
Titulo: {titulo}
Empresa: {empresa}
Descripcion: {descripcion}

Devuelve UNICAMENTE este JSON sin markdown:
{{
  "cv_recomendado": "A",
  "confianza": "alta",
  "gaps": ["gap 1 maximo 8 palabras", "gap 2 maximo 8 palabras"],
  "ajuste_sugerido": "instruccion concreta maximo 15 palabras o null si no hay ajuste"
}}

confianza debe ser exactamente: "alta", "media" o "baja"
cv_recomendado debe ser exactamente: "A", "B", "C" o "D"
gaps: maximo 3 items. Lista vacia si no hay gaps relevantes.
ajuste_sugerido: null si el CV es buen fit sin cambios."""


def fit_cv(description: str, title: str, company: str) -> dict:
    """
    Corre solo para ofertas con score >= 7.
    Devuelve dict con cv_recomendado, confianza, gaps, ajuste_sugerido.
    """
    prompt = CV_FIT_PROMPT.format(
        cv_a=CV_RESUMENES["A"],
        cv_b=CV_RESUMENES["B"],
        cv_c=CV_RESUMENES["C"],
        cv_d=CV_RESUMENES["D"],
        titulo=title,
        empresa=company,
        descripcion=description[:1500],
    )

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            temperature=0,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = message.content[0].text.strip()
        clean = re.sub(r"```json\s*|\s*```", "", raw).strip()
        result = json.loads(clean)

        if "cv_recomendado" not in result or "confianza" not in result:
            return {"cv_recomendado": None, "confianza": None, "gaps": [], "ajuste_sugerido": None, "error": True}

        return result

    except Exception:
        return {"cv_recomendado": None, "confianza": None, "gaps": [], "ajuste_sugerido": None, "error": True}

if __name__ == "__main__":
    descripcion_test = """
    Buscamos Analista de Datos con experiencia en SQL y Python.
    El rol implica construir dashboards en Power BI, análisis de cohortes,
    funnel analysis y generar insights accionables para stakeholders del negocio.
    Modalidad híbrida. Sector fintech. Experiencia requerida: 2-4 años.
    """

    print("Testeando scorer con Claude API...")
    resultado = score_job(descripcion_test)

    if "score_final" in resultado:
        print(f"\nScore final: {resultado['score_final']}/10")
        print(f"Categoría: {resultado.get('categoria', 'N/A')}")
        print(f"Razón: {resultado.get('reason', '')}")
        print("\nDimensiones:")
        for dim in ["fit_negocio", "fit_tecnico", "proximidad_negocio",
                    "empresa", "sector", "modalidad", "seniority"]:
            if dim in resultado:
                d = resultado[dim]
                print(f"  {dim}: {d['score']}/5 — {d['note']}")
        print(f"\nPenalizaciones: {resultado.get('penalizaciones', 0)}")
    else:
        print("Error:", resultado)