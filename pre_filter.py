import pandas as pd
from datetime import datetime, timedelta
import re


# Palabras que descartan sin importar nada más
DESCARTE_TITULO = [
    # RRHH
    "reclutamiento", "selección", "recursos humanos", "hr data",
    "people partner", "talento humano", "experiencia del colaborador",
    # Desarrollo de software
    "programador", "developer", "fullstack", "backend", "frontend",
    "genexus", "bantotal", "visual studio",
    # Operativo
    "químico", "mantenimiento", "combustible", "logística",
    "abastecimiento", "inventarios", "almacén",
    # Tech no analytics
    "ciberseguridad", "seguridad de la información", "qa automatizador",
    "sistema junior",
    # Nivel
    "practicante",
    # Contable
    "auditoría",
    # Agregar a la lista existente
    "maintenance", "diseño grafico", "ehs", "development analyst",
    "desarrollo docente", "docente", "planeamiento financiero",
    "gasto industrial", "seguros sr",
    # Finanzas / contabilidad / tesorería
    "contable", "nómina", "nomina", "treasury", "cash administration",
    "tributari", "tesorería", "tesoreria", "facturación", "facturacion",

    # Supply / logística
    "logística", "logistica", "compras", "flota", "supply chain",
    "planner ruta", "producción", "produccion", "demanda operativ",

    # RRHH / legal / admin
    "asistente legal", "capacitación", "capacitacion",
    "administrativo", "administrador",

    # Soporte TI
    "power builder", "soporte operativo", "soporte comercial", "infraestructura",

    # Créditos operativos
    "créditos", "creditos", "cobranza", "cartera mora", "riesgo operativo",

    # Seniority no aplica
    "assistant", "intern", "practicante", "trainee", "manager",
    "director", "head of", "gerente", "jefe",
        
    ]

# Empresas internacionales donde junior puede ser middle
EMPRESAS_INTERNACIONALES = [
    "citi", "nestlé", "nestle", "abbott", "mondelez", "mondelēz",
    "scotiabank", "bbva", "interbank", "bcp", "hsbc", "jp morgan",
    "accenture", "deloitte", "pwc", "kpmg", "ernst", "mckinsey",
]

def is_junior_internacional(row):
    titulo = str(row["title"]).lower()
    empresa = str(row["company"]).lower()
    
    es_junior = any(j in titulo for j in ["junior", " jr", "jr.", "jr "])
    es_internacional = any(e in empresa for e in EMPRESAS_INTERNACIONALES)
    
    return es_junior and es_internacional


def calcular_dias_publicado(row):
    """
    Devuelve días desde publicación como int, o None si no hay dato.
    - LinkedIn/Indeed: usa 'date_posted' (formato ISO YYYY-MM-DD)
    - Bumeran/Workday: usa 'fecha_texto' (ej: 'Publicado hace 3 días')
    - Computrabajo: usa 'fecha_texto' (ej: 'Hace 2 días', 'Hace 1 hora' → 0 días)
    - Sin dato: devuelve None (conservador — no descartamos)
    """
    site = str(row.get("site", "")).lower()

    if site in ("linkedin", "indeed"):
        date_val = row.get("date_posted")
        if pd.isna(date_val) or date_val == "":
            return None
        try:
            fecha = pd.to_datetime(date_val).date()
            return (datetime.now().date() - fecha).days
        except Exception:
            return None

    if site in ("bumeran", "workday"):
        texto = str(row.get("fecha_texto", ""))
        match = re.search(r"hace (?:más de )?(\d+) d[íi]a", texto)
        if match:
            return int(match.group(1))
        return None

    if site == "computrabajo":
        texto = str(row.get("fecha_texto", "")).lower()
        match_dias = re.search(r"hace\s+(\d+)\s+d[íi]a", texto)
        if match_dias:
            return int(match_dias.group(1))
        if "hora" in texto or "minuto" in texto:
            return 0
        return None

    return None


def es_ghost_job(row):
    """Devuelve True si la oferta lleva más de 30 días publicada."""
    dias = calcular_dias_publicado(row)
    return dias is not None and dias > 30


def filtrar_por_fecha_texto(df, dias=3):
    """Filtra Bumeran y Computrabajo por fecha_texto (fuentes sin date_posted ISO)."""
    mask = df["site"].isin(["bumeran", "computrabajo"])
    df_texto = df[mask].copy()
    df_otros = df[~mask].copy()
    df_texto["dias_publicado"] = df_texto.apply(calcular_dias_publicado, axis=1)
    mask_reciente = (df_texto["dias_publicado"] <= dias) | (df_texto["dias_publicado"].isna())
    df_texto_filtrado = df_texto[mask_reciente].copy()
    descartados = len(df_texto) - len(df_texto_filtrado)
    print(f"Bumeran+Computrabajo — filtro de fecha ({dias} días): {len(df_texto_filtrado)} de {len(df_texto)} ({descartados} descartados)")
    return pd.concat([df_otros, df_texto_filtrado], ignore_index=True)

