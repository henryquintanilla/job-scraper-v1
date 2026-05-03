# Job Scraper con Scoring Automático

Pipeline de búsqueda laboral que extrae ofertas de LinkedIn, Indeed y Bumeran,
las filtra automáticamente y usa IA para evaluar el fit con tu perfil.

## ¿Qué hace?

1. **Scrapea** ofertas de tres fuentes (LinkedIn, Indeed, Bumeran)
2. **Filtra** por título, nivel de seniority y fecha de publicación
3. **Descarga** descripciones completas solo de las ofertas que pasaron el filtro
4. **Scorea** cada oferta del 1 al 10 usando Claude AI (o Llama local)
5. **Genera** un reporte HTML navegable con ranking y links directos

## Stack técnico

- **Python 3.11**
- **jobspy** — scraping de Indeed y LinkedIn
- **Playwright** — browser automation para Bumeran
- **Pandas** — manipulación y limpieza de datos
- **Claude API (Haiku)** — scoring con IA
- **Ollama + Llama 3.1 8b** — alternativa local gratuita
- **SQLite** — cache para no re-scorear ofertas ya vistas

## Estructura del proyecto

```
job_scraper/
├── scrapers/
│   └── scraper_metadata.py  # Extrae metadata de las tres fuentes
├── pre_filter.py             # Filtra por título, seniority y fecha
├── fetch_descriptions.py     # Descarga JDs de ofertas filtradas
├── pipeline.py               # Scorea con IA y guarda en cache
├── scorer.py                 # Cliente Claude API / Ollama
├── cache.py                  # Historial SQLite
├── config.py                 # Prompt de scoring configurable
├── report.py                 # Genera reporte HTML
├── run_pipeline.bat          # Ejecuta el pipeline completo
└── results/
    └── report.html           # Output final
```

## Instalación

```bash
# Clonar el repositorio
git clone https://github.com/tu_usuario/job-scraper-v1.git
cd job-scraper-v1

# Crear entorno virtual
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux

# Instalar dependencias
pip install -r requirements.txt

# Instalar browser para Playwright
python -m playwright install chromium
```

## Configuración

Creá un archivo `.env` en la raíz del proyecto:

```
ANTHROPIC_API_KEY=sk-ant-tu_key_aqui
LINKEDIN_COOKIE=tu_cookie_li_at_aqui
```

- **ANTHROPIC_API_KEY** — obtenela en console.anthropic.com
- **LINKEDIN_COOKIE** — valor de la cookie `li_at` desde DevTools de LinkedIn

## Uso

### Opción 1 — Script automático (recomendado)

```bash
run_pipeline.bat
```

### Opción 2 — Paso a paso

```bash
python scrapers/scraper_metadata.py  # ~15 min
python pre_filter.py                 # ~1 min
python fetch_descriptions.py         # ~15 min
python pipeline.py                   # ~1 min
python report.py                     # instantáneo
```

Abrí `results/report.html` en tu browser para ver los resultados.

## Configurar el scoring

Editá `config.py` para personalizar los criterios de evaluación:
- Skills y herramientas que suman puntos
- Sectores preferidos
- Modalidad de trabajo
- Señales de influencia en decisiones de negocio

## Usar Ollama (gratis, sin API key)

En `pipeline.py` cambiá:

```python
USE_OLLAMA = True
```

Requiere tener Ollama instalado y el modelo descargado:

```bash
ollama pull llama3.1:8b
```

## Costo estimado con Claude API

| Modelo | Costo por corrida (100 ofertas) |
|---|---|
| Claude Haiku 4.5 | ~$0.15 |
| Claude Sonnet 4.6 | ~$0.75 |

## Tiempo de ejecución

| Paso | Tiempo aproximado |
|---|---|
| Scraping metadata | ~15 minutos |
| Pre-filtro | ~1 minuto |
| Fetch descripciones | ~15 minutos |
| Scoring (ofertas nuevas) | ~1-3 minutos |
| **Total primera corrida** | **~35 minutos** |
| **Total corridas siguientes** | **~32 minutos** |

El cache SQLite evita re-scorear ofertas ya vistas — solo procesa las nuevas.

## Fuentes de datos

| Fuente | Ofertas típicas | Notas |
|---|---|---|
| Bumeran | ~40-50 | Mejor cobertura mercado peruano |
| LinkedIn | ~50-60 | Requiere cookie de sesión |
| Indeed | ~10-15 | Menor volumen en Perú |

## Requisitos

Generá el archivo de dependencias con:

```bash
pip freeze > requirements.txt
```
