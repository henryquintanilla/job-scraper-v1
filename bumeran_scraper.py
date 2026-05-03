from playwright.sync_api import sync_playwright
import pandas as pd

SEARCHES = [
    "data analyst",
    "business analyst",
    "analista de datos",
    "product analyst",
    "analista business intelligence",
]

def scrape_bumeran(search_term):
    results = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.set_viewport_size({"width": 1280, "height": 800})

        url = f"https://www.bumeran.com.pe/empleos-busqueda-{search_term.replace(' ', '+')}.html"
        page.goto(url)
        page.wait_for_timeout(4000)

        try:
            page.click("button:has-text('Acepto')", timeout=3000)
            page.wait_for_timeout(1000)
        except:
            pass

                
       # Extraer cards de ofertas
        cards = page.query_selector_all("div[id*='header-col-job-posting']")
        print(f"  → {len(cards)} ofertas encontradas para '{search_term}'")

        for card in cards:
            try:
                card_id = card.evaluate("el => el.closest('[id*=\"header-col-job-posting\"]').id")
                job_id = card_id.replace("header-col-job-posting-", "")

                titulo = card.query_selector("h2")
                empresa = card.query_selector("span[class*='dcOKER'] h3")

                results.append({
                    "title": titulo.inner_text() if titulo else None,
                    "company": empresa.inner_text() if empresa else None,
                    "job_url": f"https://www.bumeran.com.pe/empleos/id-{job_id}.html",
                    "site": "bumeran"
                })
            except:
                continue

        browser.close()
    
    return results

def get_description(page, url):
    page.goto(url)
    page.wait_for_timeout(3000)
    
    try:
        page.click("button:has-text('Acepto')", timeout=2000)
        page.wait_for_timeout(500)
    except:
        pass
    
    section = page.query_selector("div#section-detalle")
    return section.inner_text() if section else None

all_results = []

for term in SEARCHES:
    print(f"Buscando: {term}...")
    results = scrape_bumeran(term)
    all_results.extend(results)

df = pd.DataFrame(all_results)
df = df.dropna(subset=["title"])
df = df.drop_duplicates(subset=["job_url"])
df = df.reset_index(drop=True)

print(f"\nTotal ofertas únicas: {len(df)}")

# Extraer descripciones
print("\nExtrayendo descripciones...")
with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    
    descriptions = []
    for i, row in df.iterrows():
        print(f"[{i+1}/{len(df)}] {row['title']}")
        desc = get_description(page, row["job_url"])
        descriptions.append(desc)
    
    browser.close()

df["description"] = descriptions
df = df.dropna(subset=["description"])
df = df.reset_index(drop=True)

print(f"\nOfertas con descripción: {len(df)}")
df.to_csv("results/bumeran_raw.csv", index=False)
print("Guardado en results/bumeran_raw.csv")