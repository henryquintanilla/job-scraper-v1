import anthropic
import json
import re
import os
from dotenv import load_dotenv
from config import SCORING_CRITERIA

load_dotenv()

PESOS = {
    "fit_negocio": 0.25,
    "fit_tecnico": 0.20,
    "proximidad_negocio": 0.20,
    "empresa": 0.15,
    "modalidad": 0.10,
    "sector": 0.05,
    "seniority": 0.05,
}

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

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
            return result
        else:
            # Formato incompleto — devolver error estructurado
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