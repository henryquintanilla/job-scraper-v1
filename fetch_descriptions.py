from playwright.sync_api import sync_playwright
from jobspy import scrape_jobs
import pandas as pd
import time
import random
import os
from dotenv import load_dotenv

load_dotenv()

def fetch_bumeran_descriptions(urls):
    descriptions = {}
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        for i, url in enumerate(urls):
            print(f"  [Bumeran] [{i+1}/{len(urls)}] {url}")
            try:
                page.goto(url)
                page.wait_for_timeout(3000)
                
                try:
                    page.click("button:has-text('Acepto')", timeout=2000)
                    page.wait_for_timeout(500)
                except:
                    pass
                
                section = page.query_selector("div#section-detalle")
                descriptions[url] = section.inner_text() if section else None
            except:
                descriptions[url] = None
        
        browser.close()
    
    return descriptions


def fetch_indeed_descriptions(df_indeed):
    descriptions = {}
    
    for i, row in df_indeed.iterrows():
        print(f"  [Indeed] [{i+1}/{len(df_indeed)}] {row['title']}")
        try:
            jobs = scrape_jobs(
                site_name=["indeed"],
                search_term=row["title"],
                location="Lima, Peru",
                results_wanted=1,
                country_indeed="Peru"
            )
            match = jobs[jobs["job_url"] == row["job_url"]]
            if not match.empty and pd.notna(match.iloc[0]["description"]):
                descriptions[row["job_url"]] = match.iloc[0]["description"]
            else:
                descriptions[row["job_url"]] = None
        except:
            descriptions[row["job_url"]] = None
        
        time.sleep(random.randint(2, 5))
    
    return descriptions


def fetch_linkedin_descriptions(df_linkedin):
    cookie = os.getenv("LINKEDIN_COOKIE")
    if not cookie:
        print("  [LinkedIn] Cookie no encontrada — saltando")
        return {url: None for url in df_linkedin["job_url"]}

    from scrapers.scraper_metadata import SEARCHES
    
    all_jobs = []
    urls_objetivo = set(df_linkedin["job_url"].tolist())

    for term in SEARCHES:
        print(f"  [LinkedIn] Buscando con descripciones: {term}...")
        try:
            jobs = scrape_jobs(
                site_name=["linkedin"],
                search_term=term,
                location="Lima, Peru",
                results_wanted=15,
                hours_old=72,
                linkedin_fetch_description=True,
                linkedin_cookie=cookie
            )
            jobs_filtrados = jobs[jobs["job_url"].isin(urls_objetivo)]
            all_jobs.append(jobs_filtrados)
        except:
            continue

        delay = random.randint(10, 20)
        time.sleep(delay)

    if not all_jobs:
        return {url: None for url in df_linkedin["job_url"]}

    combined = pd.concat(all_jobs, ignore_index=True)
    combined = combined.drop_duplicates(subset=["job_url"])

    descriptions = dict(zip(combined["job_url"], combined["description"]))
    
    for url in urls_objetivo:
        if url not in descriptions:
            descriptions[url] = None

    found = sum(1 for v in descriptions.values() if v is not None)
    print(f"  [LinkedIn] Descripciones encontradas: {found}/{len(urls_objetivo)}")
    
    return descriptions


def fetch_workday_descriptions(urls):
    """
    Extrae el JD de cada oferta Workday entrando a la URL individual.
    Workday renderiza el contenido en [data-automation-id='jobPostingDescription']
    """
    descriptions = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        for i, url in enumerate(urls):
            print(f"  [Workday] [{i+1}/{len(urls)}] {url}")
            try:
                page.goto(url)
                page.wait_for_timeout(4000)

                section = page.query_selector("[data-automation-id='jobPostingDescription']")
                descriptions[url] = section.inner_text() if section else None
            except:
                descriptions[url] = None

        browser.close()

    found = sum(1 for v in descriptions.values() if v is not None)
    print(f"  [Workday] Descripciones encontradas: {found}/{len(urls)}")
    return descriptions



