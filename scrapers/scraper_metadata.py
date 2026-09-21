from jobspy import scrape_jobs
from playwright.sync_api import sync_playwright
import pandas as pd
import os
from dotenv import load_dotenv
import random
import time

load_dotenv()

# ── FLAGS DE FUENTES ─────────────────────────────────────
# Cambiar a False para desactivar una fuente sin borrar el código
ENABLE_INDEED        = True
ENABLE_LINKEDIN      = True
ENABLE_BUMERAN       = True
ENABLE_WORKDAY       = True
ENABLE_COMPUTRABAJO  = False
ENABLE_GETONBOARD    = True

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

# Portales Workday configurados
# location_param: parámetro de URL para filtrar por país (None = sin filtro)
WORKDAY_PORTALS = [
    {
        "company": "Rappi",
        "base_url": "https://rappi.wd12.myworkdayjobs.com/es/Rappi_jobs",
        "location_param": "locations=35c273db87bf100033a4f0edc5cb0000",  # Perú
    },
    {
        "company": "BBVA",
        "base_url": "https://bbva.wd3.myworkdayjobs.com/es/BBVA",
        "location_param": "locationCountry=0eb156ca580c4db786a7894bdaa77450",  # Perú
    },
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
            jobs["search_term"] = term
            all_jobs.append(jobs)
        except Exception as e:
            print(f"  [Indeed] Error en '{term}': {e} — saltando")
            continue

    combined = pd.concat(all_jobs, ignore_index=True)
    combined = combined.drop_duplicates(subset=["job_url"])
    combined["site"] = "indeed"
    combined["fecha_texto"] = None
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
            linkedin_fetch_description=False,
            linkedin_cookie=cookie
        )
        cols = ["title", "company", "location", "date_posted",
                "job_type", "is_remote", "job_level", "job_url"]
        cols_existentes = [c for c in cols if c in jobs.columns]
        jobs = jobs[cols_existentes].copy()
        jobs["search_term"] = term
        all_jobs.append(jobs)

        delay = random.randint(5, 10)
        time.sleep(delay)

    combined = pd.concat(all_jobs, ignore_index=True)
    combined = combined.drop_duplicates(subset=["job_url"])
    combined["site"] = "linkedin"
    combined["fecha_texto"] = None
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
                        "fecha_texto": fecha_texto,
                        "search_term": term,
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


# ── WORKDAY ─────────────────────────────────────────────

