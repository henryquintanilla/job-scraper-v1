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
            # Buscar la oferta por URL
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
            # Solo quedarse con las URLs que pasaron el pre-filter
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
    
    # Para URLs no encontradas, poner None
    for url in urls_objetivo:
        if url not in descriptions:
            descriptions[url] = None

    found = sum(1 for v in descriptions.values() if v is not None)
    print(f"  [LinkedIn] Descripciones encontradas: {found}/{len(urls_objetivo)}")
    
    return descriptions


if __name__ == "__main__":
    df = pd.read_csv("results/metadata_filtered.csv")
    print(f"Fetching descripciones para {len(df)} ofertas...\n")
    
    df_bumeran = df[df["site"] == "bumeran"].copy()
    df_indeed = df[df["site"] == "indeed"].copy()
    df_linkedin = df[df["site"] == "linkedin"].copy()
    
    all_descriptions = {}
    
    print("-- Bumeran --")
    desc_bumeran = fetch_bumeran_descriptions(df_bumeran["job_url"].tolist())
    all_descriptions.update(desc_bumeran)
    
    print("\n-- Indeed --")
    desc_indeed = fetch_indeed_descriptions(df_indeed)
    all_descriptions.update(desc_indeed)
    
    print("\n-- LinkedIn --")
    desc_linkedin = fetch_linkedin_descriptions(df_linkedin)
    all_descriptions.update(desc_linkedin)
    
    # Agregar descripciones al DataFrame
    df["description"] = df["job_url"].map(all_descriptions)
    df = df.dropna(subset=["description"])
    df = df.reset_index(drop=True)
    
    print(f"\nOfertas con descripción: {len(df)}")
    df.to_csv("results/jobs_raw.csv", index=False)
    print("Guardado en results/jobs_raw.csv")