def fetch_getonboard_descriptions(urls):
    """
    Entra a cada URL de Get on Board y extrae:
    - Descripción: div.gb-rich-txt (concatena todos los bloques)
    - Fecha: <time> tag -> date_posted ISO
    - Política remota: texto bajo h2 "Política de trabajo remoto"
    """
    results = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        for i, url in enumerate(urls):
            print(f"  [GetOnBoard] [{i+1}/{len(urls)}] {url}")
            try:
                page.goto(url)
                page.wait_for_timeout(3000)

                # Descripción — concatenar todos los bloques gb-rich-txt
                bloques = page.query_selector_all("div.gb-rich-txt")
                description = "\n\n".join(
                    b.inner_text().strip() for b in bloques if b.inner_text().strip()
                ) or None

                # Fecha de publicación
                date_posted = None
                time_el = page.query_selector("time")
                if time_el:
                    import re
                    texto_fecha = time_el.inner_text().strip()
                    # "11 de mayo de 2026" -> parse
                    meses = {
                        "enero": "01", "febrero": "02", "marzo": "03",
                        "abril": "04", "mayo": "05", "junio": "06",
                        "julio": "07", "agosto": "08", "septiembre": "09",
                        "octubre": "10", "noviembre": "11", "diciembre": "12"
                    }
                    match = re.search(r"(\d+) de (\w+) de (\d{4})", texto_fecha)
                    if match:
                        dia, mes_texto, anio = match.groups()
                        mes = meses.get(mes_texto.lower())
                        if mes:
                            date_posted = f"{anio}-{mes}-{dia.zfill(2)}"

                # Política remota
                politica_remota = None
                try:
                    h2_elements = page.query_selector_all("h2")
                    for h2 in h2_elements:
                        if "Política de trabajo remoto" in h2.inner_text():
                            # El texto descriptivo está dos elementos después
                            parent = h2.evaluate_handle("el => el.parentElement")
                            politica_remota = parent.query_selector("p.size0").inner_text().strip()
                            break
                except Exception:
                    pass

                results[url] = {
                    "description": description,
                    "date_posted": date_posted,
                    "politica_remota": politica_remota,
                }
            except Exception:
                results[url] = {
                    "description": None,
                    "date_posted": None,
                    "politica_remota": None,
                }

        browser.close()

    found = sum(1 for v in results.values() if v["description"] is not None)
    print(f"  [GetOnBoard] Descripciones encontradas: {found}/{len(urls)}")
    return results

if __name__ == "__main__":
    df = pd.read_csv("results/metadata_filtered.csv")
    print(f"Fetching descripciones para {len(df)} ofertas...\n")
    
    df_bumeran = df[df["site"] == "bumeran"].copy()
    df_indeed = df[df["site"] == "indeed"].copy()
    df_linkedin = df[df["site"] == "linkedin"].copy()
    df_workday = df[df["site"] == "workday"].copy()
    df_computrabajo = df[df["site"] == "computrabajo"].copy()

    all_descriptions = {}

    # Computrabajo ya trae descripción desde scraper_metadata.py
    # Solo mapeamos las que ya existen en el CSV
    if not df_computrabajo.empty:
        if "description" in df_computrabajo.columns:
            desc_computrabajo = dict(zip(
                df_computrabajo["job_url"],
                df_computrabajo["description"]
            ))
            all_descriptions.update(desc_computrabajo)
            found = sum(1 for v in desc_computrabajo.values() if pd.notna(v))
            print(f"-- Computrabajo -- {found}/{len(df_computrabajo)} descripciones ya disponibles")

    print("-- Bumeran --")
    desc_bumeran = fetch_bumeran_descriptions(df_bumeran["job_url"].tolist())
    all_descriptions.update(desc_bumeran)
    
    print("\n-- Indeed --")
    desc_indeed = fetch_indeed_descriptions(df_indeed)
    all_descriptions.update(desc_indeed)
    
    print("\n-- LinkedIn --")
    desc_linkedin = fetch_linkedin_descriptions(df_linkedin)
    all_descriptions.update(desc_linkedin)

    if not df_workday.empty:
        print("\n-- Workday --")
        desc_workday = fetch_workday_descriptions(df_workday["job_url"].tolist())
        all_descriptions.update(desc_workday)
    
    # Get on Board — fetch descripción + fecha + política remota
    df_getonboard = df[df["site"] == "getonboard"].copy()
    if not df_getonboard.empty:
        print("\n-- Get on Board --")
        res_gob = fetch_getonboard_descriptions(df_getonboard["job_url"].tolist())
        for url, data in res_gob.items():
            all_descriptions[url] = data["description"]
        # Propagar date_posted y politica_remota al dataframe
        df.loc[df["job_url"].isin(res_gob), "date_posted"] = df.loc[df["job_url"].isin(res_gob), "job_url"].map(
            lambda u: res_gob.get(u, {}).get("date_posted")
        )
        df.loc[df["job_url"].isin(res_gob), "politica_remota"] = df.loc[df["job_url"].isin(res_gob), "job_url"].map(
            lambda u: res_gob.get(u, {}).get("politica_remota")
        )

    df["description"] = df["job_url"].map(all_descriptions)
    df = df.dropna(subset=["description"])
    df = df.reset_index(drop=True)

    print(f"\nOfertas con descripcion: {len(df)}")
    df.to_csv("results/jobs_raw.csv", index=False)
    print("Guardado en results/jobs_raw.csv")