def scrape_workday_portal(page, company, base_url, location_param=None):
    """
    Scrape un portal Workday genérico.
    - Sin keywords (trae todas las ofertas del portal)
    - Filtro de ubicación opcional via URL param
    - Paginación automática leyendo el total de puestos
    """
    all_results = []

    # Construir URL base con filtro de ubicación si aplica
    url = f"{base_url}?{location_param}" if location_param else base_url

    page.goto(url)
    page.wait_for_timeout(5000)

    # Leer total de puestos para calcular páginas
    # Workday muestra "1 - 20 de 47 puestos" o similar
    total_jobs = 0
    try:
        paginacion = page.query_selector("[data-automation-id='jobFoundText']")
        if paginacion:
            texto = paginacion.inner_text()
            # Extraer el total — último número del texto "X - Y de Z puestos"
            import re
            match = re.search(r'de (\d+)', texto)
            if match:
                total_jobs = int(match.group(1))
    except:
        pass

    jobs_por_pagina = 20
    paginas = max(1, -(-total_jobs // jobs_por_pagina))  # ceil division
    print(f"  [{company}] Total: {total_jobs} puestos · {paginas} página(s)")

    for pagina in range(paginas):
        if pagina > 0:
            url_pagina = f"{url}&page={pagina + 1}"
            page.goto(url_pagina)
            page.wait_for_timeout(4000)

        # Extraer cards — el <a> con data-automation-id="jobTitle" es el anchor principal
        cards = page.query_selector_all("a[data-automation-id='jobTitle']")

        for card in cards:
            try:
                titulo = card.inner_text().strip()
                href = card.get_attribute("href")
                job_url = f"https://{base_url.split('//')[1].split('/')[0]}{href}"

                # Subir al li contenedor para extraer los demás campos
                li = card.evaluate_handle("el => el.closest('li')")

                ubicacion_el = li.query_selector("[data-automation-id='locations'] dd")
                ubicacion = ubicacion_el.inner_text().strip() if ubicacion_el else None

                job_type_el = li.query_selector("[data-automation-id='time'] dd")
                job_type = job_type_el.inner_text().strip() if job_type_el else None

                fecha_el = li.query_selector("[data-automation-id='postedOn'] dd")
                fecha_texto = fecha_el.inner_text().strip() if fecha_el else None

                all_results.append({
                    "title": titulo,
                    "company": company,
                    "job_url": job_url,
                    "site": "workday",
                    "location": ubicacion,
                    "date_posted": None,
                    "job_type": job_type,
                    "is_remote": None,
                    "job_level": None,
                    "fecha_texto": fecha_texto,
                    "search_term": None,
                })
            except:
                continue

    return all_results


def scrape_workday_metadata():
    all_results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        for portal in WORKDAY_PORTALS:
            print(f"  [Workday] {portal['company']}...")
            try:
                results = scrape_workday_portal(
                    page=page,
                    company=portal["company"],
                    base_url=portal["base_url"],
                    location_param=portal.get("location_param"),
                )
                all_results.extend(results)
                print(f"  [Workday] {portal['company']}: {len(results)} ofertas")
            except Exception as e:
                print(f"  [Workday] Error en {portal['company']}: {e} — saltando")
                continue

        browser.close()

    df = pd.DataFrame(all_results)
    if df.empty:
        print("  [Workday] Sin resultados")
        return df

    df = df.dropna(subset=["title"])
    df = df.drop_duplicates(subset=["job_url"])
    df = df.reset_index(drop=True)
    print(f"  [Workday] Total: {len(df)} ofertas únicas")
    return df


# ── COMPUTRABAJO ─────────────────────────────────────────

MAX_PAGINAS_COMPUTRABAJO = 3  # 60 ofertas por keyword (20 por página)

def scrape_computrabajo_metadata():
    """
    Scrape Computrabajo Perú con keywords.
    - Extrae metadata del listing Y descripción del panel lateral en una sola sesión
    - Máximo MAX_PAGINAS_COMPUTRABAJO páginas por keyword
    - Paginación via ?p=N
    """
    all_results = []
    seen_urls = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        for term in SEARCHES:
            print(f"  [Computrabajo] {term}...")
            term_slug = term.replace(" ", "-")

            for num_pagina in range(1, MAX_PAGINAS_COMPUTRABAJO + 1):
                if num_pagina == 1:
                    url = f"https://pe.computrabajo.com/trabajo-de-{term_slug}"
                else:
                    url = f"https://pe.computrabajo.com/trabajo-de-{term_slug}?p={num_pagina}"

                try:
                    page.goto(url)
                    page.wait_for_timeout(3000)
                except Exception as e:
                    print(f"    Error navegando página {num_pagina}: {e}")
                    break

                cards = page.query_selector_all("article[data-offers-grid-offer-item-container]")
                if not cards:
                    break  # no hay más resultados

                for card in cards:
                    try:
                        # Título y URL
                        titulo_el = card.query_selector("h2 a.js-o-link")
                        if not titulo_el:
                            continue
                        titulo = titulo_el.inner_text().strip()
                        href = titulo_el.get_attribute("href")
                        job_url = f"https://pe.computrabajo.com{href}"

                        if job_url in seen_urls:
                            continue
                        seen_urls.add(job_url)

                        # Empresa
                        empresa_el = card.query_selector("a[offer-grid-article-company-url]")
                        empresa = empresa_el.inner_text().strip() if empresa_el else None

                        # Ubicación — primer <p> con span.mr10
                        ubicacion_el = card.query_selector("p span.mr10")
                        ubicacion = ubicacion_el.inner_text().strip() if ubicacion_el else None

                        # Fecha relativa
                        fecha_el = card.query_selector("p.fc_aux")
                        fecha_texto = fecha_el.inner_text().strip() if fecha_el else None

                        # Click en la card para cargar descripción en panel lateral
                        titulo_el.click()
                        page.wait_for_timeout(1500)

                        # Extraer descripción del panel lateral
                        desc_el = page.query_selector("div.fs16.t_word_wrap")
                        description = desc_el.inner_text().strip() if desc_el else None

                        all_results.append({
                            "title": titulo,
                            "company": empresa,
                            "job_url": job_url,
                            "site": "computrabajo",
                            "location": ubicacion,
                            "date_posted": None,
                            "job_type": None,
                            "is_remote": None,
                            "job_level": None,
                            "fecha_texto": fecha_texto,
                            "description": description,
                        })
                    except Exception:
                        continue

        browser.close()

    df = pd.DataFrame(all_results)
    if df.empty:
        print("  [Computrabajo] Sin resultados")
        return df

    df = df.dropna(subset=["title"])
    df = df.drop_duplicates(subset=["job_url"])
    df = df.reset_index(drop=True)
    print(f"  [Computrabajo] {len(df)} ofertas únicas con descripción")
    return df



# ── GET ON BOARD ─────────────────────────────────────────

# Categorías de Get on Board relevantes para analytics
GETONBOARD_CATEGORIES = [
    "https://www.getonbrd.com/empleos/data-science-analytics",
    "https://www.getonbrd.com/empleos/marketing-digital",
    "https://www.getonbrd.com/empleos/operaciones-management",
]

def scrape_getonboard_metadata():
    """
    Scrape Get on Board por categoría — sin keywords, sin filtro de fecha en URL.
    Extrae metadata del listing. Descripción + fecha + política remota en fetch.
    Paginación via ?page=2
    """
    all_results = []
    seen_urls = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        for category_url in GETONBOARD_CATEGORIES:
            print(f"  [GetOnBoard] {category_url.split('/')[-1]}...")
            num_pagina = 1

            while True:
                url = category_url if num_pagina == 1 else f"{category_url}?page={num_pagina}"
                try:
                    page.goto(url)
                    page.wait_for_timeout(3000)
                except Exception as e:
                    print(f"    Error en página {num_pagina}: {e}")
                    break

                cards = page.query_selector_all("a.gb-results-list__item")
                if not cards:
                    break

                nuevas = 0
                for card in cards:
                    try:
                        href = card.get_attribute("href")
                        if not href:
                            continue
                        # URL completa
                        if href.startswith("http"):
                            job_url = href
                        else:
                            job_url = f"https://www.getonbrd.com{href}"

                        if job_url in seen_urls:
                            continue
                        seen_urls.add(job_url)
                        nuevas += 1

                        # Título
                        titulo_el = card.query_selector("strong.pr-3")
                        titulo = titulo_el.inner_text().strip() if titulo_el else None

                        # Job type
                        job_type_el = card.query_selector("h2 span.opacity-half")
                        job_type = job_type_el.inner_text().strip() if job_type_el else None

                        # Empresa
                        empresa_el = card.query_selector("div.size0 strong")
                        empresa = empresa_el.inner_text().strip() if empresa_el else None

                        # Ubicación y país — extraer código de flag desde la URL de la imagen
                        pais_code = None
                        ubicacion = None
                        flag_el = card.query_selector("span.location-flag")
                        if flag_el:
                            style = flag_el.get_attribute("style") or ""
                            import re
                            match = re.search(r"/flags/([a-z]{2})_mini", style)
                            if match:
                                pais_code = match.group(1)  # "pe", "cl", "mx", etc.

                        ubicacion_el = card.query_selector("span.js-locations-tooltip")
                        if ubicacion_el:
                            ubicacion = ubicacion_el.inner_text().strip().split("\n")[0].strip()

                        # Modalidad — texto entre paréntesis al final del location span
                        modalidad = None
                        location_span = card.query_selector("span.location")
                        if location_span:
                            texto = location_span.inner_text()
                            match_mod = re.search(r"\((Híbrido|Remoto|Presencial)\)", texto)
                            if match_mod:
                                modalidad = match_mod.group(1)

                        all_results.append({
                            "title": titulo,
                            "company": empresa,
                            "job_url": job_url,
                            "site": "getonboard",
                            "location": ubicacion,
                            "pais_code": pais_code,
                            "modalidad": modalidad,
                            "date_posted": None,
                            "job_type": job_type,
                            "is_remote": None,
                            "job_level": None,
                            "fecha_texto": None,
                            "search_term": None,
                        })
                    except Exception:
                        continue

                print(f"    Página {num_pagina}: {nuevas} nuevas")
                if nuevas == 0:
                    break
                num_pagina += 1

        browser.close()

    df = pd.DataFrame(all_results)
    if df.empty:
        print("  [GetOnBoard] Sin resultados")
        return df

    df = df.dropna(subset=["title"])
    df = df.drop_duplicates(subset=["job_url"])
    df = df.reset_index(drop=True)
    print(f"  [GetOnBoard] {len(df)} ofertas únicas")
    return df

# ── MAIN ─────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Scraping metadata ===\n")

    if ENABLE_INDEED:
        print("-- Indeed --")
        df_indeed = scrape_indeed_metadata()
    else:
        df_indeed = pd.DataFrame()

    if ENABLE_LINKEDIN:
        print("\n-- LinkedIn --")
        df_linkedin = scrape_linkedin_metadata()
    else:
        df_linkedin = pd.DataFrame()

    if ENABLE_BUMERAN:
        print("\n-- Bumeran --")
        df_bumeran = scrape_bumeran_metadata()
    else:
        df_bumeran = pd.DataFrame()

    if ENABLE_WORKDAY:
        print("\n-- Workday (portales corporativos) --")
        df_workday = scrape_workday_metadata()
    else:
        df_workday = pd.DataFrame()

    if ENABLE_COMPUTRABAJO:
        print("\n-- Computrabajo --")
        df_computrabajo = scrape_computrabajo_metadata()
    else:
        df_computrabajo = pd.DataFrame()

    if ENABLE_GETONBOARD:
        print("\n-- Get on Board --")
        df_getonboard = scrape_getonboard_metadata()
    else:
        df_getonboard = pd.DataFrame()

    print("\n=== Combinando ===")
    dfs = [df for df in [df_indeed, df_linkedin, df_bumeran, df_workday, df_computrabajo, df_getonboard] if not df.empty]

    combined = pd.concat(dfs, ignore_index=True)
    combined = combined.drop_duplicates(subset=["job_url"])
    combined = combined.reset_index(drop=True)

    print(f"Total metadata: {len(combined)} ofertas unicas")
    print("\nPor fuente:")
    print(combined["site"].value_counts())

    combined.to_csv("results/metadata_raw.csv", index=False)
    print("\nGuardado en results/metadata_raw.csv")
