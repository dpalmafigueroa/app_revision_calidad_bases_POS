# --- validador_app.py ---
# Versión Atlantia 2.30 (Ajustes Geo, Reporte Abiertas V8 y V14 Conteo Demos)

import streamlit as st
import pandas as pd
import locale
import io # Para leer los archivos subidos
import numpy as np # Para manejar tipos numéricos
from io import BytesIO # Para crear Excel en memoria
from collections import Counter # Para manejar duplicados

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="Auditor de calidad de bases de datos")

# --- Función para convertir DataFrame a Excel en memoria ---
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Reglas')
    processed_data = output.getvalue()
    return processed_data

# --- NUEVA FUNCIÓN PARA DATAFRAME DE MAPEO (v2.27) ---
def create_mapping_dataframe(mapping_dict, paises_list):
    """
    Convierte el diccionario anidado COLUMN_MAPPING en un DataFrame plano
    para su descarga.
    """
    records = []
    # Iterar sobre las bases (Numérica, Textual)
    for base_name, mappings in mapping_dict.items():
        # Iterar sobre las columnas estándar (Unico, [age], etc.)
        for standard_col, country_map in mappings.items():
            record = {
                'Base': base_name,
                'Columna Estándar (Usada en código)': standard_col
            }
            # Iterar sobre la lista de países para mantener el orden
            for pais in paises_list:
                # Obtener el nombre específico del país; usar '-' si no existe
                record[pais] = country_map.get(pais, '-')
            records.append(record)
    
    # Crear DataFrame
    df = pd.DataFrame(records)
    
    # Ordenar columnas
    column_order = ['Base', 'Columna Estándar (Usada en código)'] + paises_list
    df = df[column_order]
    
    return df

# --- FUNCIÓN PARA MANEJAR COLUMNAS DUPLICADAS ---
def deduplicate_columns(df, operation_name="lectura"):
    """
    Renombra columnas duplicadas añadiendo un sufijo numérico (.1, .2, etc.).
    Asegura que todos los nombres de columnas sean strings.
    """
    cols = pd.Series(df.columns)
    counts = Counter(cols)
    new_cols = []
    col_counts_so_far = Counter()
    renamed_info = [] # Para almacenar info de renombrado

    for col in cols:
        count = counts[col]
        original_col_name = col # Guardar nombre original por si acaso
        # Asegurarse que es string para evitar errores con nombres numéricos
        col_str = str(col) 

        if count > 1:
            suffix_num = col_counts_so_far[col_str]
            if suffix_num > 0: # Solo añadir sufijo a partir de la segunda ocurrencia
                new_name = f"{col_str}.{suffix_num}"
                new_cols.append(new_name)
                # Registrar info de renombrado solo una vez por nombre original
                is_already_registered = any(r[0] == original_col_name for r in renamed_info)
                if not is_already_registered:
                    renamed_info.append((original_col_name, new_name))
            else:
                new_cols.append(col_str) # La primera se queda igual (como string)
            col_counts_so_far[col_str] += 1
        else:
            new_cols.append(col_str) # Si no está duplicada, se queda igual (como string)

    df.columns = new_cols
    # Advertir si se renombraron columnas
    if renamed_info:
        renamed_originals = list(set([str(r[0]) for r in renamed_info])) # Convertir a string para join
        st.warning(f"Se detectaron y renombraron columnas duplicadas en el archivo durante la {operation_name}: {', '.join(renamed_originals)}. Se usará la primera ocurrencia para el mapeo.")
    return df
# --- FIN FUNCIÓN DUPLICADOS ---


# --- CSS PERSONALIZADO ---
# (Mismo CSS que versiones anteriores)
atlantia_css = """
<style>
    /* ... (pega aquí TODO el CSS) ... */
     /* Importar fuentes Atlantia */
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Hind:wght@400;500;600&display=swap');

    /* Variables de colores Atlantia (Fijos) */
    :root {
        --atlantia-violet: #6546C3;
        --atlantia-purple: #AA49CA;
        --atlantia-lemon: #77C014;
        --atlantia-turquoise: #04D1CD;
        --atlantia-white: #FFFFFF;
        --atlantia-green: #23B776;
        --atlantia-yellow: #FFB73B;
        --atlantia-orange: #FF9231;
        --atlantia-red: #E61252;
        /* Colores pastel para validación */
        --validation-correct-bg: #E8F5E9;
        --validation-correct-border: #4CAF50;
        --validation-correct-text: #1B5E20;
        --validation-incorrect-bg: #FFEBEE;
        --validation-incorrect-border: #F44336;
        --validation-incorrect-text: #B71C1C;
        --validation-info-bg: #E3F2FD;
        --validation-info-border: #2196F3;
        --validation-info-text: #0D47A1;
        --validation-error-bg: #FFF3E0;
        --validation-error-border: #FF9800;
        --validation-error-text: #E65100;

        /* --- Variables ADAPTATIVAS Claro/Oscuro --- */
        /* Tema Claro (Por defecto) */
        --text-color: #0E1117; /* Streamlit's default dark text */
        --text-color-subtle: #555;
        --bg-color: #FFFFFF;
        --secondary-bg-color: #F0F2F6; /* Streamlit's light secondary bg */
        --widget-bg: #FFFFFF;
        --input-border-color: #CCCCCC;
        --table-header-bg: #F0F2F6;
        --table-row-even-bg: #FFFFFF;
        --table-border-color: #E0E0E0;
    }

    /* Tema Oscuro (Sobrescribe variables) */
    html[data-theme="dark"] {
        --text-color: #FAFAFA; /* Streamlit's default light text */
        --text-color-subtle: #a0a0a0;
        --bg-color: #0E1117; /* Streamlit's dark bg */
        --secondary-bg-color: #1c202a; /* Darker secondary bg */
        --widget-bg: #262730; /* Streamlit's dark widget bg */
        --input-border-color: #555;
        --table-header-bg: #222733;
        --table-row-even-bg: #2a303e;
        --table-border-color: #444;

        /* Ajustar fondos pastel para mejor contraste en oscuro */
        --validation-correct-bg: #1c3d1e;
        --validation-incorrect-bg: #4d1f23;
        --validation-info-bg: #1a3a57;
        --validation-error-bg: #4d3a1e;
        /* Ajustar texto pastel si es necesario */
        --validation-correct-text: #b8f5b9;
        --validation-incorrect-text: #f7c5c7;
        --validation-info-text: #bce3ff;
        --validation-error-text: #ffe0b3;
    }

    /* Ocultar menú y footer */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Tipografía base (Usa variable adaptativa) */
    body, * {
        font-family: 'Hind', sans-serif;
        color: var(--text-color);
    }
    .stApp { background-color: var(--bg-color); }

    /* Títulos Atlantia (Color fijo) */
    h1, .main-title, h2, .section-title, h3, .subsection-title {
        font-family: 'Poppins', sans-serif !important;
        font-weight: 700 !important;
        color: var(--atlantia-violet) !important;
    }
    h1, .main-title { font-size: 24pt !important; }
    h2, .section-title { font-size: 20pt !important; }
    h3, .subsection-title { font-size: 16pt !important; }

    /* Labels Atlantia (Color fijo) */
    .stSelectbox label, .stTextInput label, .stTextArea label, .stFileUploader label,
    .indicator-subtitle, .metric-label, .stMetric label, .stExpander summary {
        font-family: 'Hind', sans-serif !important;
        font-weight: 600 !important;
        font-size: 14pt !important;
        color: var(--atlantia-violet) !important;
    }

    /* Cuerpo de texto (Usa variable adaptativa) */
    p, .body-text, .stMarkdown, .stText, label, div[data-baseweb="select"] > div, .stAlert * {
        font-family: 'Hind', sans-serif !important;
        font-weight: 400 !important;
        font-size: 12pt !important;
        color: var(--text-color) !important;
    }
    .stExpander div[data-baseweb="block"] > div { color: var(--text-color) !important; }

    /* Botones */
    .stButton button { font-family: 'Hind', sans-serif !important; font-weight: 600 !important; font-size: 12pt !important; border-radius: 8px !important; }

    /* Inputs y Select (Adaptativo) */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    div[data-baseweb="select"] > div {
        border: 1px solid var(--input-border-color) !important;
        background-color: var(--widget-bg) !important;
        color: var(--text-color) !important;
        border-radius: 8px !important;
    }
     .stTextInput > div > div > input:focus,
     .stTextArea > div > div > textarea:focus {
         border-color: var(--atlantia-violet) !important;
         box-shadow: 0 0 0 2px rgba(101, 70, 195, 0.3) !important;
     }

    /* File Uploader (Adaptativo) */
    .stFileUploader > div > div {
         border: 2px dashed var(--atlantia-violet) !important;
         background-color: var(--secondary-bg-color) !important;
         border-radius: 10px !important;
     }
     .stFileUploader label span {
         color: var(--text-color) !important;
     }

    /* Expander (Adaptativo) */
    .streamlit-expanderHeader {
         background-color: var(--secondary-bg-color) !important;
         border: 1px solid var(--input-border-color) !important;
         border-radius: 8px !important;
    }
    .streamlit-expanderHeader p {
         color: var(--atlantia-violet) !important;
    }

    /* Métricas (Adaptativo) */
    .stMetric {
         background-color: var(--widget-bg);
         border: 1px solid var(--input-border-color);
         border-radius: 8px;
         padding: 10px 15px;
     }
     .stMetric > label { color: var(--atlantia-violet) !important; }
     .stMetric > div[data-testid="stMetricValue"] { color: var(--text-color) !important; }
     .stMetric > div[data-testid="stMetricDelta"] { color: var(--text-color-subtle) !important; }

    /* --- ESTILOS DE VALIDACIÓN (Adaptativos) --- */
    .validation-box {
        border: 1px solid var(--input-border-color);
        border-left-width: 5px !important;
        border-radius: 8px; padding: 16px; margin-bottom: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05); line-height: 1.6;
    }
    .validation-box h3 { border-bottom: 1px solid var(--input-border-color); color: var(--atlantia-violet); } /* Título principal violeta */
    .validation-box h3.sub-heading { color: var(--text-color-subtle); border-bottom-style: dotted; }

    /* Estados */
    .status-correcto { background-color: var(--validation-correct-bg); border-left-color: var(--validation-correct-border); }
    .status-correcto h3, .status-correcto span, .status-correcto p, .status-correcto li { color: var(--validation-correct-text) !important; }
    .status-correcto-inline { color: var(--validation-correct-text) !important; font-weight: bold; }

    .status-incorrecto { background-color: var(--validation-incorrect-bg); border-left-color: var(--validation-incorrect-border); }
    .status-incorrecto h3, .status-incorrecto span, .status-incorrecto p, .status-incorrecto li, .status-incorrecto .df-style th, .status-incorrecto .df-style td { color: var(--validation-incorrect-text) !important; }
    .status-incorrecto-inline { color: var(--validation-incorrect-text) !important; font-weight: bold; }

    .status-info { background-color: var(--validation-info-bg); border-left-color: var(--validation-info-border); }
    .status-info h3, .status-info span, .status-info p, .status-info li, .status-info .df-style th, .status-info .df-style td { color: var(--validation-info-text) !important; }
    .status-info-inline { color: var(--validation-info-text) !important; font-weight: bold; } /* Añadido para V13 */


    .status-error { background-color: var(--validation-error-bg); border-left-color: var(--validation-error-border); }
    .status-error h3, .status-error span, .status-error p, .status-error li, .status-error .df-style th, .status-error .df-style td { color: var(--validation-error-text) !important; }
    .status-error-inline { color: var(--validation-error-text) !important; font-weight: bold; }

     /* Tablas dentro de validación */
    .df-style { border-collapse: collapse; width: 95%; margin: 10px auto; font-size: 0.9em; }
    .df-style th, .df-style td { border: 1px solid var(--table-border-color); padding: 6px; color: var(--text-color) !important; }
    .df-style th { background-color: var(--table-header-bg); text-align: left; font-weight: bold; }
    .df-style tr:nth-child(even) { background-color: var(--table-row-even-bg); }
    /* Override para tablas dentro de cajas de estado */
    .status-incorrecto .df-style th, .status-incorrecto .df-style td { color: var(--validation-incorrect-text) !important; border-color: rgba(183, 28, 28, 0.3); }
    .status-incorrecto .df-style th { background-color: rgba(183, 28, 28, 0.1); }
    .status-error .df-style th, .status-error .df-style td { color: var(--validation-error-text) !important; border-color: rgba(230, 81, 0, 0.3); }
    .status-error .df-style th { background-color: rgba(230, 81, 0, 0.1); }
    .status-info .df-style th, .status-info .df-style td { color: var(--validation-info-text) !important; border-color: rgba(13, 71, 161, 0.3); }
    .status-info .df-style th { background-color: rgba(13, 71, 161, 0.1); }


    /* Resumen Lista */
    .summary-list ul { list-style-type: none; padding-left: 0; }
    .summary-list li { padding: 5px 0; border-bottom: 1px dotted var(--input-border-color); }
    .summary-list li strong { color: var(--atlantia-violet); }

    /* Header principal */
    .main-header-container { margin-bottom: 2rem; }
    .main-header { text-align: center; padding: 1rem 0; background: linear-gradient(135deg, var(--atlantia-violet) 0%, var(--atlantia-purple) 100%); border-radius: 15px; color: white; }
    .main-header h1 { color: white !important; font-family: 'Poppins', sans-serif !important; font-weight: 700 !important; font-size: 24pt !important; margin-bottom: 0.2rem; }
    .main-header .subtitle { color: rgba(255, 255, 255, 0.9) !important; font-family: 'Poppins', sans-serif !important; font-weight: 500 !important; font-size: 14pt !important; margin-top: 0; }
    .atlantia-logo { width: 40px; height: auto; vertical-align: middle; margin-right: 0.5rem; }
</style>
"""
st.markdown(atlantia_css, unsafe_allow_html=True)

