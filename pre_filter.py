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


def extraer_dias_bumeran(description):
    if pd.isna(description):
        return None
    
    # Busca patrones como "hace 3 días", "hace 1 día", "hace más de 15 días"
    match = re.search(r'hace (?:más de )?(\d+) d[íi]a', str(description))
    if match:
        return int(match.group(1))
    return None

def filtrar_bumeran_por_fecha(df, dias=3):
    mask_bumeran = df["site"] == "bumeran"
    
    df_bumeran = df[mask_bumeran].copy()
    df_otros = df[~mask_bumeran].copy()
    
    def extraer_dias(texto):
        if pd.isna(texto):
            return None
        match = re.search(r'hace (?:más de )?(\d+) d[íi]a', str(texto))
        if match:
            return int(match.group(1))
        return None
    
    # Usar fecha_texto en vez de description
    df_bumeran["dias_publicado"] = df_bumeran["fecha_texto"].apply(extraer_dias)
    
    mask_reciente = (df_bumeran["dias_publicado"] <= dias) | (df_bumeran["dias_publicado"].isna())
    df_bumeran_filtrado = df_bumeran[mask_reciente].copy()
    
    descartados = len(df_bumeran) - len(df_bumeran_filtrado)
    print(f"Bumeran — filtro de fecha ({dias} días): {len(df_bumeran_filtrado)} de {len(df_bumeran)} ({descartados} descartados)")
    
    return pd.concat([df_otros, df_bumeran_filtrado], ignore_index=True)

def filtrar_por_fecha(df, dias=3):
    # Convertir date_posted a datetime
    df["date_posted"] = pd.to_datetime(df["date_posted"], errors="coerce")
    
    cutoff = datetime.now() - timedelta(days=dias)
    
    # Mantener ofertas recientes O sin fecha (Bumeran)
    mask_reciente = (df["date_posted"] >= cutoff) | (df["date_posted"].isna())
    
    df_filtrado = df[mask_reciente].copy()
    descartados = len(df) - len(df_filtrado)
    print(f"Después de filtro de fecha ({dias} días): {len(df_filtrado)} ({descartados} descartados)")
    
    return df_filtrado

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

    # Filtro 4 — fecha
    jobs_filtrados = jobs_filtrados.reset_index(drop=True)
    jobs_filtrados = filtrar_por_fecha(jobs_filtrados, dias=3)
    jobs_filtrados = filtrar_bumeran_por_fecha(jobs_filtrados, dias=3)
    
    jobs_filtrados.to_csv("results/metadata_filtered.csv", index=False)
    
    print(f"\nTotal final: {len(jobs_filtrados)} de {total_original} ofertas")
    print("\nOfertas por fuente después del filtro:")
    print(jobs_filtrados["site"].value_counts())
    
    return jobs_filtrados

if __name__ == "__main__":
    pre_filter()