def filtrar_por_fecha(df, dias=3):
    df["date_posted"] = pd.to_datetime(df["date_posted"], errors="coerce")
    
    cutoff = datetime.now() - timedelta(days=dias)
    
    mask_reciente = (df["date_posted"] >= cutoff) | (df["date_posted"].isna())
    
    df_filtrado = df[mask_reciente].copy()
    descartados = len(df) - len(df_filtrado)
    print(f"Después de filtro de fecha ({dias} días): {len(df_filtrado)} ({descartados} descartados)")
    
    return df_filtrado


def filtrar_getonboard_por_ubicacion(df):
    """
    Filtra ofertas de Get on Board por ubicación y modalidad.
    Mantiene:
      - País = Perú (cualquier modalidad)
      - Modalidad = Remoto SIN restricción de residencia (politica_remota no menciona país)
    Descarta:
      - País != Perú + Híbrido
      - País != Perú + Remoto sólo localmente
      - País != Perú + Presencial
    """
    mask_gob = df["site"] == "getonboard"
    df_gob = df[mask_gob].copy()
    df_otros = df[~mask_gob].copy()

    if df_gob.empty:
        return df

    def aplica(row):
        pais = str(row.get("pais_code", "")).lower()
        modalidad = str(row.get("modalidad", "")).lower()
        politica = str(row.get("politica_remota", "")).lower()

        # Perú → siempre mantener
        if pais == "pe":
            return True

        # Remoto global → mantener (politica no menciona residencia en un país específico)
        if "remoto" in modalidad and "resid" not in politica and "localmente" not in politica:
            return True

        return False

    mask_aplica = df_gob.apply(aplica, axis=1)
    df_gob_filtrado = df_gob[mask_aplica].copy()

    descartados = len(df_gob) - len(df_gob_filtrado)
    print(f"GetOnBoard — filtro ubicación/modalidad: {len(df_gob_filtrado)} de {len(df_gob)} ({descartados} descartados)")

    return pd.concat([df_otros, df_gob_filtrado], ignore_index=True)

def pre_filter(csv_path="results/metadata_raw.csv"):
    jobs = pd.read_csv(csv_path)
    total_original = len(jobs)
    
    # Filtro 1 — descarte por palabras en título
    def tiene_descarte(titulo):
        titulo_lower = str(titulo).lower()
        return any(palabra in titulo_lower for palabra in DESCARTE_TITULO)
    
    mask_descarte = jobs["title"].apply(tiene_descarte)
    jobs_filtrados = jobs[~mask_descarte].copy()
    print(f"Después de filtro por título: {len(jobs_filtrados)} ({total_original - len(jobs_filtrados)} descartados)")
    
    # Filtro 2 — junior en empresas peruanas
    def es_junior_peruano(row):
        titulo = str(row["title"]).lower()
        empresa = str(row["company"]).lower()
        es_junior = any(j in titulo for j in ["junior", " jr", "jr.", "jr "])
        es_internacional = any(e in empresa for e in EMPRESAS_INTERNACIONALES)
        return es_junior and not es_internacional
    
    mask_junior = jobs_filtrados.apply(es_junior_peruano, axis=1)
    jobs_filtrados = jobs_filtrados[~mask_junior].copy()
    print(f"Después de filtro junior peruano: {len(jobs_filtrados)} ({mask_junior.sum()} descartados)")

    # Filtro 3 — deduplicar por título + empresa
    antes = len(jobs_filtrados)
    jobs_filtrados = jobs_filtrados.drop_duplicates(subset=["title", "company"])
    print(f"Después de deduplicar título+empresa: {len(jobs_filtrados)} ({antes - len(jobs_filtrados)} descartados)")

    # Filtro 4 — fecha reciente (≤ 3 días)
    jobs_filtrados = jobs_filtrados.reset_index(drop=True)
    jobs_filtrados = filtrar_por_fecha(jobs_filtrados, dias=3)
    jobs_filtrados = filtrar_por_fecha_texto(jobs_filtrados, dias=3)

    # Filtro 5 — ghost jobs (> 30 días)
    antes = len(jobs_filtrados)
    mask_ghost = jobs_filtrados.apply(es_ghost_job, axis=1)
    jobs_filtrados = jobs_filtrados[~mask_ghost].copy()
    descartados_ghost = antes - len(jobs_filtrados)
    print(f"Después de filtro ghost jobs (> 30 días): {len(jobs_filtrados)} ({descartados_ghost} descartados)")

    # Filtro 6 — Get on Board: ubicación y modalidad
    jobs_filtrados = filtrar_getonboard_por_ubicacion(jobs_filtrados)
    
    jobs_filtrados.to_csv("results/metadata_filtered.csv", index=False)
    
    print(f"\nTotal final: {len(jobs_filtrados)} de {total_original} ofertas")
    print("\nOfertas por fuente después del filtro:")
    print(jobs_filtrados["site"].value_counts())
    
    return jobs_filtrados

if __name__ == "__main__":
    pre_filter()