# --- HEADER PERSONALIZADO ---
st.markdown('<div class="main-header-container">', unsafe_allow_html=True)
st.markdown("""
<div class="main-header">
    <svg class="atlantia-logo" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg"><defs><linearGradient id="atlantiaGradient" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" style="stop-color:#04D1CD"/><stop offset="50%" style="stop-color:#6546C3"/><stop offset="100%" style="stop-color:#AA49CA"/></linearGradient></defs><path d="M20,80 L50,20 L80,80 L65,80 L50,50 L35,80 Z" fill="url(#atlantiaGradient)" stroke="white" stroke-width="2"/></svg>
    <h1 style="display: inline-block; vertical-align: middle;">Auditor de calidad de bases de datos</h1>
    <div class="subtitle">Powered by Atlantia</div>
</div>
""", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# --- INSTRUCCIONES ---
st.markdown("## Instrucciones")
st.markdown("""1.  **Selecciona el país** para el cual se aplicarán las reglas geográficas y de volumetría.\n2.  **Carga los archivos Excel** correspondientes a la base numérica y textual.""")
st.markdown("### Evaluaciones Realizadas:")
st.markdown("""
* **Tamaño:** Compara filas y columnas.
* **Orden de IDs:** Verifica `Unico` vs `[auth]`.
* **Unico valor en (lastpage, lastpage2 y lastpage3):** Revisa unicidad.
* **Periodo de Campo:** Muestra fechas de `startdate`.
* **Agrupaciones:** Rango de edad vs `[age]`, `NSE` vs `NSE2`, Geografía (Región/Ciudad). (Perú incluye validación `region2`).
* **Origen/Proveedor:** Conteo por proveedor.
* **Nulos (Numérica):** Busca vacíos en `NSE`, `gender`, `AGErange`, `Region`.
* **Abiertas ('Menciona'):** Lista respuestas (ID, Pregunta, Respuesta).
* **Ponderador (Numérica):** Compara suma `Ponderador` vs total filas.
* **Suma Ponderador por demográfico:** Suma `Ponderador` por `NSE`, `gender`, `AGErange`, `Region` y muestra porcentajes.
* **Volumetría (Numérica):** Valida columnas contra umbrales definidos por país.
* **Duplicados en IDs:** Verifica que `Unico` (Num) y `[auth]` (Txt) no tengan valores repetidos.
* **Duplicados [panelistid]:** Reporta (Info) `[panelistid]` (Txt) duplicados y su conteo.
* **Conteo de Demográficos:** Reporta (Info) conteo y % de `gender`, `AGErange`, `NSE` y `Region`.
""")
st.divider()

# --- CONFIGURACIÓN DE REGLAS ---
CLASIFICACIONES_POR_PAIS = {
    # --- AJUSTE 1: 'Guacala' -> 'Gualaca' ---
    'Panamá': {'Centro': ['Aguadulce', 'Antón', 'La Pintada', 'Natá', 'Olá', 'Penonomé','Chagres', 'Ciudad de Colón', 'Colón', 'Donoso', 'Portobelo','Resto del Distrito', 'Santa Isabel', 'La Chorrera', 'Arraiján','Capira', 'Chame', 'San Carlos'],'Metro': ['Panamá', 'San Miguelito', 'Balboa', 'Chepo', 'Chimán', 'Taboga', 'Chepigana', 'Pinogana'],'Oeste': ['Alanje', 'Barú', 'Boquerón', 'Boquete', 'Bugaba', 'David', 'Dolega', 'Gualaca', 'Remedios', 'Renacimiento', 'San Félix', 'San Lorenzo', 'Tolé', 'Bocas del Toro', 'Changuinola', 'Chiriquí Grande', 'Chitré', 'Las Minas', 'Los Pozos', 'Ocú', 'Parita', 'Pesé', 'Santa María', 'Guararé', 'Las Tablas', 'Los Santos', 'Macaracas', 'Pedasí', 'Pocrí', 'Tonosí', 'Atalaya', 'Calobre', 'Cañazas', 'La Mesa', 'Las Palmas', 'Mariato', 'Montijo', 'Río de Jesús', 'San Francisco', 'Santa Fé', 'Santiago', 'Soná']},
    'México': {'Central/Bajío': ['CDMX + AM', 'Estado de México', 'Guanajuato', 'Hidalgo','Morelos', 'Puebla', 'Querétaro', 'Tlaxcala'],'Norte': ['Baja California Norte', 'Chihuahua', 'Coahuila','Durango', 'Nuevo León', 'Sonora', 'Tamaulipas'],'Occidente/Pacifico': ['Aguascalientes', 'Baja California Sur', 'Colima', 'Guerrero', 'Jalisco', 'Michoacan','Nayarit', 'San Luis Potosi', 'Sinaloa', 'Zacatecas'],'Sureste': ['Campeche', 'Chiapas', 'Oaxaca', 'Quintana Roo', 'Tabasco','Veracruz', 'Yucatán']},
    'Colombia': {'Andes': ['Antioquia', 'Caldas', 'Quindio', 'Risaralda', 'Santander'],'Centro': ['Bogotá', 'Boyacá', 'Casanare', 'Cundinamarca'],'Norte': ['Atlántico', 'Bolívar', 'Cesar', 'Córdoba', 'La Guajira', 'Magdalena', 'Norte de Santader', 'Sucre'], 'Sur': ['Cauca', 'Huila', 'Meta', 'Nariño', 'Tolima', 'Valle de Cauca']},
    # --- AJUSTE 2: 'Tungahua' -> 'Tungurahua' ---
    'Ecuador': {'Costa': ['El Oro', 'Esmeraldas', 'Los Ríos', 'Manabí', 'Santa Elena', 'Santo Domingo de los Tsáchilas'],'Guayaquil': ['Guayas'],'Quito': ['Pichincha'],'Sierra': ['Azuay', 'Bolívar', 'Cañar', 'Carchi', 'Chimborazo', 'Cotopaxi', 'Imbabura', 'Loja', 'Tungurahua']},
    
    # (v2.28 - Ica y Huánuco a Centro)
    'Perú': {
        'Centro': ['Ayacucho', 'Huancavelica', 'Junín', 'Ica', 'Huánuco'],
        'Lima y Callao': ['Lima', 'Callao'],
        'Norte': ['Áncash', 'Cajamarca', 'La Libertad', 'Lambayeque', 'Piura', 'Tumbes'],
        'Oriente': ['Amazonas', 'Loreto', 'Pasco', 'San Martin', 'Ucayali'],
        'Sur': ['Apurimac', 'Arequipa', 'Cuzco', 'Madre de Dios', 'Moquegua', 'Puno', 'Tacna']
    },
    
    'R. Dominicana': {'Capital': ['Distrito Nacional', 'Santo Domingo'],'Region Este': ['El Seibo', 'Hato Mayor', 'La Altagracia', 'La Romana', 'Monte Plata', 'San Pedro de Macorís'],'Region norte/ Cibao': ['Dajabón', 'Duarte (San Francisco)', 'Espaillat', 'Hermanas Mirabal', 'La Vega', 'María Trinidad Sánchez', 'Monseñor Nouel', 'Montecristi', 'Puerto Plata', 'Samaná', 'Sánchez Ramírez', 'Santiago', 'Santiago Rodríguez', 'Valverde'],'Region Sur': ['Azua', 'Bahoruco', 'Barahona', 'Elías Piña', 'Independencia', 'Pedernales', 'Peravia', 'San Cristóbal', 'San José de Ocoa', 'San Juan']},
    'Honduras': {'Norte Ciudad': ['Cortés'],'Norte interior': ['Atlántida', 'Colón', 'Copán', 'Ocotepeque', 'Santa Bárbara', 'Yoro'],'Sur Ciudad': ['Francisco Morazán'],'Sur interior': ['Choluteca', 'Comayagua', 'El Paraíso', 'Intibucá', 'La Paz', 'Olancho', 'Valle']},
    'Guatemala': { # Estructura v2.19 (5 Regiones, Escuintla en Sur Occidente)
        'Metro': ['Guatemala'],
        'Nor Oriente': ['Petén', 'Alta Verapaz', 'Zacapa', 'El Progreso', 'Izabal', 'Baja Verapaz'],
        'Nor Occidente': ['San Marcos', 'Quetzaltengango', 'Chimaltenango', 'Quiché', 'Totonicapán', 'Huehuetenango', 'Sololá', 'Sacatepequez'],
        'Sur Occidente': ['Suchitepéquez', 'Retalhuleu', 'Escuintla'],
        'Sur Oriente': ['Chiquimula', 'Jutiapa', 'Jalapa', 'Santa Rosa']
    },
    'El Salvador': {'AMSS': ['San Salvador'],'Centro': ['Cabañas', 'Chalatenango', 'Cuscatlán', 'La Libertad', 'La Paz', 'San Vicente'],'Occidente': ['Ahuachapán', 'Santa Ana', 'Sonsonate'],'Oriente': ['La Union', 'Morazán', 'San Miguel', 'Usulután']},
    'Costa Rica': {}, 'Puerto Rico': {},
    # --- INICIO MODIFICACIÓN SOLICITADA ---
    # Se iguala Colombia Minors a Colombia
    'Colombia Minors': {'Andes': ['Antioquia', 'Caldas', 'Quindio', 'Risaralda', 'Santander'],'Centro': ['Bogotá', 'Boyacá', 'Casanare', 'Cundinamarca'],'Norte': ['Atlántico', 'Bolívar', 'Cesar', 'Córdoba', 'La Guajira', 'Magdalena', 'Norte de Santader', 'Sucre'], 'Sur': ['Cauca', 'Huila', 'Meta', 'Nariño', 'Tolima', 'Valle de Cauca']}
    # --- FIN MODIFICACIÓN SOLICITADA ---
}

# --- INICIO CORRECCIÓN PERÚ GEO R2 v2.29 (Actualización completa R2) ---
CLASIFICACIONES_PERU_REGION2 = {
    'LIMA': ['Lima', 'Callao', 'Ica'],
    'NORTE': ['La Libertad', 'Lambayeque', 'Piura', 'Cajamarca', 'Áncash', 'Tumbes'],
    'CENTRO': ['Junín', 'Ayacucho', 'Huancavelica'],
    'SUR': ['Arequipa', 'Cuzco', 'Puno', 'Tacna', 'Moquegua', 'Apurimac', 'Madre de Dios'],
    'ORIENTE': ['Loreto', 'Huánuco', 'San Martin', 'Pasco', 'Ucayali', 'Amazonas']
}
# --- FIN CORRECCIÓN PERÚ GEO R2 v2.29 ---

THRESHOLDS_POR_PAIS = {
    # (Igual que V1.8)
    'México': [{'col': 'Total_consumo', 'cond': 'mayor_a', 'lim': 11000}, {'col': 'Total_consumo', 'cond': 'igual_a', 'lim': 0},{'col': 'Beer', 'cond': 'mayor_a', 'lim': 7000},{'col': 'Wine', 'cond': 'mayor_a', 'lim': 3000},{'col': 'Spirits', 'cond': 'mayor_a', 'lim': 1400},{'col': 'Other_alc', 'cond': 'mayor_a', 'lim': 1400},{'col': 'CSDs', 'cond': 'mayor_a', 'lim': 5000},{'col': 'Energy_drinks', 'cond': 'mayor_a', 'lim': 1400}],
    'Colombia': [{'col': 'Total_consumo', 'cond': 'mayor_a', 'lim': 11000}, {'col': 'Total_consumo', 'cond': 'igual_a', 'lim': 0},{'col': 'Beer', 'cond': 'mayor_a', 'lim': 7000},{'col': 'Wine', 'cond': 'mayor_a', 'lim': 3000},{'col': 'Spirits', 'cond': 'mayor_a', 'lim': 1400},{'col': 'Other_alc', 'cond': 'mayor_a', 'lim': 1400},{'col': 'CSDs', 'cond': 'mayor_a', 'lim': 3000},{'col': 'Energy_drinks', 'cond': 'mayor_a', 'lim': 1400},{'col': 'Malts', 'cond': 'mayor_a', 'lim': 2000}],
    'Ecuador': [{'col': 'Total_consumo', 'cond': 'mayor_a', 'lim': 11000}, {'col': 'Total_consumo', 'cond': 'igual_a', 'lim': 0},{'col': 'Beer', 'cond': 'mayor_a', 'lim': 7000},{'col': 'Wine', 'cond': 'mayor_a', 'lim': 3000},{'col': 'Spirits', 'cond': 'mayor_a', 'lim': 1400},{'col': 'Other_alc', 'cond': 'mayor_a', 'lim': 1400},{'col': 'CSDs', 'cond': 'mayor_a', 'lim': 3000},{'col': 'Energy_drinks', 'cond': 'mayor_a', 'lim': 1400},{'col': 'Malts', 'cond': 'mayor_a', 'lim': 2000}],
    'Perú': [{'col': 'Total_consumo', 'cond': 'mayor_a', 'lim': 11000}, {'col': 'Total_consumo', 'cond': 'igual_a', 'lim': 0},{'col': 'Beer', 'cond': 'mayor_a', 'lim': 7000},{'col': 'Wine', 'cond': 'mayor_a', 'lim': 3000},{'col': 'Spirits', 'cond': 'mayor_a', 'lim': 1400},{'col': 'Other_alc', 'cond': 'mayor_a', 'lim': 1400},{'col': 'CSDs', 'cond': 'mayor_a', 'lim': 3000},{'col': 'Energy_drinks', 'cond': 'mayor_a', 'lim': 1400},{'col': 'Malts', 'cond': 'mayor_a', 'lim': 2000}],
    'R. Dominicana': [{'col': 'Total_consumo', 'cond': 'mayor_a', 'lim': 11000},{'col': 'Total_consumo', 'cond': 'igual_a', 'lim': 0},{'col': 'Beer', 'cond': 'mayor_a', 'lim': 7000},{'col': 'Wine', 'cond': 'mayor_a', 'lim': 3000},{'col': 'Ron', 'cond': 'mayor_a', 'lim': 1400},{'col': 'Whisky', 'cond': 'mayor_a', 'lim': 1400},{'col': 'Spirits', 'cond': 'mayor_a', 'lim': 1400},{'col': 'Other_alc', 'cond': 'mayor_a', 'lim': 1400},{'col': 'CSDs', 'cond': 'mayor_a', 'lim': 3000},{'col': 'Energy_drinks', 'cond': 'mayor_a', 'lim': 1400},{'col': 'Malts', 'cond': 'mayor_a', 'lim': 2000}],
    'Honduras': [{'col': 'Total_consumo', 'cond': 'mayor_a', 'lim': 11000},{'col': 'Total_consumo', 'cond': 'igual_a', 'lim': 0},{'col': 'Beer', 'cond': 'mayor_a', 'lim': 7000},{'col': 'Wine', 'cond': 'mayor_a', 'lim': 3000},{'col': 'Spirits', 'cond': 'mayor_a', 'lim': 1400},{'col': 'Other_alc', 'cond': 'mayor_a', 'lim': 1400},{'col': 'CSDs', 'cond': 'mayor_a', 'lim': 5000},{'col': 'Energy_drinks', 'cond': 'mayor_a', 'lim': 1400},{'col': 'Malts', 'cond': 'mayor_a', 'lim': 2000}],
    'El Salvador': [{'col': 'Total_consumo', 'cond': 'mayor_a', 'lim': 11000},{'col': 'Total_consumo', 'cond': 'igual_a', 'lim': 0},{'col': 'Beer', 'cond': 'mayor_a', 'lim': 7000},{'col': 'Wine', 'cond': 'mayor_a', 'lim': 3000},{'col': 'Spirits', 'cond': 'mayor_a', 'lim': 1400},{'col': 'Other_alc', 'cond': 'mayor_a', 'lim': 1400},{'col': 'CSDs', 'cond': 'mayor_a', 'lim': 3000},{'col': 'Energy_drinks', 'cond': 'mayor_a', 'lim': 1400},{'col': 'Malts', 'cond': 'mayor_a', 'lim': 2000}],
    'Costa Rica': [{'col': 'Total_consumo', 'cond': 'mayor_a', 'lim': 11000},{'col': 'Total_consumo', 'cond': 'igual_a', 'lim': 0},{'col': 'Beer', 'cond': 'mayor_a', 'lim': 7000},{'col': 'Wine', 'cond': 'mayor_a', 'lim': 3000},{'col': 'Spirits', 'cond': 'mayor_a', 'lim': 1400},{'col': 'Other_alc', 'cond': 'mayor_a', 'lim': 1400},{'col': 'CSDs', 'cond': 'mayor_a', 'lim': 3000},{'col': 'Energy_drinks', 'cond': 'mayor_a', 'lim': 1400},{'col': 'Malts', 'cond': 'mayor_a', 'lim': 2000}],
    'Puerto Rico': [{'col': 'Total_consumo', 'cond': 'mayor_a', 'lim': 11000},{'col': 'Total_consumo', 'cond': 'igual_a', 'lim': 0},{'col': 'Beer', 'cond': 'mayor_a', 'lim': 7000},{'col': 'Wine', 'cond': 'mayor_a', 'lim': 3000},{'col': 'Spirits', 'cond': 'mayor_a', 'lim': 1400},{'col': 'Other_alc', 'cond': 'mayor_a', 'lim': 1400},{'col': 'CSDs', 'cond': 'mayor_a', 'lim': 3000},{'col': 'Energy_drinks', 'cond': 'mayor_a', 'lim': 1400},{'col': 'Malts', 'cond': 'mayor_a', 'lim': 2000}],
    'Panamá': [{'col': 'Total_consumo', 'cond': 'mayor_a', 'lim': 11000},{'col': 'Total_consumo', 'cond': 'igual_a', 'lim': 0},{'col': 'Beer', 'cond': 'mayor_a', 'lim': 7000},{'col': 'Wine', 'cond': 'mayor_a', 'lim': 3000},{'col': 'Spirits', 'cond': 'mayor_a', 'lim': 1400},{'col': 'Other_alc', 'cond': 'mayor_a', 'lim': 1400},{'col': 'CSDs', 'cond': 'mayor_a', 'lim': 3000},{'col': 'Energy_drinks', 'cond': 'mayor_a', 'lim': 1400},{'col': 'Malts', 'cond': 'mayor_a', 'lim': 2000}],
    'Guatemala': [{'col': 'Total_consumo', 'cond': 'mayor_a', 'lim': 11000},{'col': 'Total_consumo', 'cond': 'igual_a', 'lim': 0},{'col': 'Beer', 'cond': 'mayor_a', 'lim': 7000},{'col': 'Wine', 'cond': 'mayor_a', 'lim': 3000},{'col': 'Spirits', 'cond': 'mayor_a', 'lim': 1400},{'col': 'Other_alc', 'cond': 'mayor_a', 'lim': 1400},{'col': 'CSDs', 'cond': 'mayor_a', 'lim': 3000},{'col': 'Energy_drinks', 'cond': 'mayor_a', 'lim': 1400},{'col': 'Malts', 'cond': 'mayor_a', 'lim': 2000}],
    'Colombia Minors': [{'col': 'Total_consumo', 'cond': 'mayor_a', 'lim': 11000},{'col': 'Total_consumo', 'cond': 'igual_a', 'lim': 0},{'col': 'Beer', 'cond': 'mayor_a', 'lim': 7000},{'col': 'Wine', 'cond': 'mayor_a', 'lim': 3000},{'col': 'Spirits', 'cond': 'mayor_a', 'lim': 1400},{'col': 'Other_alc', 'cond': 'mayor_a', 'lim': 1400},{'col': 'CSDs', 'cond': 'mayor_a', 'lim': 3000},{'col': 'Energy_drinks', 'cond': 'mayor_a', 'lim': 1400},{'col': 'Malts', 'cond': 'mayor_a', 'lim': 2000}],
}
paises_disponibles = sorted(list(CLASIFICACIONES_POR_PAIS.keys()))

# --- (ACTUALIZADO) MAPEO DINÁMICO DE COLUMNAS ---
COLUMN_MAPPING = {
    'Base Numérica': {
        # ... (sin cambios aquí) ...
        'Unico': {'Panamá': 'Unico', 'México': 'Unico', 'Colombia': 'Unico', 'Ecuador': 'Unico', 'Perú': 'Unico', 'R. Dominicana': 'Unico', 'Honduras': 'Unico', 'El Salvador': 'Unico', 'Guatemala': 'Unico', 'Colombia Minors': 'id'},
        'lastpage': {'Panamá': 'lastpage', 'México': 'lastpage', 'Colombia': 'lastpage', 'Ecuador': 'lastpage', 'Perú': 'lastpage', 'R. Dominicana': 'lastpage', 'Honduras': 'lastpage', 'El Salvador': 'lastpage', 'Guatemala': 'lastpage', 'Colombia Minors': 'lastpage'},
        'lastpage_Parte2': {'Panamá': 'lastpage_Parte2', 'México': 'lastpage_Parte2', 'Colombia': 'lastpage_Parte2', 'Ecuador': 'lastpage_Parte2', 'Perú': 'lastpage_Parte2', 'R. Dominicana': 'lastpage_Parte2', 'Honduras': 'lastpage_Parte2', 'El Salvador': 'lastpage_Parte2', 'Guatemala': 'lastpage_Parte2', 'Colombia Minors': ''},
        'lastpage_Parte3': {'Panamá': 'lastpage_Parte3', 'México': 'lastpage_Parte3', 'Colombia': 'lastpage_Parte3', 'Ecuador': 'lastpage_Parte3', 'Perú': 'lastpage_Parte3', 'R. Dominicana': 'lastpage_Parte3', 'Honduras': 'lastpage_Parte3', 'El Salvador': 'lastpage_Parte3', 'Guatemala': 'lastpage_Parte3', 'Colombia Minors': ''},
        'Ponderador': {'Panamá': 'Ponderador', 'México': 'Ponderador', 'Colombia': 'Ponderador', 'Ecuador': 'Ponderador', 'Perú': 'Ponderador', 'R. Dominicana': 'Ponderador', 'Honduras': 'Ponderador', 'El Salvador': 'Ponderador', 'Guatemala': 'Ponderador', 'Colombia Minors': ''},
        'NSE': {'Panamá': 'NSE', 'México': 'NSE', 'Colombia': 'NSE', 'Ecuador': 'NSE', 'Perú': 'NSE', 'R. Dominicana': 'NSE', 'Honduras': 'NSE', 'El Salvador': 'NSE', 'Guatemala': 'NSE', 'Colombia Minors': 'NSE'},
        'gender': {'Panamá': 'gender', 'México': 'gender', 'Colombia': 'gender', 'Ecuador': 'gender', 'Perú': 'gender', 'R. Dominicana': 'gender', 'Honduras': 'gender', 'El Salvador': 'gender', 'Guatemala': 'gender', 'Colombia Minors': 'gender'},
        'AGErange': {'Panamá': 'AGErange', 'México': 'AGErange', 'Colombia': 'AGErange', 'Ecuador': 'AGErange', 'Perú': 'AGErange', 'R. Dominicana': 'AGErange', 'Honduras': 'AGErange', 'El Salvador': 'AGErange', 'Guatemala': 'AGErange', 'Colombia Minors': 'AGErange'},
        'Region': {'Panamá': 'Region', 'México': 'Region', 'Colombia': 'region', 'Ecuador': 'region', 'Perú': 'region', 'R. Dominicana': 'region', 'Honduras': 'region', 'El Salvador': 'region', 'Guatemala': 'region', 'Colombia Minors': 'region'},
        'Total_consumo': {'Panamá': 'Total_consumo', 'México': 'Total_consumo', 'Colombia': 'Total_consumo', 'Ecuador': 'Total_consumo', 'Perú': 'Total_consumo', 'R. Dominicana': 'Total_consumo', 'Honduras': 'Total_consumo', 'El Salvador': 'Total_consumo', 'Guatemala': 'Total_consumo', 'Colombia Minors': 'Total_consumo'},
        'Beer': {'Panamá': 'Beer', 'México': 'Beer', 'Colombia': 'Beer', 'Ecuador': 'Beer', 'Perú': 'Beer', 'R. Dominicana': 'Beer', 'Honduras': 'Beer', 'El Salvador': 'Beer', 'Guatemala': 'Beer', 'Colombia Minors': ''},
        'Wine': {'Panamá': 'Wine', 'México': 'Wine', 'Colombia': 'Wine', 'Ecuador': 'Wine', 'Perú': 'Wine', 'R. Dominicana': 'Wine', 'Honduras': 'Wine', 'El Salvador': 'Wine', 'Guatemala': 'Wine', 'Colombia Minors': ''},
        'Ron': {'R. Dominicana': 'Rum'},
        'Whisky': {'R. Dominicana': 'Wiskey'},
        'Spirits': {'Panamá': 'Spirits', 'México': 'Spirits', 'Colombia': 'Spirits', 'Ecuador': 'Spirits', 'Perú': 'Spirits', 'R. Dominicana': 'Spirits', 'Honduras': 'Spirits', 'El Salvador': 'Spirits', 'Guatemala': 'Spirits', 'Colombia Minors': ''},
        'Other_alc': {'Panamá': 'Other_alc', 'México': 'Other_alc', 'Colombia': 'Other_alc', 'Ecuador': 'Other_alc', 'Perú': 'Other_alc', 'R. Dominicana': 'Other_alc', 'Honduras': 'Other_alc', 'El Salvador': 'Other_alc', 'Guatemala': 'Other_alc', 'Colombia Minors': ''},
        'CSDs': {'Panamá': 'CSDs', 'México': 'CSDs', 'Colombia': 'CSDs', 'Ecuador': 'CSDs', 'Perú': 'CSDs', 'R. Dominicana': 'CSDs', 'Honduras': 'CSDs', 'El Salvador': 'CSDs', 'Guatemala': 'CSDs', 'Colombia Minors': 'CSDs'},
        'Energy_drinks': {'Panamá': 'Energy_drinks', 'México': 'Energy_drinks', 'Colombia': 'Energy_drinks', 'Ecuador': 'Energy_drinks', 'Perú': 'Energy_drinks', 'R. Dominicana': 'Energy_drinks', 'Honduras': 'Energy_drinks', 'El Salvador': 'Energy_drinks', 'Guatemala': 'Energy_drinks', 'Colombia Minors': 'Energy_drinks'},
        'Malts': {'Panamá': 'Malts', 'México': '', 'Colombia': 'Malts', 'Ecuador': 'Malts', 'Perú': 'Malts', 'R. Dominicana': 'Malts', 'Honduras': 'Malts', 'El Salvador': 'Malts', 'Guatemala': 'Malts', 'Colombia Minors': 'Malts'},
        'RTD_Cider': {'Panamá': 'RTD_Cider', 'México': 'RTD_Cider', 'Colombia': 'RTD_Cider', 'Ecuador': 'RTD_Cider', 'Perú': 'RTD_Cider', 'R. Dominicana': 'RTD_Cider', 'Honduras': 'RTD_Cider', 'El Salvador': 'RTD_Cider', 'Guatemala': 'RTD_Cider', 'Colombia Minors': ''},
        'Hard_Seltzer': {'Panamá': 'Hard_Seltzer', 'México': 'Hard_Seltzer', 'Colombia': 'Hard_Seltzer', 'Ecuador': 'Hard_Seltzer', 'Perú': 'Hard_Seltzer', 'R. Dominicana': 'Hard_Seltzer', 'Honduras': 'Hard_Seltzer', 'El Salvador': 'Hard_Seltzer', 'Guatemala': 'Hard_Seltzer', 'Colombia Minors': ''},
        'Bottled_water': {'Panamá': 'Bottled_water', 'México': 'Bottled_water', 'Colombia': 'Bottled_water', 'Ecuador': 'Bottled_water', 'Perú': 'Bottled_water', 'R. Dominicana': 'Bottled_water', 'Honduras': 'Bottled_water', 'El Salvador': 'Bottled_water', 'Guatemala': 'Bottled_water', 'Colombia Minors': 'Bottled_water'},
        'NABs': {'Panamá': 'NABs', 'México': 'NABs', 'Colombia': 'NABs', 'Ecuador': 'NABs', 'Perú': 'NABs', 'R. Dominicana': 'NABs', 'Honduras': 'NABs', 'El Salvador': 'NABs', 'Guatemala': 'NABs', 'Colombia Minors': 'NABs'},
        'Alcohol': {'Panamá': 'Alcohol', 'México': '', 'Colombia': 'Alcohol', 'Ecuador': 'Alcohol', 'Perú': 'Alcohol', 'R. Dominicana': 'Alcohol', 'Honduras': 'Alcohol', 'El Salvador': '', 'Guatemala': 'Alcohol', 'Colombia Minors': ''},
    },
    'Base Textual': {
        '[auth]': {'Panamá': '[auth]', 'México': '[auth]', 'Colombia': '[auth]', 'Ecuador': '[auth]', 'Perú': '[auth]', 'R. Dominicana': '[auth]', 'Honduras': '[auth]', 'El Salvador': '[auth]', 'Guatemala': '[auth]', 'Colombia Minors': 'id'},
        'startdate': {'Panamá': 'startdate', 'México': 'startdate', 'Colombia': 'startdate', 'Ecuador': 'startdate', 'Perú': 'startdate', 'R. Dominicana': 'startdate', 'Honduras': 'startdate', 'El Salvador': 'startdate', 'Guatemala': 'startdate', 'Colombia Minors': 'startdate'},
        # --- INICIO CORRECCIÓN HONDURAS EDAD v2.26 ---
        'Por favor, selecciona el rango de edad en el que te encuentras:': {
            'Panamá': 'Por favor, selecciona el rango de edad en el que te encuentras:', 
            'México': 'Por favor, selecciona el rango de edad en el que te encuentras:', 
            'Colombia': 'Por favor, selecciona el rango de edad en el que te encuentras:', 
            'Ecuador': 'Por favor, selecciona el rango de edad en el que te encuentras:', 
            'Perú': 'Por favor, selecciona el rango de edad en el que te encuentras:', 
            'R. Dominicana': 'Por favor, selecciona el rango de edad en el que te encuentras:', 
            'Honduras': 'Por favor, selecciona el rango de edad en el que te encuentras:', # <-- Corregido para Honduras según tu último input
            'El Salvador': 'Por favor, selecciona el rango de edad en el que te encuentras:', 
            'Guatemala': 'Por favor, selecciona el rango de edad en el que te encuentras:', 
            'Colombia Minors': 'AGErange'
        },
        '[age]': {
            'Panamá': '[age]', 
            'México': 'Edad:', 
            'Colombia': 'Edad en el que te encuentras:', 
            'Ecuador': 'EDAD', 
            'Perú': 'Edad:', 
            'R. Dominicana': 'AGE', 
            'Honduras': 'EDAD', # <-- Corregido para Honduras
            'El Salvador': 'AGE', 
            'Guatemala': 'AGE', 
            'Colombia Minors': 'A partir de esta sección te pediremos que respondas pensando sobre el consumo de bebidas de tus hijos entre 8 y 17 años.Si tienes más de 1 hijo en esta edad te pediremos que te enfoques en uno de tus hijos para responder sobre su consumo. ¿Qué edad t'
        },
        # --- FIN CORRECCIÓN HONDURAS EDAD v2.26 ---
        'NSE': {'Panamá': 'NSE', 'México': 'SEL AGRUPADO', 'Colombia': 'NSE', 'Ecuador': 'agrupado ows', 'Perú': 'SEL AGRUPADO', 'R. Dominicana': 'NSE', 'Honduras': 'NSE', 'El Salvador': 'NSE', 'Guatemala': 'NSE Agrupado', 'Colombia Minors': 'SEL AGRUPADO'},
        
        # --- INICIO MODIFICACIÓN SOLICITADA (Guatemala NSE2) ---
        'NSE2': {'Panamá': 'NSE2', 'México': 'SEL SEPARADO', 'Colombia': 'NSE2', 'Ecuador': 'Clasificación NSE (HIDDEN VARIABLE)PUNTOS: 0', 'Perú': 'SEL SEPARADO', 'R. Dominicana': 'NSE2', 'Honduras': 'NSE2', 'El Salvador': '¿Cuál es el ingreso mensual promedio de su hogar?', 'Guatemala': 'NSE_Parte2', 'Colombia Minors': 'SEL SEPARADO'},
        # --- FIN MODIFICACIÓN SOLICITADA ---
        
        'Region 1 (Centro/Metro/Oeste)': {'Panamá': 'Region 1 (Centro/Metro/Oeste)', 'México': 'Region 2026', 'Colombia': 'region_Parte2', 'Ecuador': 'Region', 'Perú': 'region', 'R. Dominicana': 'region', 'Honduras': 'Region', # <-- Columna de Región Amplia (v2.21)
         'El Salvador': 'REGION', 'Guatemala': 'region', 'Colombia Minors': 'region'},
        'CIUDAD': {'Panamá': 'CIUDAD', 'México': 'Estado donde vive:', 'Colombia': 'Por favor escribe el nombre de la ciudad en la que vives:', 'Ecuador': 'Estado', 'Perú': 'state', 'R. Dominicana': 'state', 'Honduras': 'Estado', # <-- Columna de Departamento/Ciudad (v2.21)
         'El Salvador': 'ESTADO', 'Guatemala': 'state', 'Colombia Minors': 'Departamento:'},
        'Region2': {'Perú': 'region2'},
        'Origen': {'Panamá': 'Origen', 'México': 'Origen', 'Colombia': '', 'Ecuador': 'Origen del registro', 'Perú': '', 'R. Dominicana': '', 'Honduras': '', 'El Salvador': '', 'Guatemala': '', 'Colombia Minors': ''},
        # Columnas como 'Proveedor' y '[panelistid]' no están en el CSV de mapeo,
        # por lo que el script buscará el nombre estándar ('Proveedor', '[panelistid]')
        # en el archivo cargado.
    }
}
# ---

# --- SELECCIÓN DE PAÍS Y CARGA DE ARCHIVOS ---
col_pais, col_vacia = st.columns([1, 2])
with col_pais:
    pais_seleccionado_display = st.selectbox("Selecciona el País:", paises_disponibles, key="select_pais")

# --- Botones de Descarga ---
st.markdown("### Descargar Reglas de Validación")
# --- MODIFICACIÓN v2.27: Añadida col_dl3 ---
col_dl1, col_dl2, col_dl3 = st.columns(3)
with col_dl1:
    reglas_vol = THRESHOLDS_POR_PAIS.get(pais_seleccionado_display, [])
    if reglas_vol:
        df_vol = pd.DataFrame(reglas_vol); df_vol.columns = ['Columna', 'Condición', 'Límite']
        excel_vol = to_excel(df_vol)
        st.download_button(label="Descargar Reglas Volumetría (.xlsx)", data=excel_vol, file_name=f'reglas_volumetria_{pais_seleccionado_display}.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', key='dl_vol')
    else: st.info(f"No hay regras de volumetría para {pais_seleccionado_display}.")
with col_dl2:
    reglas_geo = CLASIFICACIONES_POR_PAIS.get(pais_seleccionado_display, {})
    if reglas_geo:
        lista_g = [{'Región 1': r, 'Ciudad/Dpto': c} for r, ciudades in reglas_geo.items() for c in ciudades]
        if lista_g:
            df_geo = pd.DataFrame(lista_g)
            excel_geo = to_excel(df_geo)
            st.download_button(label="Descargar Reglas Geografía 1 (.xlsx)", data=excel_geo, file_name=f'reglas_geografia_r1_{pais_seleccionado_display}.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', key='dl_geo')
        else: st.info(f"No hay regras geográficas detalladas para {pais_seleccionado_display}.")
    else: st.info(f"No hay regras geográficas definidas para {pais_seleccionado_display}.")

# --- NUEVO BOTÓN GEO 2 PERÚ (v2.27) ---
with col_dl3:
    if pais_seleccionado_display == 'Perú':
        reglas_geo_r2 = CLASIFICACIONES_PERU_REGION2
        if reglas_geo_r2:
            lista_g_r2 = [{'Región 2': r, 'Ciudad/Dpto': c} for r, ciudades in reglas_geo_r2.items() for c in ciudades]
            df_geo_r2 = pd.DataFrame(lista_g_r2)
            excel_geo_r2 = to_excel(df_geo_r2)
            st.download_button(
                label="Descargar Reglas Geo 2 (Perú)",
                data=excel_geo_r2,
                file_name=f'reglas_geografia_r2_Peru.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                key='dl_geo_r2'
            )
        else:
            st.info("No hay reglas de Geografía 2 para Perú.")
    else:
        # Espacio reservado para mantener alineación
        st.empty() 
# --- FIN NUEVO BOTÓN ---

st.divider()

# --- NUEVO BOTÓN MAPEO DE COLUMNAS (v2.27) ---
st.markdown("### Descargar Mapeo de Columnas")
try:
    df_mapeo = create_mapping_dataframe(COLUMN_MAPPING, paises_disponibles)
    excel_mapeo = to_excel(df_mapeo)
    st.download_button(
        label="Descargar Mapeo Completo (.xlsx)",
        data=excel_mapeo,
        file_name='mapeo_columnas_completo.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        key='dl_mapeo'
    )
except Exception as e_map:
    st.error(f"No se pudo generar el archivo de mapeo: {e_map}")
# --- FIN NUEVO BOTÓN ---


st.divider()

# --- Carga de Archivos ---
st.markdown("### Carga de Archivos Excel")
col1_up, col2_up = st.columns(2)
with col1_up: uploaded_file_num = st.file_uploader("Carga el archivo Numérico", type=["xlsx"], key="num")
with col2_up: uploaded_file_txt = st.file_uploader("Carga el archivo Textual", type=["xlsx"], key="txt")

# --- LÓGICA DE VALIDACIÓN ---
if uploaded_file_num is not None and uploaded_file_txt is not None:

    st.info(f"Archivos cargados. Iniciando validación para **{pais_seleccionado_display}**...")
    st.divider()
    pais_clave_interna = pais_seleccionado_display
    validation_results = []
    # --- AJUSTE 4: Inicializar DF para descarga de abiertas ---
    df_para_descarga_abiertas = pd.DataFrame()

    try:
        # Leer archivos
        df_numerico_full = pd.read_excel(io.BytesIO(uploaded_file_num.getvalue()))
        df_textual_full = pd.read_excel(io.BytesIO(uploaded_file_txt.getvalue()))

        # --- APLICAR DEDUPLICACIÓN DE COLUMNAS (v2.23) ---
        df_numerico_full = deduplicate_columns(df_numerico_full.copy(), operation_name="lectura (Numérico)")
        df_textual_full = deduplicate_columns(df_textual_full.copy(), operation_name="lectura (Textual)")
        # --- FIN DEDUPLICACIÓN ---

    except Exception as e: st.error(f"Error al leer o pre-procesar archivos: {e}"); st.stop()

    # --- LÓGICA DE RENOMBRADO DINÁMICO ---
    rename_map_num = {}
    rename_map_txt = {}
    missing_original_cols = {'num': [], 'txt': []} # Para rastrear cols que faltan en origen

    # Ahora el mapeo buscará el nombre original (sin sufijo .1, .2) en las columnas ya deduplicadas
    for standard_name, country_mappings in COLUMN_MAPPING['Base Numérica'].items():
        if pais_clave_interna in country_mappings:
            country_specific_name = country_mappings[pais_clave_interna]
            if country_specific_name: # Solo si hay un nombre mapeado
                if country_specific_name in df_numerico_full.columns: # Buscar el nombre *sin* sufijo
                    rename_map_num[country_specific_name] = standard_name
                else:
                    missing_original_cols['num'].append(country_specific_name) # Registrar original faltante (sin sufijo)

    for standard_name, country_mappings in COLUMN_MAPPING['Base Textual'].items():
        if pais_clave_interna in country_mappings:
            country_specific_name = country_mappings[pais_clave_interna]
            if country_specific_name: # Solo si hay un nombre mapeado
                if country_specific_name in df_textual_full.columns: # Buscar el nombre *sin* sufijo
                    rename_map_txt[country_specific_name] = standard_name
                else:
                    missing_original_cols['txt'].append(country_specific_name) # Registrar original faltante (sin sufijo)

    # Mostrar advertencia si faltan columnas ORIGINALES mapeadas
    if missing_original_cols['num']:
        st.warning(f"Advertencia: Las siguientes columnas mapeadas no se encontraron (ni siquiera como primera ocurrencia) en el archivo Numérico: {', '.join(missing_original_cols['num'])}")
    if missing_original_cols['txt']:
        st.warning(f"Advertencia: Las siguientes columnas mapeadas no se encontraron (ni siquiera como primera ocurrencia) en el archivo Textual: {', '.join(missing_original_cols['txt'])}")

    try:
        # Renombrar usando los nombres originales (sin sufijo) que sí existen
        df_numerico_renamed = df_numerico_full.rename(columns=rename_map_num)
        df_textual_renamed = df_textual_full.rename(columns=rename_map_txt)

        # --- INICIO CORRECCIÓN v2.26: DEDUPLICAR OTRA VEZ ---
        # Volver a ejecutar deduplicate para manejar duplicados creados POR EL RENOMBRADO
        # (ej. si 'EDAD' se renombra a '[age]' y ya existía una columna '[age]')
        df_numerico_renamed = deduplicate_columns(df_numerico_renamed.copy(), operation_name="renombrado (Numérico)")
        df_textual_renamed = deduplicate_columns(df_textual_renamed.copy(), operation_name="renombrado (Textual)")
        # --- FIN CORRECCIÓN v2.26 ---

    except Exception as e:
        st.error(f"Error during rename or post-rename deduplication: {e}")
        st.stop()
    # --- FIN DE LÓGICA DE RENOMBRADO ---

    # --- INICIO CHEQUEO POST-RENOMBRADO (v2.19) ---
    required_cols_num = ['Unico', 'NSE', 'gender', 'AGErange', 'Region'] # Columnas numéricas esenciales con nombre estándar
    required_cols_txt = ['[auth]', 'NSE', 'NSE2', '[age]', 'Region 1 (Centro/Metro/Oeste)', 'CIUDAD'] # Columnas textuales esenciales con nombre estándar
    
    # Añadir "Por favor, selecciona..." a la lista de requeridos de texto
    required_cols_txt.append("Por favor, selecciona el rango de edad en el que te encuentras:")
    
    # Añadir Ponderador si no es Colombia Minors
    if pais_clave_interna != 'Colombia Minors':
        required_cols_num.append('Ponderador')
     # Añadir Region2 si es Perú
    if pais_clave_interna == 'Perú':
        required_cols_txt.append('Region2')


    missing_std_cols_num = [col for col in required_cols_num if col not in df_numerico_renamed.columns]
    missing_std_cols_txt = [col for col in required_cols_txt if col not in df_textual_renamed.columns]

    error_messages = []
    if missing_std_cols_num:
        error_messages.append(f"Faltan columnas esenciales en la base numérica después del renombrado: **{', '.join(missing_std_cols_num)}**. Verifique el mapeo o el archivo original.")
    if missing_std_cols_txt:
        # Ya no necesitamos la excepción especial para Honduras Geo, el chequeo general funcionará
         error_messages.append(f"Faltan columnas esenciales en la base textual después del renombrado: **{', '.join(missing_std_cols_txt)}**. Verifique el mapeo o el archivo original.")

    if error_messages:
        for msg in error_messages:
            st.error(msg)
        st.stop() # Detener ejecución si faltan columnas críticas
    # --- FIN CHEQUEO POST-RENOMBRADO ---


    # --- Optimización de Carga (ahora usa los DFs renombrados) ---
    num_cols_base = ['Unico', 'lastpage', 'lastpage_Parte2', 'lastpage_Parte3']
    # Columnas textuales con nombre ESTÁNDAR que se usarán
    txt_cols_std = ['[auth]', 'startdate', "Por favor, selecciona el rango de edad en el que te encuentras:", '[age]', 'NSE', 'NSE2', 'Region 1 (Centro/Metro/Oeste)', 'CIUDAD', 'Origen', 'Proveedor', 'Region2', '[panelistid]']
    # Columnas numéricas con nombre ESTÁNDAR que se usarán
    num_cols_extra_std = ['Ponderador', 'NSE', 'gender', 'AGErange', 'Region']
    # Añadir columnas de volumetría (ya tienen nombre estándar por el mapeo de THRESHOLDS)
    num_cols_extra_std.extend([rule['col'] for rule in THRESHOLDS_POR_PAIS.get(pais_clave_interna, [])])

    # Seleccionar solo las columnas ESTÁNDAR que existen en los DFs renombrados
    # IMPORTANTE: Usar .loc para evitar problemas con columnas duplicadas si el chequeo fallara
    num_ex = [c for c in num_cols_base + list(set(num_cols_extra_std)) if c in df_numerico_renamed.columns]
    txt_ex = [c for c in txt_cols_std if c in df_textual_renamed.columns]

    # Prevenir selección de duplicados explícitamente
    num_ex = list(dict.fromkeys(num_ex)) # Mantener orden pero quitar duplicados
    txt_ex = list(dict.fromkeys(txt_ex)) # Mantener orden pero quitar duplicados

    try:
        # Crear los dataframes finales df_numerico y df_textual usando los DFs RENOMBRADOS
        df_numerico = df_numerico_renamed[num_ex].copy()
        df_textual = df_textual_renamed[txt_ex].copy()
    except KeyError as e:
        st.error(f"Error inesperado al seleccionar columnas finales: {e}. Verifique que las columnas base ('Unico', '[auth]') existan.")
        st.stop()
    except Exception as e_sel:
         st.error(f"Error inesperado durante la selección final de columnas: {e_sel}")
         st.stop()

    # --- VALIDACIONES (V1-V13) ---

    # V1: Tamaño
    key_v1 = "Tamaño de las Bases"; content_v1 = ""; status_v1 = "Correcto"
    # USA df_numerico_full y df_textual_full para obtener dimensiones originales
    fn, cn = df_numerico_full.shape; ft, ct = df_textual_full.shape
    content_v1 += f"- Num: {fn} filas x {cn} columnas<br>- Txt: {ft} filas x {ct} columnas<br><br><b>Comparación:</b><br>"
    if fn == ft and cn == ct: content_v1 += "<span class='status-correcto-inline'>[Correcto]</span> Coinciden."
    else: status_v1 = "Incorrecto"; content_v1 += "<span class='status-incorrecto-inline'>[Incorrecto]</span> Diferentes.<br>";
    if fn != ft: content_v1 += "- Filas.<br>"
    if cn != ct: content_v1 += "- Columnas.<br>"
    validation_results.append({'key': key_v1, 'status': status_v1, 'content': content_v1})

    # V2: Orden IDs (Usa df_numerico y df_textual, que ya están filtrados y renombrados)
    key_v2 = "Orden de Códigos Únicos"; content_v2 = ""; status_v2 = "Correcto"; col_num = 'Unico'; col_txt = '[auth]'
    try:
        # Ya verificamos que 'Unico' y '[auth]' existen
        cod_num = df_numerico[col_num]; cod_txt = df_textual[col_txt]
        if len(cod_num) != len(cod_txt): status_v2 = "Incorrecto"; content_v2 += f"<span class='status-incorrecto-inline'>[Incorrecto]</span> Filas no coinciden.<br>Num:{len(cod_num)}, Txt:{len(cod_txt)}<br>(Error V1 o Filtrado)"
        elif cod_num.equals(cod_txt): content_v2 += f"<span class='status-correcto-inline'>[Correcto]</span> Orden idéntico."
        else:
            status_v2 = "Incorrecto"; content_v2 += f"<span class='status-incorrecto-inline'>[Incorrecto]</span> Códigos/orden no coinciden.<br>"; diff = cod_num != cod_txt
            # Asegurarse de tomar los índices correctos para el reporte
            diff_indices = cod_num.index[diff]
            if not diff_indices.empty:
                rep = pd.DataFrame({'Fila': diff_indices + 2, f'{col_num} (Num)': cod_num.loc[diff_indices].values, f'{col_txt} (Txt)': cod_txt.loc[diff_indices].values})
                content_v2 += f"Primeras 5 diferencias (Fila Excel, Num, Txt):<br>" + rep.head().to_html(classes='df-style', index=False)
            else: # Puede que equals sea False por tipos de datos aunque los valores "parezcan" iguales
                content_v2 += "No se encontraron diferencias visuales, posible diferencia de tipos de dato.<br>"
    except Exception as e_v2: # Captura genérica por si algo más falla
        status_v2 = "Error"; content_v2 += f"<span class='status-error-inline'>[ERROR Inesperado V2]</span> {e_v2}."
    validation_results.append({'key': key_v2, 'status': status_v2, 'content': content_v2})


    # V3: lastpage (Usa df_numerico)
    key_v3 = "lastpage, lastpage_Parte2 y lastpage_Parte3"; content_v3 = ""; status_v3 = "Correcto"; cols_v3 = ['lastpage', 'lastpage_Parte2', 'lastpage_Parte3']
    for col in cols_v3:
        content_v3 += f"<br><b>'{col}':</b><br>";
        if col not in df_numerico.columns:
            # No marcar como error si la columna simplemente no existe para ese país (ej. Colombia Minors)
             map_exists = COLUMN_MAPPING['Base Numérica'].get(col, {}).get(pais_clave_interna)
             if map_exists == '': # Si está mapeado a vacío, es esperado que no exista
                 status_v3 = "Info" if status_v3 == "Correcto" else status_v3 # Mantener Error/Incorrecto si ya lo era
                 content_v3 += f"<span class='status-info-inline'>[INFO]</span> Columna no aplica o no mapeada para {pais_clave_interna}.<br>"
             else: # Si debería existir pero no está, es error
                 status_v3 = "Error"; content_v3 += f"<span class='status-error-inline'>[ERROR]</span> Columna '{col}' no encontrada después del renombrado.<br>";
             continue # Saltar al siguiente
        vals = df_numerico[col].dropna().unique()
        if len(vals) <= 1: content_v3 += f"<span class='status-correcto-inline'>[Correcto]</span> Único valor o vacía.<br>" # Considerar vacía como ok
        else:
            if status_v3 != "Error": status_v3 = "Incorrecto" # No sobrescribir si ya hay error
            vals_str = ", ".join(map(str, vals)); content_v3 += f"<span class='status-incorrecto-inline'>[Incorrecto]</span> Múltiples valores encontrados: {vals_str}<br>"
    # Si al final no hubo errores ni incorrectos, pero sí info, el estado final es Info
    if status_v3 == "Correcto" and "[INFO]" in content_v3: status_v3 = "Info"
    elif status_v3 == "Correcto" and not "[INFO]" in content_v3: content_v3 = "<span class'status-correcto-inline'>[Correcto]</span> Todas las columnas ('lastpage', 'lastpage_Parte2', 'lastpage_Parte3' si aplican) tienen un único valor."

    validation_results.append({'key': key_v3, 'status': status_v3, 'content': content_v3})


    # V4: Periodo Campo (Usa df_textual)
    key_v4 = "Periodo Campo ('startdate')"; content_v4 = ""; status_v4 = "Info"; col_fecha = 'startdate'
    locale_usado = ''; formato_fecha = '%d/%b/%Y %H:%M' # Formato por defecto
    try:
        # Intentar configurar locale español (más común primero)
        try: locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8'); locale_usado = 'es_ES.UTF-8'
        except locale.Error:
            try: locale.setlocale(locale.LC_TIME, 'es_MX.UTF-8'); locale_usado = 'es_MX.UTF-8'
            except locale.Error:
                try: locale.setlocale(locale.LC_TIME, 'es'); locale_usado = 'es' # Genérico español
                except locale.Error:
                        try:
                            # Fallback a locale del sistema
                            locale.setlocale(locale.LC_TIME, '')
                            locale_usado = f"Sistema ({locale.getlocale(locale.LC_TIME)[0]})"
                        except locale.Error:
                            locale_usado = 'No configurado'
                            st.warning("No se pudo configurar un locale en español ni el del sistema para formatear fechas.")

        # Establecer formato de fecha según el locale conseguido (si es español)
        if 'es' in locale_usado.split('_')[0].lower():
            formato_fecha = '%d de %B de %Y, %I:%M %p'
        else: # Usar formato más internacional si no es español
            formato_fecha = '%Y-%m-%d %H:%M:%S'


        if col_fecha not in df_textual.columns: raise KeyError(f"'{col_fecha}' ausente.")
        # Intentar convertir AHORA, después de configurar locale si fue posible
        fechas_validas = pd.to_datetime(df_textual[col_fecha], errors='coerce').dropna()

        if not fechas_validas.empty:
            f_min, f_max = fechas_validas.min(), fechas_validas.max()
            content_v4 += f"<b>Periodo (locale usado: {locale_usado}):</b><br> - Inicio: {f_min.strftime(formato_fecha)}<br> - Fin: {f_max.strftime(formato_fecha)}<br>"
        else:
            # Verificar si la columna original tenía datos
            if df_textual[col_fecha].isnull().all():
                content_v4 += "<span class='status-info-inline'>[INFO]</span> Columna 'startdate' está vacía.<br>"
            else:
                status_v4 = "Error"; content_v4 += "<span class='status-error-inline'>[ERROR]</span> No se pudieron convertir las fechas. Verifique el formato en el Excel.<br>"
                # Mostrar algunos ejemplos no convertidos
                invalid_dates = df_textual[pd.to_datetime(df_textual[col_fecha], errors='coerce').isna()][col_fecha].unique()
                content_v4 += f"Primeros 5 formatos no reconocidos: {list(invalid_dates[:5])}<br>"

    except KeyError as e: status_v4 = "Error"; content_v4 += f"<span class='status-error-inline'>[ERROR]</span> Columna {e} no encontrada.<br>"
    except Exception as e_loc: status_v4 = "Error"; content_v4 += f"<span class='status-error-inline'>[ERROR Locale/Fecha]</span> {e_loc}.<br>"
    validation_results.append({'key': key_v4, 'status': status_v4, 'content': content_v4})


    # V5: Agrupaciones
    key_v5 = "Agrupaciones"; content_v5 = ""; status_v5 = "Correcto"
    # 5.1 Edad
    content_v5 += "<h3>5.1: Edad vs [age]</h3>";
    col_g_edad_std = "Por favor, selecciona el rango de edad en el que te encuentras:" # Nombre estándar
    col_d_edad_std = '[age]' # Nombre estándar

    try:
        # Ya se verificó que las columnas existen después del renombrado y antes de crear df_textual
        # Ahora usamos directamente los nombres estándar en df_textual
        # df_textual[col_g_edad_std] y df_textual[col_d_edad_std] deberían ser Series únicas
        # gracias a la doble deduplicación
        df_temp_edad = df_textual[[col_g_edad_std, col_d_edad_std]].copy()
        df_temp_edad[col_d_edad_std] = pd.to_numeric(df_temp_edad[col_d_edad_std], errors='coerce')

        # Agrupar usando el nombre ESTÁNDAR de la columna de rango
        # df_temp_edad[col_g_edad_std] es una Serie, por lo que groupby funciona
        grouped_edad = df_temp_edad.groupby(col_g_edad_std, dropna=False)

        # Accedemos directamente a la columna de agregación
        # grouped_edad[col_d_edad_std] es un SeriesGroupBy
        rep_edad = grouped_edad[col_d_edad_std].agg(['count', 'min', 'max'])
        rep_edad.columns = ['Total', 'Min', 'Max']
        # Llenar NaN con texto indicativo para la tabla HTML
        rep_edad.fillna({'Min': '-', 'Max': '-'}, inplace=True)
        rep_edad = rep_edad.reset_index() # Mover índice (rango edad) a columna
        rep_edad.rename(columns={col_g_edad_std: 'Rango Edad'}, inplace=True)
        content_v5 += rep_edad.to_html(classes='df-style', index=False, na_rep='-')

    except KeyError as e: # Aunque ya chequeamos, por si acaso
        status_v5 = "Error"
        content_v5 += f"<span class='status-error-inline'>[ERROR]</span> Columna de edad faltante: {e}<br>"
    except Exception as e_agg: # Captura el error "arg must be a list..." si la deduplicación falló
        status_v5 = "Error"
        content_v5 += f"<span class='status-error-inline'>[ERROR Agregación Edad]</span> {e_agg}. Esto usualmente significa que una columna ('Rango Edad' o 'Edad Exacta') sigue duplicada.<br>"

    content_v5 += "<hr style='border-top: 1px dotted #ccc;'>"

    # 5.2 NSE - Añadido fillna y try-except más específico v2.22
    content_v5 += "<h3>5.2: NSE vs NSE2</h3>"; col_g_nse = 'NSE'; col_d_nse = 'NSE2'
    try:
        # Asegurarse de que ambas columnas existen (ya chequeado antes, pero doble check)
        if col_g_nse not in df_textual.columns: raise KeyError(f"Columna '{col_g_nse}'")
        if col_d_nse not in df_textual.columns: raise KeyError(f"Columna '{col_d_nse}'")

        # Rellenar NaNs explícitamente ANTES de crosstab
        nse1_filled = df_textual[col_g_nse].fillna('VACÍO/NULO')
        nse2_filled = df_textual[col_d_nse].fillna('VACÍO/NULO')

        # Usar las series rellenadas en crosstab
        rep_nse = pd.crosstab(nse1_filled, nse2_filled, dropna=False) # dropna=False es redundante ahora pero no daña

        content_v5 += "Verifica consistencia (incluye valores vacíos/nulos):<br>" + rep_nse.to_html(classes='df-style', na_rep='-') # na_rep es por si acaso
    except KeyError as e_nse_key: # Captura específica si A PESAR de todo falta una columna
        if status_v5 != "Error": status_v5 = "Error"
        content_v5 += f"<span class'status-error-inline'>[ERROR]</span> {e_nse_key} no encontrada al intentar crear tabla cruzada NSE.<br>"
    except Exception as e_crosstab: # Captura otros posibles errores de crosstab
        if status_v5 != "Error": status_v5 = "Error"
        content_v5 += f"<span class='status-error-inline'>[ERROR Crosstab NSE]</span> {e_crosstab}<br>"

    content_v5 += "<hr style='border-top: 1px dotted #ccc;'>"

    # 5.3 Geografía (Región 1) - Usa chequeo case-insensitive y global de ciudad
    content_v5 += f"<h3>5.3: Geografía ({pais_seleccionado_display} - Region 1 vs Ciudad/Dpto)</h3>"; status_v5_3 = "Correcto"
    col_reg = 'Region 1 (Centro/Metro/Oeste)'; col_ciu = 'CIUDAD' # Nombres estándar
    try:
        clasif = CLASIFICACIONES_POR_PAIS.get(pais_clave_interna);
        if not clasif: status_v5_3 = "Info"; content_v5 += f"<span class'status-info-inline'>[INFO]</span> No hay regras geográficas definidas para {pais_seleccionado_display}."
        elif not all(c in df_textual.columns for c in [col_reg, col_ciu]):
            # Este caso ahora debería ser manejado por el chequeo post-renombrado, pero lo dejamos como fallback
            raise KeyError(f"Columnas '{col_reg}' o '{col_ciu}' no encontradas después del renombrado.")
        else:
            err_reg = [];
            # Crear diccionarios para búsqueda case-insensitive eficiente
            clasif_lower_keys = {k.lower(): k for k in clasif.keys()}
            clasif_lower_values = {k_lower: {v.lower() for v in clasif[k_orig]} for k_lower, k_orig in clasif_lower_keys.items()}
            # Set global de todas las ciudades para validar si existe en algún lugar del país
            all_valid_cities_lower = {ciu for cities in clasif_lower_values.values() for ciu in cities}

            for idx, row in df_textual.iterrows():
                reg_val, ciu_val = row[col_reg], row[col_ciu] # Usar nombres estándar
                if pd.isna(reg_val) or pd.isna(ciu_val): continue
                # Convertir a string para comparación insensible a mayúsculas/minúsculas y espacios
                reg_str_lower = str(reg_val).strip().lower()
                ciu_str_lower = str(ciu_val).strip().lower()

                # Verificar primero si la ciudad existe en absoluto en el país
                if ciu_str_lower not in all_valid_cities_lower:
                    err_reg.append({'Fila': idx + 2, 'Region': reg_val, 'Ciudad': ciu_val, 'Error': f"Ciudad/Dpto '{ciu_val}' no existe en el catálogo general del país"})
                # Si existe, buscar si pertenece a la región correcta
                elif reg_str_lower in clasif_lower_keys:
                    correct_reg_key_orig = clasif_lower_keys[reg_str_lower]
                    if not ciu_str_lower in clasif_lower_values[reg_str_lower]:
                        err_reg.append({'Fila': idx + 2, 'Region': reg_val, 'Ciudad': ciu_val, 'Error': f"'{ciu_val}' no pertenece a la región '{correct_reg_key_orig}'"})
                else:
                    err_reg.append({'Fila': idx + 2, 'Region': reg_val, 'Ciudad': ciu_val, 'Error': f"Región '{reg_val}' no válida"})

            if not err_reg: content_v5 += f"<span class='status-correcto-inline'>[Correcto]</span> Consistente."
            else:
                if status_v5 != "Error": status_v5_3 = "Incorrecto"
                content_v5 += f"<span class='status-incorrecto-inline'>[Incorrecto]</span> {len(err_reg)} inconsistencias.<br>"; df_err = pd.DataFrame(err_reg); content_v5 += "Detalle de inconsistencias:<br>" + df_err.to_html(classes='df-style', index=False)

    except KeyError as e: # Captura el error si las columnas no existen A PESAR del chequeo previo
        status_v5_3 = "Error"; content_v5 += f"<span class='status-error-inline'>[ERROR]</span> {e}<br>"
    except Exception as e_geo1: # Otros errores inesperados
        status_v5_3 = "Error"; content_v5 += f"<span class='status-error-inline'>[ERROR Inesperado Geo 1]</span> {e_geo1}<br>"

    # Actualizar estado general de V5
    if status_v5 == "Correcto" and status_v5_3 not in ["Correcto", "Info"]: status_v5 = status_v5_3
    elif status_v5_3 == "Error": status_v5 = "Error" # Error en sub-validación hace que toda V5 sea Error


    # --- 5.4: Geografía 2 (Solo Perú) - Usa chequeo case-insensitive y global de ciudad
    if pais_clave_interna == 'Perú':
        content_v5 += "<hr style='border-top: 1px dotted #ccc;'>"
        content_v5 += f"<h3>5.4: Geografía 2 ({pais_seleccionado_display} - Region2 vs Ciudad/Dpto)</h3>"
        status_v5_4 = "Correcto"
        col_reg_r2 = 'Region2'; col_ciu_r2 = 'CIUDAD'
        try:
            clasif_r2 = CLASIFICACIONES_PERU_REGION2
            if not all(c in df_textual.columns for c in [col_reg_r2, col_ciu_r2]):
                raise KeyError(f"Columnas '{col_reg_r2}' o '{col_ciu_r2}' no encontradas para validación Geo 2.")

            err_reg_r2 = []
            # Crear diccionarios para búsqueda case-insensitive eficiente
            clasif_r2_lower_keys = {k.lower(): k for k in clasif_r2.keys()}
            clasif_r2_lower_values = {k_lower: {v.lower() for v in clasif_r2[k_orig]} for k_lower, k_orig in clasif_r2_lower_keys.items()}
            # Set global de ciudades Geo 2
            all_valid_cities_r2_lower = {ciu for cities in clasif_r2_lower_values.values() for ciu in cities}

            for idx, row in df_textual.iterrows():
                reg, ciu = row[col_reg_r2], row[col_ciu_r2]
                if pd.isna(reg) or pd.isna(ciu): continue
                # Convertir a string para comparación insensible
                reg_str_lower = str(reg).strip().lower()
                ciu_str_lower = str(ciu).strip().lower()

                if ciu_str_lower not in all_valid_cities_r2_lower:
                    err_reg_r2.append({'Fila': idx + 2, 'Region2': reg, 'Ciudad': ciu, 'Error': f"Ciudad/Dpto '{ciu}' no existe en el catálogo Geo 2"})
                elif reg_str_lower in clasif_r2_lower_keys:
                    correct_reg_key_r2 = clasif_r2_lower_keys[reg_str_lower]
                    if ciu_str_lower not in clasif_r2_lower_values[reg_str_lower]:
                        err_reg_r2.append({'Fila': idx + 2, 'Region2': reg, 'Ciudad': ciu, 'Error': f"'{ciu}' no en '{correct_reg_key_r2}' (region2)"})
                else:
                    if pd.notna(reg): # Solo reportar si la región no es nula pero inválida
                        err_reg_r2.append({'Fila': idx + 2, 'Region2': reg, 'Ciudad': ciu, 'Error': f"Región '{reg}' no válida (region2)"})

            if not err_reg_r2:
                content_v5 += f"<span class='status-correcto-inline'>[Correcto]</span> Consistente (region2)."
            else:
                if status_v5 != "Error": status_v5_4 = "Incorrecto"
                content_v5 += f"<span class='status-incorrecto-inline'>[Incorrecto]</span> {len(err_reg_r2)} inconsistencias (region2).<br>"
                df_err_r2 = pd.DataFrame(err_reg_r2)
                content_v5 += "Detalle de inconsistencias:<br>" + df_err_r2.to_html(classes='df-style', index=False)
        except KeyError as e:
            status_v5_4 = "Error"; content_v5 += f"<span class='status-error-inline'>[ERROR]</span> {e}<br>"
        except Exception as e_geo2:
             status_v5_4 = "Error"; content_v5 += f"<span class'status-error-inline'>[ERROR Inesperado Geo 2]</span> {e_geo2}<br>"

        # Actualizar estado general de V5
        if status_v5 == "Correcto" and status_v5_4 not in ["Correcto", "Info"]: status_v5 = status_v5_4
        elif status_v5_4 == "Error": status_v5 = "Error"
    # --- FIN V5.4 ---

    validation_results.append({'key': key_v5, 'status': status_v5, 'content': content_v5})


    # V6: Origen/Proveedor (Usa df_textual)
    key_v6 = "Origen/Proveedor"; content_v6 = ""; status_v6 = "Info"; prov_cols = ['Origen', 'Proveedor']
    # Buscar cuál de las columnas (con nombre estándar) existe en df_textual
    prov_col = next((col for col in prov_cols if col in df_textual.columns), None)
    if prov_col:
        content_v6 += f"<b>Conteo por '{prov_col}':</b><br>";
        try:
            # Calcular conteo, llenar NaNs con 'VACÍO/NULO' ANTES de reset_index
            cnt = df_textual[prov_col].fillna('VACÍO/NULO').value_counts().reset_index()
            cnt.columns = [prov_col, 'Conteo'] # Renombrar columnas
            content_v6 += cnt.to_html(classes='df-style', index=False)
        except Exception as e_v6: status_v6 = "Error"; content_v6 += f"<span class='status-error-inline'>[ERROR Contando]</span> {e_v6}<br>"
    else:
        content_v6 += f"<span class='status-info-inline'>[INFO]</span> No se encontraron columnas mapeadas a 'Origen' o 'Proveedor'.<br>"
        # No cambiar estado a Error si simplemente no aplican
        status_v6 = "Info" if status_v6 != "Error" else "Error"

    validation_results.append({'key': key_v6, 'status': status_v6, 'content': content_v6})


    # V7: Nulos Base Numérica (Usa df_numerico para chequear nulos, df_numerico_renamed para obtener IDs si hay nulos)
    key_v7 = "Nulos Base Numérica"; content_v7 = ""; status_v7 = "Correcto"; id_unico = 'Unico'; cols_v7 = ['NSE', 'gender', 'AGErange', 'Region']
    # Incluir Ponderador si no es Colombia Minors
    if pais_clave_interna != 'Colombia Minors':
         cols_v7.append('Ponderador')

    nulos_det = []; cols_chequeadas_existentes = []
    id_col_exists = id_unico in df_numerico_renamed.columns # Chequear ID en el renombrado
    if not id_col_exists: content_v7 += f"<span class='status-error-inline'>[WARN]</span> Columna ID '{id_unico}' no encontrada para reportar IDs con nulos.<br>"

    for col in cols_v7:
        if col in df_numerico.columns: # Chequear si la columna existe en el DF final (df_numerico)
            cols_chequeadas_existentes.append(col)
            nulas_mask = df_numerico[col].isnull()
            cant = nulas_mask.sum()
            if cant > 0:
                if status_v7 != "Error": status_v7 = "Incorrecto" # Marcar como incorrecto si hay nulos
                # Obtener IDs del DF renombrado usando la máscara de nulos
                ids_nulos = df_numerico_renamed.loc[nulas_mask.index, id_unico].tolist() if id_col_exists else []
                nulos_det.append({'col': col, 'cant': cant, 'ids': ids_nulos[:5]}) # Mostrar solo los primeros 5 IDs
        # No hacer nada si la columna no existe en df_numerico, ya se manejó en el chequeo post-renombrado

    if not cols_chequeadas_existentes:
         status_v7 = "Error"
         content_v7 += f"<span class='status-error-inline'>[ERROR]</span> Ninguna de las columnas demográficas esperadas ({', '.join(cols_v7)}) fue encontrada para chequear nulos.<br>"
    elif nulos_det:
        content_v7 += f"<span class='status-incorrecto-inline'>[Incorrecto]</span> Se encontraron valores nulos:<br><ul>"
        for item in nulos_det:
            content_v7 += f"<li><b>{item['col']}</b>: {item['cant']} nulos.";
            if item['ids']: ids_str = ", ".join(map(str, item['ids'])); content_v7 += f"<br>- Primeros IDs: {ids_str}"
            elif id_col_exists: content_v7 += "<br>- IDs no disponibles." # Si la col ID existe pero no se recuperaron IDs (raro)
            content_v7 += "</li>"
        content_v7 += "</ul>"

    if status_v7 == "Correcto" and cols_chequeadas_existentes:
        content_v7 = f"<span class='status-correcto-inline'>[Correcto]</span> No se encontraron nulos en columnas demográficas ({', '.join(cols_chequeadas_existentes)})."

    validation_results.append({'key': key_v7, 'status': status_v7, 'content': content_v7})


    # V8: Abiertas ('Menciona') (Usa df_textual_full para buscar todas las 'menciona', df_textual_renamed para obtener IDs)
    key_v8 = "Abiertas ('Menciona')"; content_v8 = ""; status_v8 = "Info"
    try:
        id_auth = '[auth]';
        if id_auth not in df_textual_renamed.columns: raise KeyError(f"Columna ID '{id_auth}' no encontrada para reporte de abiertas.")

        # Buscar columnas 'menciona' en el DF ORIGINAL (antes de filtrar)
        # Usamos df_textual_full.columns que tiene los nombres únicos post-deduplicación
        cols_m_original_dedup = [c for c in df_textual_full.columns if c.split('.')[0] == 'Menciona' or ("menciona" in str(c).lower() and "mencionaste" not in str(c).lower())]
        total_p = len(cols_m_original_dedup)

        if not cols_m_original_dedup:
            content_v8 = "<span class='status-info-inline'>[INFO]</span> No se encontraron columnas que contengan 'menciona' en el archivo textual original."
        else:
            # Seleccionar estas columnas y el ID del DF RENOMBRADO
            # Mapear los nombres deduplicados a los nombres estándar si existen en el renombrado
            cols_m_renamed = [rename_map_txt.get(c.split('.')[0], c) # Intentar mapear el nombre base
                              for c in cols_m_original_dedup
                              if rename_map_txt.get(c.split('.')[0], c) in df_textual_renamed.columns]
            # Eliminar duplicados si el mapeo causa que varias 'Menciona.X' apunten a la misma
            cols_m_renamed = list(dict.fromkeys(cols_m_renamed))

            cols_to_melt = [id_auth] + cols_m_renamed
            if len(cols_to_melt) > 1: # Si encontramos al menos una col 'menciona' renombrada y mapeada
                melted = df_textual_renamed[cols_to_melt].melt(id_vars=[id_auth], var_name='Pregunta_Std', value_name='Respuesta')
                final_abiertas = melted.dropna(subset=['Respuesta'])
                # Convertir respuesta a string para evitar errores en display
                final_abiertas['Respuesta'] = final_abiertas['Respuesta'].astype(str)
                # Filtrar respuestas vacías o que solo sean espacios
                final_abiertas = final_abiertas[final_abiertas['Respuesta'].str.strip() != '']

                if final_abiertas.empty:
                    content_v8 = f"<span class='status-info-inline'>[INFO]</span> Se encontraron {total_p} columnas 'menciona' en el original, pero no hay respuestas abiertas válidas después del filtrado/renombrado."
                else:
                    total_r = len(final_abiertas); content_v8 += f"<span class='status-info-inline'>[REPORTE]</span> <b>{total_p}</b> cols 'menciona' encontradas en original, <b>{total_r}</b> respuestas abiertas no vacías.<br><br>";
                    
                    # --- AJUSTE 4: Preparar datos para descarga ---
                    df_para_descarga_abiertas = final_abiertas[[id_auth, 'Pregunta_Std', 'Respuesta']].copy()
                    df_para_descarga_abiertas.columns = ['ID', 'Pregunta', 'Respuesta']
                    
                    # --- AJUSTE 4: Mostrar Pregunta en reporte V8 ---
                    df_disp = final_abiertas[[id_auth, 'Pregunta_Std', 'Respuesta']]
                    if total_r > 500: content_v8 += f"(Se muestran las primeras 500)<br>"; df_disp = df_disp.head(500)
                    df_disp.columns = [id_auth, 'Pregunta', 'Respuesta'] # Renombrar para display
                    content_v8 += df_disp.to_html(classes='df-style', index=False)
            else:
                content_v8 = f"<span class'status-info-inline'>[INFO]</span> Se encontraron {total_p} columnas 'menciona' en el original, pero ninguna existe o está mapeada correctamente en el archivo procesado."

    except KeyError as e_v8: status_v8 = "Error"; content_v8 = f"<span class'status-error-inline'>[ERROR]</span> {e_v8}<br>"
    except Exception as e_v8_gen: status_v8 = "Error"; content_v8 = f"<span class'status-error-inline'>[ERROR Inesperado V8]</span> {e_v8_gen}<br>"
    validation_results.append({'key': key_v8, 'status': status_v8, 'content': content_v8})


    # V9: Ponderador vs Total Filas (Usa df_numerico_renamed)
    key_v9 = "Ponderador vs Total Filas"; content_v9 = ""; status_v9 = "Correcto"; col_pond = 'Ponderador'
    # Solo ejecutar si no es Colombia Minors
    if pais_clave_interna == 'Colombia Minors':
        status_v9 = "Info"
        content_v9 = "<span class='status-info-inline'>[INFO]</span> Validación no aplica para Colombia Minors."
    else:
        try:
            if col_pond not in df_numerico_renamed.columns: raise KeyError(f"Columna '{col_pond}' no encontrada después del renombrado.")
            # Intentar convertir a numérico, errores a NaN
            ponderador_numeric = pd.to_numeric(df_numerico_renamed[col_pond], errors='coerce')
            # Sumar ignorando NaN
            suma_ponderador = ponderador_numeric.sum()
            # Contar filas donde la conversión falló
            errores_conversion = ponderador_numeric.isnull().sum() - df_numerico_renamed[col_pond].isnull().sum() # Restar nulos originales

            total_filas = df_numerico_renamed.shape[0] # Usar total filas del DF renombrado

            suma_str = f"{suma_ponderador:,.2f}" if pd.notna(suma_ponderador) and suma_ponderador != int(suma_ponderador) else f"{int(suma_ponderador):,}" if pd.notna(suma_ponderador) else "Error en suma"
            total_str = f"{total_filas:,}"

            content_v9 += f"- Suma '{col_pond}': {suma_str}<br>- Total Filas: {total_str}<br>"
            if errores_conversion > 0:
                content_v9 += f"<br><span class='status-error-inline'>[WARN]</span> Hubo {errores_conversion} valores en '{col_pond}' que no pudieron ser convertidos a número y fueron ignorados en la suma.<br>"
                status_v9 = "Error" # Si hay errores de conversión, marcar como Error

            content_v9 += "<br><b>Comparación:</b><br>"
            # Comparar solo si la suma fue exitosa
            if pd.notna(suma_ponderador):
                if np.isclose(suma_ponderador, total_filas, atol=1e-5):
                    # Si coincide pero hubo errores de conversión, el estado sigue siendo Error
                    if status_v9 != "Error":
                        content_v9 += "<span class='status-correcto-inline'>[Correcto]</span> La suma coincide con el total de filas."
                    else:
                         content_v9 += "<span class='status-info-inline'>[INFO]</span> La suma (ignorando errores) coincide con el total de filas."
                else:
                    status_v9 = "Incorrecto" # Si no coincide, es Incorrecto (sobrescribe Error si lo era)
                    content_v9 += f"<span class='status-incorrecto-inline'>[Incorrecto]</span> La suma NO coincide con el total de filas. Diferencia: {suma_ponderador - total_filas:,.2f}"
            else:
                status_v9 = "Error" # Si la suma falló completamente
                content_v9 += "<span class='status-error-inline'>[ERROR]</span> No se pudo calcular la suma del ponderador."

        except KeyError as e: status_v9 = "Error"; content_v9 = f"<span class'status-error-inline'>[ERROR]</span> {e}"
        except Exception as e_v9: status_v9 = "Error"; content_v9 = f"<span class'status-error-inline'>[ERROR Inesperado V9]</span> al sumar '{col_pond}': {e_v9}"
    validation_results.append({'key': key_v9, 'status': status_v9, 'content': content_v9})


    # V10: Suma Ponderador por Demo (Usa df_numerico_renamed)
    key_v10 = "Suma Ponderador por Demográfico"; content_v10 = ""; status_v10 = "Info"; col_pond = 'Ponderador'
    cols_demo = ['NSE', 'gender', 'AGErange', 'Region']

    # Solo ejecutar si no es Colombia Minors
    if pais_clave_interna == 'Colombia Minors':
        status_v10 = "Info"
        content_v10 = "<span class='status-info-inline'>[INFO]</span> Validación no aplica para Colombia Minors."
    else:
        missing_cols_v10 = []
        if col_pond not in df_numerico_renamed.columns: missing_cols_v10.append(col_pond)
        for d_col in cols_demo:
            if d_col not in df_numerico_renamed.columns: missing_cols_v10.append(d_col)

        if missing_cols_v10:
             status_v10 = "Error"; content_v10 = f"<span class='status-error-inline'>[ERROR]</span> Faltan columnas requeridas después del renombrado: {', '.join(missing_cols_v10)}"
        else:
            try:
                # Crear copia y columna numérica para Ponderador
                temp_df_v10 = df_numerico_renamed.copy()
                temp_df_v10['Ponderador_Num'] = pd.to_numeric(temp_df_v10[col_pond], errors='coerce')
                errores_conv_v10 = temp_df_v10['Ponderador_Num'].isnull().sum() - temp_df_v10[col_pond].isnull().sum()
                if errores_conv_v10 > 0:
                    content_v10 += f"<span class='status-error-inline'>[WARN]</span> {errores_conv_v10} valores de '{col_pond}' no numéricos fueron tratados como 0.<br>"
                    # Llenar NaNs en la columna numérica con 0 para que no afecten la suma por grupo
                    temp_df_v10['Ponderador_Num'].fillna(0, inplace=True)

                all_results = []
                for dem_col in cols_demo:
                    # Agrupar por la columna demográfica (fillna ANTES de agrupar)
                    suma_grupo = temp_df_v10.fillna({dem_col: 'VACÍO/NULO'}).groupby(dem_col)['Ponderador_Num'].sum().reset_index()
                    total_suma_variable = suma_grupo['Ponderador_Num'].sum()

                    if total_suma_variable > 0:
                        suma_grupo['Porcentaje'] = (suma_grupo['Ponderador_Num'] / total_suma_variable) * 100
                    else:
                        suma_grupo['Porcentaje'] = 0.0

                    suma_grupo.rename(columns={dem_col: 'Categoría', 'Ponderador_Num': 'Suma Ponderador'}, inplace=True)
                    suma_grupo['Variable'] = dem_col;
                    # Asegurar el orden de columnas deseado
                    all_results.append(suma_grupo[['Variable', 'Categoría', 'Suma Ponderador', 'Porcentaje']])

                if all_results:
                    final_table = pd.concat(all_results, ignore_index=True)
                    # Formatear números
                    final_table['Suma Ponderador'] = final_table['Suma Ponderador'].apply(lambda x: f"{x:,.2f}" if pd.notna(x) and x != int(x) else f"{int(x):,}" if pd.notna(x) else "Error")
                    final_table['Porcentaje'] = final_table['Porcentaje'].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "-")
                    content_v10 += final_table.to_html(classes='df-style', index=False)
                else:
                    content_v10 += "<span class='status-info-inline'>[INFO]</span> No se generaron resultados para la suma de ponderador.";
                    status_v10 = "Error" # Si no hay resultados, algo falló

            except Exception as e_v10:
                status_v10 = "Error";
                content_v10 += f"<span class='status-error-inline'>[ERROR Inesperado V10]</span> {e_v10}"
    validation_results.append({'key': key_v10, 'status': status_v10, 'content': content_v10})


    # V11: Volumetría (Usa df_numerico_renamed)
    key_v11 = "Volumetría (Umbrales Numéricos)"; content_v11 = ""; status_v11 = "Correcto"; id_unico = 'Unico'
    errores_umbrales = []
    reglas_pais = THRESHOLDS_POR_PAIS.get(pais_clave_interna, [])
    if not reglas_pais:
        status_v11 = "Info"; content_v11 = f"<span class'status-info-inline'>[INFO]</span> No hay regras de volumetría definidas para {pais_seleccionado_display}."
    else:
        id_col_ok_v11 = id_unico in df_numerico_renamed.columns
        if not id_col_ok_v11: content_v11 += f"<span class'status-error-inline'>[WARN]</span> Columna ID '{id_unico}' no encontrada para reportar violaciones.<br>"

        for regla in reglas_pais:
            col = regla['col']; cond = regla['cond']; lim = regla['lim']
            # Chequear si la columna existe en el DF renombrado
            if col not in df_numerico_renamed.columns:
                # Verificar si la columna simplemente no aplica (mapeada a '')
                map_exists = COLUMN_MAPPING['Base Numérica'].get(col, {}).get(pais_clave_interna)
                if map_exists != '': # Si no está mapeada a vacío, debería existir
                    errores_umbrales.append({'Columna': col, 'Error': 'No encontrada después del renombrado', 'ID': '-', 'Valor': '-'})
                    if status_v11 != "Error": status_v11 = "Error"
                # Si está mapeada a '', ignorar esta regla
                continue

            try:
                col_numerica = pd.to_numeric(df_numerico_renamed[col], errors='coerce')
                # Chequear errores de conversión
                errores_conv_v11 = col_numerica.isnull().sum() - df_numerico_renamed[col].isnull().sum()
                if errores_conv_v11 > 0 and status_v11 != "Error":
                    status_v11 = "Error" # Marcar como error si hay problemas de conversión
                    content_v11 += f"<span class='status-error-inline'>[ERROR Conversión]</span> {errores_conv_v11} valores no numéricos en '{col}'.<br>"

            except Exception as e_conv:
                errores_umbrales.append({'Columna': col, 'Error': f'Error al convertir a numérico: {e_conv}', 'ID': '-', 'Valor': '-'})
                if status_v11 != "Error": status_v11 = "Error"
                continue # Saltar al siguiente regla si falla la conversión

            violaciones = pd.Series(False, index=df_numerico_renamed.index); cond_desc = ""
            try:
                if cond == 'mayor_a': violaciones = col_numerica.gt(lim) & col_numerica.notna(); cond_desc = f"> {lim}"
                elif cond == 'igual_a': violaciones = col_numerica.eq(lim) & col_numerica.notna(); cond_desc = f"== {lim}"
                # Añadir otras condiciones si son necesarias en el futuro
                else:
                    raise ValueError(f'Condición "{cond}" no reconocida')

                df_violaciones = df_numerico_renamed.loc[violaciones] # Usar máscara en DF renombrado

                if not df_violaciones.empty:
                    if status_v11 == "Correcto": status_v11 = "Incorrecto" # Marcar incorrecto si hay violaciones
                    for idx, row in df_violaciones.head().iterrows(): # Mostrar solo las primeras 5 violaciones por regla
                        uid = row[id_unico] if id_col_ok_v11 else f"Fila {idx+2}"
                        valor_violador_num = col_numerica.loc[idx] # Obtener valor numérico que violó
                        try: # Formatear valor
                            valor_violador_str = f"{valor_violador_num:,.2f}" if isinstance(valor_violador_num, (float, np.floating)) and valor_violador_num != int(valor_violador_num) else f"{int(valor_violador_num):,}"
                        except: valor_violador_str = str(row[col]) # Fallback al valor original

                        errores_umbrales.append({'Columna': col, 'Error': f'Valor viola {cond_desc}', 'ID': uid, 'Valor': valor_violador_str})
            except ValueError as e_cond: # Capturar error de condición no reconocida
                errores_umbrales.append({'Columna': col, 'Error': str(e_cond), 'ID': '-', 'Valor': '-'})
                if status_v11 != "Error": status_v11 = "Error"
            except Exception as e_val: # Otros errores durante la validación
                errores_umbrales.append({'Columna': col, 'Error': f'Error validando: {e_val}', 'ID': '-', 'Valor': '-'})
                if status_v11 != "Error": status_v11 = "Error"


        # Construir contenido final de V11
        if status_v11 == "Correcto": content_v11 = f"<span class='status-correcto-inline'>[Correcto]</span> Todas las columnas aplicables cumplen los umbrales."
        else:
            prefix = ""
            if status_v11 == "Incorrecto": prefix = f"<span class='status-incorrecto-inline'>[Incorrecto]</span> Se encontraron valores fuera de umbral (se muestran max 5 por regla):<br>"
            if status_v11 == "Error": prefix = f"<span class'status-error-inline'>[ERROR]</span> Errores encontrados durante la validación de umbrales:<br>{content_v11}" # Incluir errores de conversión si hubo
            if errores_umbrales:
                df_errores = pd.DataFrame(errores_umbrales)[['Columna', 'Error', 'ID', 'Valor']]
                content_v11 = prefix + df_errores.to_html(classes='df-style', index=False)
            elif status_v11 == "Error": # Si es error pero no hay detalles específicos de umbrales
                content_v11 = prefix # Ya contiene el error de conversión
            else: # Si es Incorrecto pero por alguna razón no hay detalles
                content_v11 = prefix + "(Sin detalles específicos de violaciones)"

    validation_results.append({'key': key_v11, 'status': status_v11, 'content': content_v11})


    # V12: Duplicados en IDs Principales (Usa df_numerico y df_textual)
    key_v12 = "Duplicados en IDs Principales"; content_v12 = ""; status_v12 = "Correcto"
    col_num_v12 = 'Unico'; col_txt_v12 = '[auth]'
    try:
        # Checar Numérico ('Unico') - Ya sabemos que existe por chequeo previo
        dups_num_mask = df_numerico[col_num_v12].duplicated(keep=False) # Marcar TODOS los duplicados
        total_dups_num = dups_num_mask.sum()
        if total_dups_num > 0:
            status_v12 = "Incorrecto"
            ids_dup_num_vals = df_numerico.loc[dups_num_mask, col_num_v12].unique()
            content_v12 += f"<span class='status-incorrecto-inline'>[Incorrecto]</span> <b>{total_dups_num}</b> filas involucradas en duplicados de <b>'{col_num_v12}'</b> (Num).<br>Valores duplicados (max 5): {list(ids_dup_num_vals[:5])}<br>"
        else:
            content_v12 += f"<span class='status-correcto-inline'>[Correcto]</span> Sin duplicados en <b>'{col_num_v12}'</b> (Num).<br>"

        # Checar Textual ('[auth]') - Ya sabemos que existe
        dups_txt_mask = df_textual[col_txt_v12].duplicated(keep=False) # Marcar TODOS los duplicados
        total_dups_txt = dups_txt_mask.sum()
        if total_dups_txt > 0:
            status_v12 = "Incorrecto" # Asegurar estado incorrecto
            ids_dup_txt_vals = df_textual.loc[dups_txt_mask, col_txt_v12].unique()
            content_v12 += f"<span class='status-incorrecto-inline'>[Incorrecto]</span> <b>{total_dups_txt}</b> filas involucradas en duplicados de <b>'{col_txt_v12}'</b> (Txt).<br>Valores duplicados (max 5): {list(ids_dup_txt_vals[:5])}<br>"
        else:
            # Añadir mensaje de correcto solo si no había duplicados numéricos tampoco
            if status_v12 == "Correcto":
                content_v12 += f"<span class='status-correcto-inline'>[Correcto]</span> Sin duplicados en <b>'{col_txt_v12}'</b> (Txt).<br>"
            else: # Si hubo numéricos, solo añadir info
                content_v12 += f"<span class='status-info-inline'>[INFO]</span> Sin duplicados en <b>'{col_txt_v12}'</b> (Txt).<br>"

    except Exception as e_v12:
        status_v12 = "Error"
        content_v12 = f"<span class='status-error-inline'>[ERROR Inesperado V12]</span> {e_v12}"
    validation_results.append({'key': key_v12, 'status': status_v12, 'content': content_v12})


    # V13: Duplicados en [panelistid] (Usa df_textual_renamed)
    key_v13 = "Duplicados en [panelistid]"; content_v13 = ""; status_v13 = "Info"
    col_panel = '[panelistid]'; col_auth_v13 = '[auth]'
    try:
        # Chequear si la columna panelistid existe DESPUÉS del renombrado
        if col_panel not in df_textual_renamed.columns:
            # Verificar si estaba mapeada a '' (no aplica)
            map_exists = COLUMN_MAPPING['Base Textual'].get(col_panel, {}).get(pais_clave_interna)
            if map_exists == '':
                content_v13 = f"<span class='status-info-inline'>[INFO]</span> Columna '{col_panel}' no aplica o no mapeada para {pais_clave_interna}."
            else:
                raise KeyError(f"Columna '{col_panel}' no encontrada después del renombrado.")
        elif col_auth_v13 not in df_textual_renamed.columns:
             raise KeyError(f"Columna ID '{col_auth_v13}' no encontrada para reporte de duplicados '{col_panel}'.")
        else: # Si ambas columnas existen
            df_check = df_textual_renamed[[col_auth_v13, col_panel]].dropna(subset=[col_panel]) # Usar DF renombrado y quitar nulos en panelistid
            total_filas_validas = len(df_check)

            if total_filas_validas > 0:
                dups_mask_v13 = df_check[col_panel].duplicated(keep=False) # Marcar TODOS los duplicados
                total_filas_duplicadas = dups_mask_v13.sum()

                if total_filas_duplicadas > 0:
                    df_dups_v13 = df_check[dups_mask_v13]
                    ids_unicos_duplicados = df_dups_v13[col_panel].nunique()

                    content_v13 += f"<span class='status-info-inline'>[REPORTE]</span> Se encontraron <b>{total_filas_duplicadas}</b> filas (de {total_filas_validas} no nulas) con <b>{ids_unicos_duplicados}</b> '{col_panel}' duplicados.<br>"
                    porcentaje_dup = (total_filas_duplicadas / total_filas_validas) * 100 if total_filas_validas > 0 else 0
                    content_v13 += f"- Porcentaje Duplicado (sobre no nulos): <b>{porcentaje_dup:.2f}%</b><br><br>"
                    content_v13 += f"Reporte de '{col_panel}' duplicados y su frecuencia:<br>"

                    conteo_dups = df_dups_v13.groupby(col_panel)[col_auth_v13].count().reset_index()
                    conteo_dups.columns = [col_panel, 'Veces Repetido']
                    conteo_dups = conteo_dups.sort_values(by='Veces Repetido', ascending=False)

                    content_v13 += conteo_dups.head(500).to_html(classes='df-style', index=False) # Mostrar hasta 500
                    if len(conteo_dups) > 500:
                        content_v13 += "<br>(Se muestran los primeros 500 panelistid duplicados)"
                else:
                    content_v13 += f"<span class='status-info-inline'>[REPORTE]</span> No se encontraron duplicados en <b>'{col_panel}'</b> (sobre {total_filas_validas} valores no nulos)."
            else:
                content_v13 += f"<span class='status-info-inline'>[INFO]</span> La columna '{col_panel}' está completamente vacía o no se encontró."


    except KeyError as e_v13:
        status_v13 = "Error"
        content_v13 = f"<span class='status-error-inline'>[ERROR]</span> {e_v13}"
    except Exception as e_v13_gen:
         status_v13 = "Error"
         content_v13 = f"<span class='status-error-inline'>[ERROR inesperado V13]</span> {e_v13_gen}"

    validation_results.append({'key': key_v13, 'status': status_v13, 'content': content_v13})
    
    
    # --- AJUSTE 3: NUEVA VALIDACIÓN V14 ---
    key_v14 = "Conteo de Demográficos"; content_v14 = ""; status_v14 = "Info"
    cols_v14 = ['gender', 'AGErange', 'NSE', 'Region']
    cols_encontradas_v14 = []
    
    try:
        for col in cols_v14:
            if col in df_numerico_renamed.columns: # Usar df_numerico_renamed para conteo total
                cols_encontradas_v14.append(col)
                content_v14 += f"<h3 class='sub-heading'>{col}</h3>"
                
                counts = df_numerico_renamed[col].fillna('VACÍO/NULO').value_counts().reset_index()
                counts.columns = ['Categoría', 'Total']
                total_general = counts['Total'].sum()
                
                if total_general > 0:
                    counts['Porcentaje'] = (counts['Total'] / total_general * 100).apply(lambda x: f"{x:.1f}%")
                else:
                    counts['Porcentaje'] = "0.0%"
                    
                counts['Total'] = counts['Total'].apply(lambda x: f"{x:,}") # Formatear con comas
                content_v14 += counts.to_html(classes='df-style', index=False)
                
            else:
                content_v14 += f"<h3 class='sub-heading'>{col}</h3>"
                content_v14 += f"<span class='status-error-inline'>[ERROR]</span> Columna '{col}' no encontrada en base numérica (después de renombrar).<br>"
                if status_v14 != "Error": status_v14 = "Error"
        
        if not cols_encontradas_v14:
             content_v14 = "<span class='status-error-inline'>[ERROR]</span> Ninguna de las columnas demográficas requeridas fue encontrada."
             status_v14 = "Error"
             
    except Exception as e_v14:
        status_v14 = "Error"
        content_v14 = f"<span class='status-error-inline'>[ERROR inesperado V14]</span> {e_v14}"

    validation_results.append({'key': key_v14, 'status': status_v14, 'content': content_v14})
    # --- FIN AJUSTE 3 ---


    # --- FIN VALIDACIONES ---

    st.success("Proceso de validación terminado.")
    
    # --- AJUSTE 4: Botón de descarga para Abiertas ---
    st.markdown("### 🔽 Descargar Reporte de Abiertas")
    if not df_para_descarga_abiertas.empty:
        excel_abiertas = to_excel(df_para_descarga_abiertas)
        st.download_button(
            label="Descargar Abiertas (ID, Pregunta, Respuesta) (.xlsx)",
            data=excel_abiertas,
            file_name=f'reporte_abiertas_{pais_seleccionado_display}.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            key='dl_abiertas'
        )
    else:
        st.info("No se encontraron respuestas abiertas para descargar (o la V8 falló).")
    # --- FIN AJUSTE 4 ---
    
    
    st.divider()

    # --- ÁREA DE REPORTE ESTILIZADO ---
    sort_order = {'Correcto': 1, 'Incorrecto': 2, 'Error': 3, 'Info': 4}
    # Asegurarse que cada 'v' tenga 'key' antes de ordenar
    valid_results_for_sort = [v for v in validation_results if 'key' in v]
    if len(valid_results_for_sort) != len(validation_results):
        st.error("Error interno: No todos los resultados de validación tenían una 'key'. Revisar código de validaciones.")
        # Opcional: mostrar los resultados que sí son válidos
        sorted_results_temp = sorted(valid_results_for_sort, key=lambda v: sort_order.get(v['status'], 5))
    else:
        sorted_results_temp = sorted(validation_results, key=lambda v: sort_order.get(v['status'], 5))

    final_numbered_results = []
    for i, v in enumerate(sorted_results_temp):
        # Usar el número original de la validación si es posible (basado en key_vX)
        validation_num_str = ''.join(filter(str.isdigit, v['key'].split(':')[0])) if ':' in v['key'] else str(i + 1)
        # Asegurar que v['key'] existe antes de usarla
        current_key = v.get('key', f'Resultado_{i+1}') # Usar un default si falta key
        new_title = f"Validación {validation_num_str}: {current_key}"
        final_numbered_results.append({'title': new_title, 'status': v.get('status', 'Error'), 'content': v.get('content', 'Contenido no disponible')})

    correct_count = sum(1 for v in final_numbered_results if v['status'] == 'Correcto'); incorrect_count = sum(1 for v in final_numbered_results if v['status'] == 'Incorrecto')
    info_count = sum(1 for v in final_numbered_results if v['status'] == 'Info'); error_count = sum(1 for v in final_numbered_results if v['status'] == 'Error')
    total_validations_criticas = correct_count + incorrect_count + error_count # Excluir Info del %
    correct_pct = (correct_count / total_validations_criticas * 100) if total_validations_criticas > 0 else 0;
    incorrect_pct = (incorrect_count / total_validations_criticas * 100) if total_validations_criticas > 0 else 0

    st.subheader("--- RESUMEN DE VALIDACIÓN ---", divider='violet')
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("✅ Correctos", f"{correct_count}", f"{correct_pct:.1f}% de críticas"); col2.metric("❌ Incorrectos", f"{incorrect_count}", f"{incorrect_pct:.1f}% de críticas")
    col3.metric("⚠️ Errores", f"{error_count}"); col4.metric("ℹ️ Reportes", f"{info_count}")

    with st.expander("Ver lista detallada de verificaciones", expanded=False):
        summary_list_html = "<div class='summary-list'><ul>";
        for v in final_numbered_results:
            icon = "✅" if v['status'] == 'Correcto' else "❌" if v['status'] == 'Incorrecto' else "⚠️" if v['status'] == 'Error' else "ℹ️"
            status_inline_class = f"status-{v['status'].lower()}-inline"
            summary_list_html += f"<li>{icon} <strong>{v['title']}:</strong> <span class='{status_inline_class}'>{v['status']}</span></li>"
        summary_list_html += "</ul></div>"; st.markdown(summary_list_html, unsafe_allow_html=True)

    st.divider()

    st.subheader("--- REPORTE DETALLADO ---", divider='violet')
    for v in final_numbered_results:
        status_class = f"status-{v['status'].lower()}"
        content_detalle = v['content']
        # --- CORRECCIÓN v2.24: Usar v['title'] para la comprobación ---
        # --- MODIFICADO v2.30: Añadir V14 (Conteo) a la lógica de sub-heading ---
        if 'title' in v and ("Agrupaciones" in v['title'] or "Conteo de Demográficos" in v['title']):
             content_detalle = content_detalle.replace("<h3>5.1:", "<h3 class='sub-heading'>5.1:").replace("<h3>5.2:", "<h3 class='sub-heading'>5.2:").replace("<h3>5.3:", "<h3 class='sub-heading'>5.3:").replace("<h3>5.4:", "<h3 class'sub-heading'>5.4:")
        # --- FIN CORRECCIÓN/MODIFICACIÓN ---
        
        # Reemplazar <br> y \n para seguridad HTML
        safe_content = str(content_detalle).replace('<br>', '<br/>').replace('\n', '') # Asegurar que sea string
        # Eliminar posible doble <br/> si ya existe
        safe_content = safe_content.replace('<br/><br/>', '<br/>')

        # Asegurarse que 'title' existe antes de usarlo
        current_title = v.get('title', 'Validación Desconocida')
        html_content = f"""<div class'validation-box {status_class}'><h3>{current_title}</h3>{safe_content}</div>"""
        st.markdown(html_content, unsafe_allow_html=True)

# Mensaje final si no se cargaron archivos
elif not uploaded_file_num and not uploaded_file_txt:
     st.info("Esperando la carga de los archivos Excel Numérico y Textual...")
elif not uploaded_file_num:
     st.warning("Falta cargar el archivo Numérico.")
elif not uploaded_file_txt:
     st.warning("Falta cargar el archivo Textual.")