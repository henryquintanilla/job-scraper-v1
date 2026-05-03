import anthropic
import requests
import json
import os
from dotenv import load_dotenv
from config import SCORING_CRITERIA

load_dotenv()

def score_job(description: str, use_ollama: bool = False) -> dict:
    prompt = f"""{SCORING_CRITERIA}

DESCRIPCIÓN DEL TRABAJO:
{description[:2000]}

Recordá: devolvé ÚNICAMENTE el JSON, sin texto adicional."""

    if use_ollama:
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
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = message.content[0].text.strip()

    clean = raw.replace("```json", "").replace("```", "").strip()

    try:
        result = json.loads(clean)
    except json.JSONDecodeError:
        result = {"score": 0, "reason": f"Error al parsear: {raw[:100]}"}

    return result


if __name__ == "__main__":
    descripcion_test = """
    Buscamos Analista de Datos con experiencia en SQL y Python.
    El rol implica construir dashboards en Power BI, análisis de cohortes,
    funnel analysis y generar insights accionables para stakeholders del negocio.
    Modalidad híbrida. Sector fintech. Experiencia requerida: 2-4 años.
    """

    print("Testeando scorer con Claude API...")
    resultado = score_job(descripcion_test)
    print("Score:", resultado["score"])
    print("Razón:", resultado["reason"])