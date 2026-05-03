from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    
    page.goto("https://www.bumeran.com.pe/empleos-busqueda-data+analyst.html")
    
    page.wait_for_timeout(3000)  # espera 3 segundos
    
    print("Título de la página:", page.title())
    print("URL actual:", page.url)
    print("Contenido HTML:", page.content()[:300])
    
    input("Presioná Enter para cerrar el browser...")
    browser.close()