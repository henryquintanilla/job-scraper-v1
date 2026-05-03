from jobspy import scrape_jobs
from playwright.sync_api import sync_playwright
import pandas as pd
from dotenv import load_dotenv
import os

load_dotenv()  # carga el .env automáticamente

SEARCHES = [
    # Core - Cluster A (Analytics & BI)
    "data analyst",
    "business analyst",
    "analista de datos",
    "analista business intelligence",
    "business intelligence analyst",
    "analista de inteligencia de negocios",

    # Core - Cluster B (Estrategia Comercial & Revenue)
    "analista comercial",
    "analista de inteligencia comercial"
    "analista de revenue",
    "analista de pricing",
    "revenue analyst",
    "growth analyst",
    "analista de growth",
    "commercial analyst",

    # Core - Cluster C (Operaciones & Proyectos)
    "analista de planificación",
    "operations analyst",
    "planning analyst",

    # Product Analytics
    "product analyst",
    "analista de producto",

    # Búsquedas amplias con buen hit rate
    "analista senior datos",
    "senior data analyst",
]

# ── INDEED ──────────────────────────────────────────────

def scrape_indeed():
    all_jobs = []

    for term in SEARCHES:
        print(f"  [Indeed] Buscando: {term}...")
        jobs = scrape_jobs(
            site_name=["indeed"],
            search_term=term,
            location="Lima, Peru",
            results_wanted=10,
            hours_old=168,
            country_indeed="Peru"
        )
        all_jobs.append(jobs)

    combined = pd.concat(all_jobs, ignore_index=True)
    combined = combined.drop_duplicates(subset=["job_url"])

    columnas = [
        "title", "company", "location", "date_posted",
        "job_type", "is_remote", "job_level", "description",
        "job_url"
    ]
    combined = combined[columnas].copy()
    combined["site"] = "indeed"
    combined = combined.dropna(subset=["description"])
    combined = combined.reset_index(drop=True)

    print(f"  [Indeed] {len(combined)} ofertas únicas con descripción")
    return combined

# ── LINKEDIN ─────────────────────────────────────────────
def scrape_linkedin():
    import time
    import random
    
    cookie = os.getenv("LINKEDIN_COOKIE")
    if not cookie:
        print("  [LinkedIn] Cookie no encontrada en .env — saltando")
        return pd.DataFrame()
    
    all_jobs = []
    
    for term in SEARCHES:
        print(f"  [LinkedIn] Buscando: {term}...")
        jobs = scrape_jobs(
            site_name=["linkedin"],
            search_term=term,
            location="Lima, Peru",
            results_wanted=15,  # más conservador que Indeed/Bumeran
            hours_old=72,       # 3 días — consistente con tu ciclo
            linkedin_fetch_description=True,
            linkedin_cookie=cookie
        )
        all_jobs.append(jobs)
        
        # Delay aleatorio entre búsquedas — comportamiento humano
        delay = random.randint(20, 40)
        print(f"    Esperando {delay}s antes de siguiente búsqueda...")
        time.sleep(delay)
    
    combined = pd.concat(all_jobs, ignore_index=True)
    combined = combined.drop_duplicates(subset=["job_url"])
    
    columnas = [
        "title", "company", "location", "date_posted",
        "job_type", "is_remote", "job_level", "description",
        "job_url"
    ]
    
    # Solo incluir columnas que existen
    columnas_existentes = [c for c in columnas if c in combined.columns]
    combined = combined[columnas_existentes].copy()
    combined["site"] = "linkedin"
    combined = combined.dropna(subset=["description"])
    combined = combined.reset_index(drop=True)
    
    print(f"  [LinkedIn] {len(combined)} ofertas con descripción")
    return combined

# ── BUMERAN ─────────────────────────────────────────────

def get_description_bumeran(page, url):
    try:
        page.goto(url)
        page.wait_for_timeout(3000)
        try:
            page.click("button:has-text('Acepto')", timeout=2000)
            page.wait_for_timeout(500)
        except:
            pass
        section = page.query_selector("div#section-detalle")
        return section.inner_text() if section else None
    except:
        return None


def scrape_bumeran():
    all_results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        # Scrape listing pages
        for term in SEARCHES:
            print(f"  [Bumeran] Buscando: {term}...")
            url = f"https://www.bumeran.com.pe/empleos-busqueda-{term.replace(' ', '+')}.html"
            page.goto(url)
            page.wait_for_timeout(4000)

            try:
                page.click("button:has-text('Acepto')", timeout=3000)
                page.wait_for_timeout(1000)
            except:
                pass

            cards = page.query_selector_all("div[id*='header-col-job-posting']")

            for card in cards:
                try:
                    card_id = card.evaluate("el => el.closest('[id*=\"header-col-job-posting\"]').id")
                    job_id = card_id.replace("header-col-job-posting-", "")
                    titulo = card.query_selector("h2")
                    empresa = card.query_selector("span[class*='dcOKER'] h3")

                    all_results.append({
                        "title": titulo.inner_text() if titulo else None,
                        "company": empresa.inner_text() if empresa else None,
                        "job_url": f"https://www.bumeran.com.pe/empleos/id-{job_id}.html",
                        "site": "bumeran"
                    })
                except:
                    continue

        df = pd.DataFrame(all_results)
        df = df.dropna(subset=["title"])
        df = df.drop_duplicates(subset=["job_url"])
        df = df.reset_index(drop=True)

        print(f"  [Bumeran] Extrayendo descripciones para {len(df)} ofertas...")

        descriptions = []
        for i, row in df.iterrows():
            print(f"    [{i+1}/{len(df)}] {row['title']}")
            desc = get_description_bumeran(page, row["job_url"])
            descriptions.append(desc)

        browser.close()

    df["description"] = descriptions
    df["location"] = "Lima, Peru"
    df["date_posted"] = None
    df["job_type"] = None
    df["is_remote"] = None
    df["job_level"] = None
    df = df.dropna(subset=["description"])
    df = df.reset_index(drop=True)

    print(f"  [Bumeran] {len(df)} ofertas con descripción")
    return df


# ── MAIN ─────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Scraping Indeed ===")
    df_indeed = scrape_indeed()

    print("\n=== Scraping LinkedIn ===")
    df_linkedin = scrape_linkedin()

    print("\n=== Scraping Bumeran ===")
    df_bumeran = scrape_bumeran()

    print("\n=== Combinando fuentes ===")
    combined = pd.concat([df_indeed, df_linkedin, df_bumeran], ignore_index=True)
    combined = combined.drop_duplicates(subset=["job_url"])
    combined = combined.reset_index(drop=True)

    print(f"Total final: {len(combined)} ofertas únicas")
    print("\nOfertas por fuente:")
    print(combined["site"].value_counts())

    combined.to_csv("results/jobs_raw.csv", index=False)
    print("\nGuardado en results/jobs_raw.csv")