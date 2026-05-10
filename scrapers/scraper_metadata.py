from jobspy import scrape_jobs
from playwright.sync_api import sync_playwright
import pandas as pd
import os
from dotenv import load_dotenv
import random
import time

load_dotenv()

SEARCHES = [
    # Core - Cluster A (Analytics & BI)
    "data analyst", "business analyst", "analista de datos",
    "analista business intelligence", "business intelligence analyst",
    "analista de inteligencia de negocios",
    # Core - Cluster B (Estrategia Comercial & Revenue)
    "analista comercial", "analista de estrategia comercial",
    "analista de revenue", "analista de pricing", "revenue analyst",
    "growth analyst", "analista de growth", "commercial analyst",
    # Core - Cluster C (Operaciones & Proyectos)
    "analista de operaciones", "analista de planificación",
    "operations analyst", "planning analyst",
    # Product Analytics
    "product analyst", "analista de producto",
    # Búsquedas amplias
    "analista senior datos", "senior data analyst",
    # Inteligencia comercial
    "analista de inteligencia comercial", "market analyst",
    "analista de mercado",
]

# ── INDEED ──────────────────────────────────────────────

def scrape_indeed_metadata():
    all_jobs = []

    for term in SEARCHES:
        print(f"  [Indeed] {term}...")
        try:
            jobs = scrape_jobs(
                site_name=["indeed"],
                search_term=term,
                location="Lima, Peru",
                results_wanted=20,
                hours_old=72,
                country_indeed="Peru"
            )
            cols = ["title", "company", "location", "date_posted",
                    "job_type", "is_remote", "job_level", "job_url"]
            cols_existentes = [c for c in cols if c in jobs.columns]
            jobs = jobs[cols_existentes].copy()
            all_jobs.append(jobs)
        except Exception as e:
            print(f"  [Indeed] Error en '{term}': {e} — saltando")
            continue

    combined = pd.concat(all_jobs, ignore_index=True)
    combined = combined.drop_duplicates(subset=["job_url"])
    combined["site"] = "indeed"
    combined["fecha_texto"] = None  # ← agregar acá
    combined = combined.reset_index(drop=True)
    print(f"  [Indeed] {len(combined)} ofertas únicas")
    return combined


# ── LINKEDIN ─────────────────────────────────────────────

def scrape_linkedin_metadata():
    cookie = os.getenv("LINKEDIN_COOKIE")
    if not cookie:
        print("  [LinkedIn] Cookie no encontrada — saltando")
        return pd.DataFrame()

    all_jobs = []

    for term in SEARCHES:
        print(f"  [LinkedIn] {term}...")
        jobs = scrape_jobs(
            site_name=["linkedin"],
            search_term=term,
            location="Lima, Peru",
            results_wanted=25,
            hours_old=72,
            linkedin_fetch_description=False,  # ← solo metadata
            linkedin_cookie=cookie
        )
        cols = ["title", "company", "location", "date_posted",
                "job_type", "is_remote", "job_level", "job_url"]
        cols_existentes = [c for c in cols if c in jobs.columns]
        jobs = jobs[cols_existentes].copy()
        all_jobs.append(jobs)

        delay = random.randint(5, 10)  # delay más corto sin fetch_description
        time.sleep(delay)

    combined = pd.concat(all_jobs, ignore_index=True)
    combined = combined.drop_duplicates(subset=["job_url"])
    combined["site"] = "linkedin"
    combined["fecha_texto"] = None  # ← agregar acá
    combined = combined.reset_index(drop=True)
    print(f"  [LinkedIn] {len(combined)} ofertas únicas")
    return combined


# ── BUMERAN ─────────────────────────────────────────────

def scrape_bumeran_metadata():
    all_results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        for term in SEARCHES:
            print(f"  [Bumeran] {term}...")
            url = f"https://www.bumeran.com.pe/empleos-busqueda-{term.replace(' ', '+')}.html"
            page.goto(url)
            page.wait_for_timeout(3000)

            try:
                page.click("button:has-text('Acepto')", timeout=2000)
                page.wait_for_timeout(500)
            except:
                pass

            cards = page.query_selector_all("div[id*='header-col-job-posting']")

            for card in cards:
                try:
                    card_id = card.evaluate("el => el.closest('[id*=\"header-col-job-posting\"]').id")
                    job_id = card_id.replace("header-col-job-posting-", "")
                    titulo = card.query_selector("h2")
                    empresa = card.query_selector("span[class*='dcOKER'] h3")
                    
                    # Extraer fecha relativa — primer h3 de la card
                    fecha_elemento = card.query_selector("h3")
                    fecha_texto = fecha_elemento.inner_text() if fecha_elemento else None

                    all_results.append({
                        "title": titulo.inner_text() if titulo else None,
                        "company": empresa.inner_text() if empresa else None,
                        "job_url": f"https://www.bumeran.com.pe/empleos/id-{job_id}.html",
                        "site": "bumeran",
                        "location": "Lima, Peru",
                        "date_posted": None,
                        "job_type": None,
                        "is_remote": None,
                        "job_level": None,
                        "fecha_texto": fecha_texto,  # ← nuevo campo
                    })
                except:
                    continue

        browser.close()

    df = pd.DataFrame(all_results)
    df = df.dropna(subset=["title"])
    df = df.drop_duplicates(subset=["job_url"])
    df = df.reset_index(drop=True)
    print(f"  [Bumeran] {len(df)} ofertas únicas")
    return df


# ── MAIN ─────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Scraping metadata ===\n")

    print("-- Indeed --")
    df_indeed = scrape_indeed_metadata()

    print("\n-- LinkedIn --")
    df_linkedin = scrape_linkedin_metadata()

    print("\n-- Bumeran --")
    df_bumeran = scrape_bumeran_metadata()

    print("\n=== Combinando ===")
    combined = pd.concat([df_indeed, df_linkedin, df_bumeran], ignore_index=True)
    combined = combined.drop_duplicates(subset=["job_url"])
    combined = combined.reset_index(drop=True)

    print(f"Total metadata: {len(combined)} ofertas únicas")
    print("\nPor fuente:")
    print(combined["site"].value_counts())

    combined.to_csv("results/metadata_raw.csv", index=False)
    print("\nGuardado en results/metadata_raw.csv")