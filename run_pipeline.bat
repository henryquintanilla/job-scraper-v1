@echo off
cd C:\Users\LENOVO\Documents\02. Profesional\02.Proyectos\job_scraper
call venv\Scripts\activate

echo ================================================
echo  JOB SCRAPER — Iniciando pipeline
echo  %date% %time%
echo ================================================

echo.
echo [1/5] Scraping metadata...
python scrapers\scraper_metadata.py

echo.
echo [2/5] Pre-filtro...
python pre_filter.py

echo.
echo [3/5] Fetching descripciones...
python fetch_descriptions.py

echo.
echo [4/5] Scoring con Claude...
python pipeline.py

echo.
echo [5/5] Generando reporte...
python report.py

echo.
echo ================================================
echo  Pipeline completado — %date% %time%
echo  Abrí results/report.html para ver resultados
echo ================================================
pause