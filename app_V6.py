# --- validador_app.py ---
# Versión Atlantia 2.33 (Ajuste Mapeo Region MX, Validación Geo Global, Visualización Total y V3 con lastpage_Parte3)

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
atlantia_css = """
<style>
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
    .status-info-inline { color: var(--validation-info-text) !important; font-weight: bold; }


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
* **Unico valor en (lastpage, lastpage2, lastpage3):** Revisa unicidad.
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
    'Panamá': {'Centro': ['Aguadulce', 'Antón', 'La Pintada', 'Natá', 'Olá', 'Penonomé','Chagres', 'Ciudad de Colón', 'Colón', 'Donoso', 'Portobelo','Resto del Distrito', 'Santa Isabel', 'La Chorrera', 'Arraiján','Capira', 'Chame', 'San Carlos'],'Metro': ['Panamá', 'San Miguelito', 'Balboa', 'Chepo', 'Chimán', 'Taboga', 'Chepigana', 'Pinogana'],'Oeste': ['Alanje', 'Barú', 'Boquerón', 'Boquete', 'Bugaba', 'David', 'Dolega', 'Gualaca', 'Remedios', 'Renacimiento', 'San Félix', 'San Lorenzo', 'Tolé', 'Bocas del Toro', 'Changuinola', 'Chiriquí Grande', 'Chitré', 'Las Minas', 'Los Pozos', 'Ocú', 'Parita', 'Pesé', 'Santa María', 'Guararé', 'Las Tablas', 'Los Santos', 'Macaracas', 'Pedasí', 'Pocrí', 'Tonosí', 'Atalaya', 'Calobre', 'Cañazas', 'La Mesa', 'Las Palmas', 'Mariato', 'Montijo', 'Río de Jesús', 'San Francisco', 'Santa Fé', 'Santiago', 'Soná']},
    'México': {'Central/Bajío': ['CDMX + AM', 'Estado de México', 'Guanajuato', 'Hidalgo','Morelos', 'Puebla', 'Querétaro', 'Tlaxcala'],'Norte': ['Baja California Norte', 'Chihuahua', 'Coahuila','Durango', 'Nuevo León', 'Sonora', 'Tamaulipas'],'Occidente/Pacifico': ['Aguascalientes', 'Colima', 'Guerrero', 'Jalisco', 'Michoacan','Nayarit', 'San Luis Potosi', 'Zacatecas', 'Sinaloa', 'Baja California Sur'],'Sureste': ['Campeche', 'Chiapas', 'Oaxaca', 'Quintana Roo', 'Tabasco','Veracruz', 'Yucatán']},
    'Colombia': {'Andes': ['Antioquia', 'Caldas', 'Quindio', 'Risaralda', 'Santander'],'Centro': ['Bogotá', 'Boyacá', 'Casanare', 'Cundinamarca'],'Norte': ['Atlántico', 'Bolívar', 'Cesar', 'Córdoba', 'La Guajira', 'Magdalena', 'Norte de Santader', 'Sucre'], 'Sur': ['Cauca', 'Huila', 'Meta', 'Nariño', 'Tolima', 'Valle de Cauca']},
    'Ecuador': {'Costa': ['El Oro', 'Esmeraldas', 'Los Ríos', 'Manabí', 'Santa Elena', 'Santo Domingo de los Tsáchilas'],'Guayaquil': ['Guayas'],'Quito': ['Pichincha'],'Sierra': ['Azuay', 'Bolívar', 'Cañar', 'Carchi', 'Chimborazo', 'Cotopaxi', 'Imbabura', 'Loja', 'Tungurahua']},
    'Perú': {
        'Centro': ['Ayacucho', 'Huancavelica', 'Junín', 'Ica', 'Huánuco'],
        'Lima y Callao': ['Lima', 'Callao'],
        'Norte': ['Áncash', 'Cajamarca', 'La Libertad', 'Lambayeque', 'Piura', 'Tumbes'],
        'Oriente': ['Amazonas', 'Loreto', 'Pasco', 'San Martin', 'Ucayali'],
        'Sur': ['Apurimac', 'Arequipa', 'Cuzco', 'Madre de Dios', 'Moquegua', 'Puno', 'Tacna']
    },
    'R. Dominicana': {'Capital': ['Distrito Nacional', 'Santo Domingo'],'Region Este': ['El Seibo', 'Hato Mayor', 'La Altagracia', 'La Romana', 'Monte Plata', 'San Pedro de Macorís'],'Region norte/ Cibao': ['Dajabón', 'Duarte (San Francisco)', 'Espaillat', 'Hermanas Mirabal', 'La Vega', 'María Trinidad Sánchez', 'Monseñor Nouel', 'Montecristi', 'Puerto Plata', 'Samaná', 'Sánchez Ramírez', 'Santiago', 'Santiago Rodríguez', 'Valverde'],'Region Sur': ['Azua', 'Bahoruco', 'Barahona', 'Elías Piña', 'Independencia', 'Pedernales', 'Peravia', 'San Cristóbal', 'San José de Ocoa', 'San Juan']},
    'Honduras': {'Norte Ciudad': ['Cortés'],'Norte interior': ['Atlántida', 'Colón', 'Copán', 'Ocotepeque', 'Santa Bárbara', 'Yoro'],'Sur Ciudad': ['Francisco Morazán'],'Sur interior': ['Choluteca', 'Comayagua', 'El Paraíso', 'Intibucá', 'La Paz', 'Olancho', 'Valle']},
    'Guatemala': { 
        'Metro': ['Guatemala'],
        'Nor Oriente': ['Petén', 'Alta Verapaz', 'Zacapa', 'El Progreso', 'Izabal', 'Baja Verapaz'],
        'Nor Occidente': ['San Marcos', 'Quetzaltengango', 'Chimaltenango', 'Quiché', 'Totonicapán', 'Huehuetenango', 'Sololá', 'Sacatepequez'],
        'Sur Occidente': ['Suchitepéquez', 'Retalhuleu', 'Escuintla'],
        'Sur Oriente': ['Chiquimula', 'Jutiapa', 'Jalapa', 'Santa Rosa']
    },
    'El Salvador': {'AMSS': ['San Salvador'],'Centro': ['Cabañas', 'Chalatenango', 'Cuscatlán', 'La Libertad', 'La Paz', 'San Vicente'],'Occidente': ['Ahuachapán', 'Santa Ana', 'Sonsonate'],'Oriente': ['La Union', 'Morazán', 'San Miguel', 'Usulután']},
    'Costa Rica': {}, 'Puerto Rico': {},
    'Colombia Minors': {'Andes': ['Antioquia', 'Caldas', 'Quindio', 'Risaralda', 'Santander'],'Centro': ['Bogotá', 'Boyacá', 'Casanare', 'Cundinamarca'],'Norte': ['Atlántico', 'Bolívar', 'Cesar', 'Córdoba', 'La Guajira', 'Magdalena', 'Norte de Santader', 'Sucre'], 'Sur': ['Cauca', 'Huila', 'Meta', 'Nariño', 'Tolima', 'Valle de Cauca']}
}

CLASIFICACIONES_PERU_REGION2 = {
    'LIMA': ['Lima', 'Callao', 'Ica'],
    'NORTE': ['La Libertad', 'Lambayeque', 'Piura', 'Cajamarca', 'Áncash', 'Tumbes'],
    'CENTRO': ['Junín', 'Ayacucho', 'Huancavelica'],
    'SUR': ['Arequipa', 'Cuzco', 'Puno', 'Tacna', 'Moquegua', 'Apurimac', 'Madre de Dios'],
    'ORIENTE': ['Loreto', 'Huánuco', 'San Martin', 'Pasco', 'Ucayali', 'Amazonas']
}

THRESHOLDS_POR_PAIS = {
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
        'Unico': {'Panamá': 'Unico', 'México': 'Unico', 'Colombia': 'Unico', 'Ecuador': 'Unico', 'Perú': 'Unico', 'R. Dominicana': 'Unico', 'Honduras': 'Unico', 'El Salvador': 'Unico', 'Guatemala': 'Unico', 'Colombia Minors': 'id'},
        'lastpage': {'Panamá': 'lastpage', 'México': 'lastpage', 'Colombia': 'lastpage', 'Ecuador': 'lastpage', 'Perú': 'lastpage', 'R. Dominicana': 'lastpage', 'Honduras': 'lastpage', 'El Salvador': 'lastpage', 'Guatemala': 'lastpage', 'Colombia Minors': 'lastpage'},
        'lastpage_Parte2': {'Panamá': 'lastpage_Parte2', 'México': 'lastpage_Parte2', 'Colombia': 'lastpage_Parte2', 'Ecuador': 'lastpage_Parte2', 'Perú': 'lastpage_Parte2', 'R. Dominicana': 'lastpage_Parte2', 'Honduras': 'lastpage_Parte2', 'El Salvador': 'lastpage_Parte2', 'Guatemala': 'lastpage_Parte2', 'Colombia Minors': ''},
        
        # --- AJUSTE V3: Agregar lastpage_Parte3 ---
        'lastpage_Parte3': {'Panamá': 'lastpage_Parte3', 'México': 'lastpage_Parte3', 'Colombia': 'lastpage_Parte3', 'Ecuador': 'lastpage_Parte3', 'Perú': 'lastpage_Parte3', 'R. Dominicana': 'lastpage_Parte3', 'Honduras': 'lastpage_Parte3', 'El Salvador': 'lastpage_Parte3', 'Guatemala': 'lastpage_Parte3', 'Colombia Minors': ''},
        
        'Ponderador': {'Panamá': 'Ponderador', 'México': 'Ponderador', 'Colombia': 'Ponderador', 'Ecuador': 'Ponderador', 'Perú': 'Ponderador', 'R. Dominicana': 'Ponderador', 'Honduras': 'Ponderador', 'El Salvador': 'Ponderador', 'Guatemala': 'Ponderador', 'Colombia Minors': ''},
        'NSE': {'Panamá': 'NSE', 'México': 'NSE', 'Colombia': 'NSE', 'Ecuador': 'NSE', 'Perú': 'NSE', 'R. Dominicana': 'NSE', 'Honduras': 'NSE', 'El Salvador': 'NSE', 'Guatemala': 'NSE', 'Colombia Minors': 'NSE'},
        'gender': {'Panamá': 'gender', 'México': 'gender', 'Colombia': 'gender', 'Ecuador': 'gender', 'Perú': 'gender', 'R. Dominicana': 'gender', 'Honduras': 'gender', 'El Salvador': 'gender', 'Guatemala': 'gender', 'Colombia Minors': 'gender'},
        'AGErange': {'Panamá': 'AGErange', 'México': 'AGErange', 'Colombia': 'AGErange', 'Ecuador': 'AGErange', 'Perú': 'AGErange', 'R. Dominicana': 'AGErange', 'Honduras': 'AGErange', 'El Salvador': 'AGErange', 'Guatemala': 'AGErange', 'Colombia Minors': 'AGErange'},
        
        # --- AJUSTE MÉXICO: Reemplazar 'Region 2026' por 'Region' ---
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
        'Por favor, selecciona el rango de edad en el que te encuentras:': {
            'Panamá': 'Por favor, selecciona el rango de edad en el que te encuentras:', 
            'México': 'Por favor, selecciona el rango de edad en el que te encuentras:', 
            'Colombia': 'Por favor, selecciona el rango de edad en el que te encuentras:', 
            'Ecuador': 'Por favor, selecciona el rango de edad en el que te encuentras:', 
            'Perú': 'Por favor, selecciona el rango de edad en el que te encuentras:', 
            'R. Dominicana': 'Por favor, selecciona el rango de edad en el que te encuentras:', 
            'Honduras': 'Por favor, selecciona el rango de edad en el que te encuentras:',
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
            'Honduras': 'EDAD',
            'El Salvador': 'AGE', 
            'Guatemala': 'AGE', 
            'Colombia Minors': 'A partir de esta sección te pediremos que respondas pensando sobre el consumo de bebidas de tus hijos entre 8 y 17 años.Si tienes más de 1 hijo en esta edad te pediremos que te enfoques en uno de tus hijos para responder sobre su consumo. ¿Qué edad t'
        },
        'NSE': {'Panamá': 'NSE', 'México': 'SEL AGRUPADO', 'Colombia': 'NSE', 'Ecuador': 'agrupado ows', 'Perú': 'SEL AGRUPADO', 'R. Dominicana': 'NSE', 'Honduras': 'NSE', 'El Salvador': 'NSE', 'Guatemala': 'NSE Agrupado', 'Colombia Minors': 'SEL AGRUPADO'},
        'NSE2': {'Panamá': 'NSE2', 'México': 'SEL SEPARADO', 'Colombia': 'NSE2', 'Ecuador': 'Clasificación NSE (HIDDEN VARIABLE)PUNTOS: 0', 'Perú': 'SEL SEPARADO', 'R. Dominicana': 'NSE2', 'Honduras': 'NSE2', 'El Salvador': '¿Cuál es el ingreso mensual promedio de su hogar?', 'Guatemala': 'NSE_Parte2', 'Colombia Minors': 'SEL SEPARADO'},
        'Region 1 (Centro/Metro/Oeste)': {'Panamá': 'Region 1 (Centro/Metro/Oeste)', 'México': 'region', 'Colombia': 'region_Parte2', 'Ecuador': 'Region', 'Perú': 'region', 'R. Dominicana': 'region', 'Honduras': 'Region',
         'El Salvador': 'REGION', 'Guatemala': 'region', 'Colombia Minors': 'region'},
        'CIUDAD': {'Panamá': 'CIUDAD', 'México': 'Estado donde vive:', 'Colombia': 'Por favor escribe el nombre de la ciudad en la que vives:', 'Ecuador': 'Estado', 'Perú': 'state', 'R. Dominicana': 'state', 'Honduras': 'Estado',
         'El Salvador': 'ESTADO', 'Guatemala': 'state', 'Colombia Minors': 'Departamento:'},
        'Region2': {'Perú': 'region2'},
        'Origen': {'Panamá': 'Origen', 'México': 'Origen', 'Colombia': '', 'Ecuador': 'Origen del registro', 'Perú': '', 'R. Dominicana': '', 'Honduras': '', 'El Salvador': '', 'Guatemala': '', 'Colombia Minors': ''},
    }
}
# ---

# --- SELECCIÓN DE PAÍS Y CARGA DE ARCHIVOS ---
col_pais, col_vacia = st.columns([1, 2])
with col_pais:
    pais_seleccionado_display = st.selectbox("Selecciona el País:", paises_disponibles, key="select_pais")

# --- Botones de Descarga ---
st.markdown("### Descargar Reglas de Validación")
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

with col_dl3:
    if pais_seleccionado_display == 'Perú':
        reglas_geo_r2 = CLASIFICACIONES_PERU_REGION2
        if reglas_geo_r2:
            lista_g_r2 = [{'Región 2': r, 'Ciudad/Dpto': c} for r, ciudades in reglas_geo_r2.items() for c in ciudades]
            df_geo_r2 = pd.DataFrame(lista_g_r2)
            excel_geo_r2 = to_excel(df_geo_r2)
            st.download_button(label="Descargar Reglas Geo 2 (Perú)", data=excel_geo_r2, file_name=f'reglas_geografia_r2_Peru.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', key='dl_geo_r2')
        else: st.info("No hay reglas de Geografía 2 para Perú.")
    else: st.empty() 

st.divider()

st.markdown("### Descargar Mapeo de Columnas")
try:
    df_mapeo = create_mapping_dataframe(COLUMN_MAPPING, paises_disponibles)
    excel_mapeo = to_excel(df_mapeo)
    st.download_button(label="Descargar Mapeo Completo (.xlsx)", data=excel_mapeo, file_name='mapeo_columnas_completo.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', key='dl_mapeo')
except Exception as e_map:
    st.error(f"No se pudo generar el archivo de mapeo: {e_map}")

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
    df_para_descarga_abiertas = pd.DataFrame()

    try:
        df_numerico_full = pd.read_excel(io.BytesIO(uploaded_file_num.getvalue()))
        df_textual_full = pd.read_excel(io.BytesIO(uploaded_file_txt.getvalue()))

        df_numerico_full = deduplicate_columns(df_numerico_full.copy(), operation_name="lectura (Numérico)")
        df_textual_full = deduplicate_columns(df_textual_full.copy(), operation_name="lectura (Textual)")
    except Exception as e: st.error(f"Error al leer o pre-procesar archivos: {e}"); st.stop()

    rename_map_num = {}
    rename_map_txt = {}
    missing_original_cols = {'num': [], 'txt': []}

    for standard_name, country_mappings in COLUMN_MAPPING['Base Numérica'].items():
        if pais_clave_interna in country_mappings:
            country_specific_name = country_mappings[pais_clave_interna]
            if country_specific_name: 
                if country_specific_name in df_numerico_full.columns: rename_map_num[country_specific_name] = standard_name
                else: missing_original_cols['num'].append(country_specific_name)

    for standard_name, country_mappings in COLUMN_MAPPING['Base Textual'].items():
        if pais_clave_interna in country_mappings:
            country_specific_name = country_mappings[pais_clave_interna]
            if country_specific_name: 
                if country_specific_name in df_textual_full.columns: rename_map_txt[country_specific_name] = standard_name
                else: missing_original_cols['txt'].append(country_specific_name)

    if missing_original_cols['num']: st.warning(f"Advertencia: Cols no encontradas en Numérico: {', '.join(missing_original_cols['num'])}")
    if missing_original_cols['txt']: st.warning(f"Advertencia: Cols no encontradas en Textual: {', '.join(missing_original_cols['txt'])}")

    try:
        df_numerico_renamed = df_numerico_full.rename(columns=rename_map_num)
        df_textual_renamed = df_textual_full.rename(columns=rename_map_txt)
        df_numerico_renamed = deduplicate_columns(df_numerico_renamed.copy(), operation_name="renombrado (Numérico)")
        df_textual_renamed = deduplicate_columns(df_textual_renamed.copy(), operation_name="renombrado (Textual)")
    except Exception as e:
        st.error(f"Error during rename: {e}"); st.stop()

    # --- CHEQUEO POST-RENOMBRADO ---
    required_cols_num = ['Unico', 'NSE', 'gender', 'AGErange', 'Region']
    required_cols_txt = ['[auth]', 'NSE', 'NSE2', '[age]', 'Region 1 (Centro/Metro/Oeste)', 'CIUDAD']
    required_cols_txt.append("Por favor, selecciona el rango de edad en el que te encuentras:")
    
    if pais_clave_interna != 'Colombia Minors': required_cols_num.append('Ponderador')
    if pais_clave_interna == 'Perú': required_cols_txt.append('Region2')

    missing_std_cols_num = [col for col in required_cols_num if col not in df_numerico_renamed.columns]
    missing_std_cols_txt = [col for col in required_cols_txt if col not in df_textual_renamed.columns]

    if missing_std_cols_num or missing_std_cols_txt:
        if missing_std_cols_num: st.error(f"Faltan cols en numérica: {', '.join(missing_std_cols_num)}")
        if missing_std_cols_txt: st.error(f"Faltan cols en textual: {', '.join(missing_std_cols_txt)}")
        st.stop()

    # --- Optimización de Carga (Actualizado con Parte 3) ---
    num_ex = list(dict.fromkeys([c for c in ['Unico', 'lastpage', 'lastpage_Parte2', 'lastpage_Parte3', 'Ponderador', 'NSE', 'gender', 'AGErange', 'Region'] if c in df_numerico_renamed.columns]))
    txt_ex = list(dict.fromkeys([c for c in ['[auth]', 'startdate', "Por favor, selecciona el rango de edad en el que te encuentras:", '[age]', 'NSE', 'NSE2', 'Region 1 (Centro/Metro/Oeste)', 'CIUDAD', 'Region2', '[panelistid]'] if c in df_textual_renamed.columns]))
    df_numerico = df_numerico_renamed[num_ex].copy()
    df_textual = df_textual_renamed[txt_ex].copy()

    # V1: Tamaño
    key_v1 = "Tamaño de las Bases"; content_v1 = ""; status_v1 = "Correcto"
    fn, cn = df_numerico_full.shape; ft, ct = df_textual_full.shape
    content_v1 += f"- Num: {fn} filas x {cn} columnas<br>- Txt: {ft} filas x {ct} columnas<br><br><b>Comparación:</b><br>"
    if fn == ft and cn == ct: content_v1 += "<span class='status-correcto-inline'>[Correcto]</span> Coinciden."
    else: status_v1 = "Incorrecto"; content_v1 += "<span class='status-incorrecto-inline'>[Incorrecto]</span> Diferentes.<br>"
    validation_results.append({'key': key_v1, 'status': status_v1, 'content': content_v1})

    # V2: Orden IDs
    key_v2 = "Orden de Códigos Únicos"; content_v2 = ""; status_v2 = "Correcto"; col_num = 'Unico'; col_txt = '[auth]'
    cod_num = df_numerico[col_num]; cod_txt = df_textual[col_txt]
    if cod_num.equals(cod_txt): content_v2 += f"<span class='status-correcto-inline'>[Correcto]</span> Orden idéntico."
    else:
        status_v2 = "Incorrecto"; content_v2 += f"<span class='status-incorrecto-inline'>[Incorrecto]</span> Diferencias.<br>"
        diff_indices = cod_num.index[cod_num != cod_txt]
        rep = pd.DataFrame({'Fila': diff_indices + 2, 'Num': cod_num.loc[diff_indices].values, 'Txt': cod_txt.loc[diff_indices].values})
        content_v2 += rep.head().to_html(classes='df-style', index=False)
    validation_results.append({'key': key_v2, 'status': status_v2, 'content': content_v2})

    # V3: lastpage (Actualizado con lastpage_Parte3)
    key_v3 = "lastpage, lastpage_Parte2 y lastpage_Parte3"; content_v3 = ""; status_v3 = "Correcto"
    for col in ['lastpage', 'lastpage_Parte2', 'lastpage_Parte3']:
        if col in df_numerico.columns:
            vals = df_numerico[col].dropna().unique()
            if len(vals) > 1:
                status_v3 = "Incorrecto"
                content_v3 += f"<span class='status-incorrecto-inline'>[Incorrecto]</span> '{col}' tiene múltiples valores: {vals}<br>"
            elif len(vals) == 1:
                content_v3 += f"'{col}': OK (Valor único: {vals[0]})<br>"
            else:
                content_v3 += f"'{col}': OK (Columna vacía)<br>"
    validation_results.append({'key': key_v3, 'status': status_v3, 'content': content_v3})

    # V4: Periodo
    key_v4 = "Periodo Campo ('startdate')"; content_v4 = ""; status_v4 = "Info"
    try:
        fechas = pd.to_datetime(df_textual['startdate'], errors='coerce').dropna()
        if not fechas.empty:
            content_v4 += f"Inicio: {fechas.min().strftime('%d/%m/%Y %H:%M')}<br>Fin: {fechas.max().strftime('%d/%m/%Y %H:%M')}"
        else: content_v4 = "No hay fechas válidas."
    except: status_v4 = "Error"; content_v4 = "Error procesando fechas."
    validation_results.append({'key': key_v4, 'status': status_v4, 'content': content_v4})

    # V5: Agrupaciones
    key_v5 = "Agrupaciones"; content_v5 = ""; status_v5 = "Correcto"
    content_v5 += "<h3>5.1: Edad vs [age]</h3>"
    try:
        col_r_edad = "Por favor, selecciona el rango de edad en el que te encuentras:"
        rep_edad = df_textual.groupby(col_r_edad)['[age]'].agg(['count', 'min', 'max']).reset_index()
        content_v5 += rep_edad.to_html(classes='df-style', index=False)
    except: content_v5 += "Error en validación de edad.<br>"

    content_v5 += "<hr><h3>5.2: NSE vs NSE2</h3>"
    try:
        rep_nse = pd.crosstab(df_textual['NSE'].fillna('NULO'), df_textual['NSE2'].fillna('NULO'))
        content_v5 += rep_nse.to_html(classes='df-style')
    except: content_v5 += "Error en validación de NSE.<br>"

    # V5.3: Geografía (Lógica completa e ilimitada + Detección Ciudad Desconocida)
    content_v5 += f"<h3>5.3: Geografía ({pais_seleccionado_display} - Region 1 vs Ciudad/Dpto)</h3>"
    col_reg = 'Region 1 (Centro/Metro/Oeste)'; col_ciu = 'CIUDAD'
    clasif = CLASIFICACIONES_POR_PAIS.get(pais_clave_interna)
    if clasif:
        err_reg = []
        clasif_lower_keys = {k.lower(): k for k in clasif.keys()}
        clasif_lower_values = {k_lower: {v.lower().strip() for v in clasif[k_orig]} for k_lower, k_orig in clasif_lower_keys.items()}
        todas_ciudades_validas = {ciu.lower().strip() for lista in clasif.values() for ciu in lista}

        for idx, row in df_textual.iterrows():
            reg_val, ciu_val = row[col_reg], row[col_ciu]
            if pd.isna(reg_val) or pd.isna(ciu_val): continue
            reg_str_lower = str(reg_val).strip().lower()
            ciu_str_lower = str(ciu_val).strip().lower()

            if ciu_str_lower not in todas_ciudades_validas:
                err_reg.append({'Fila': idx + 2, 'Region': reg_val, 'Ciudad': ciu_val, 'Error': f"Ciudad no reconocida en el diccionario de {pais_clave_interna}"})
            elif reg_str_lower in clasif_lower_keys:
                if ciu_str_lower not in clasif_lower_values[reg_str_lower]:
                    err_reg.append({'Fila': idx + 2, 'Region': reg_val, 'Ciudad': ciu_val, 'Error': f"Ciudad no pertenece a la región '{clasif_lower_keys[reg_str_lower]}'"})
            else: err_reg.append({'Fila': idx + 2, 'Region': reg_val, 'Ciudad': ciu_val, 'Error': 'Región inválida'})

        if not err_reg: content_v5 += "<span class='status-correcto-inline'>[Correcto]</span> Consistente."
        else:
            status_v5 = "Incorrecto"
            df_err = pd.DataFrame(err_reg)
            content_v5 += f"<span class='status-incorrecto-inline'>[Incorrecto]</span> {len(err_reg)} inconsistencias detectadas:<br>" + df_err.to_html(classes='df-style', index=False)
    validation_results.append({'key': key_v5, 'status': status_v5, 'content': content_v5})

    # V6: Proveedor
    key_v6 = "Origen/Proveedor"; content_v6 = ""; status_v6 = "Info"
    p_col = next((c for c in ['Origen', 'Proveedor'] if c in df_textual.columns), None)
    if p_col:
        cnt = df_textual[p_col].value_counts().reset_index()
        content_v6 += cnt.to_html(classes='df-style', index=False)
    else: content_v6 = "Columna no encontrada."
    validation_results.append({'key': key_v6, 'status': status_v6, 'content': content_v6})

    # V7: Nulos
    key_v7 = "Nulos Base Numérica"; content_v7 = ""; status_v7 = "Correcto"
    for c in ['NSE', 'gender', 'AGErange', 'Region']:
        nulls = df_numerico[c].isnull().sum()
        if nulls > 0:
            status_v7 = "Incorrecto"; content_v7 += f"{c}: {nulls} nulos.<br>"
    if status_v7 == "Correcto": content_v7 = "No se encontraron nulos demográficos."
    validation_results.append({'key': key_v7, 'status': status_v7, 'content': content_v7})

    # V8: Abiertas
    key_v8 = "Abiertas ('Menciona')"; content_v8 = ""; status_v8 = "Info"
    cols_m = [c for c in df_textual_full.columns if "menciona" in str(c).lower() and "mencionaste" not in str(c).lower()]
    if cols_m:
        melted = df_textual_full[['[auth]'] + cols_m].melt(id_vars=['[auth]'], var_name='Pregunta', value_name='Respuesta').dropna()
        melted = melted[melted['Respuesta'].astype(str).str.strip() != '']
        if not melted.empty:
            df_para_descarga_abiertas = melted.copy()
            df_para_descarga_abiertas.columns = ['ID', 'Pregunta', 'Respuesta']
            content_v8 = f"Detectadas {len(melted)} respuestas abiertas.<br>" + melted.head(10).to_html(classes='df-style', index=False)
    else: content_v8 = "No se encontraron columnas con menciones."
    validation_results.append({'key': key_v8, 'status': status_v8, 'content': content_v8})

    # V9: Ponderador
    key_v9 = "Ponderador vs Total Filas"; content_v9 = ""; status_v9 = "Correcto"
    if 'Ponderador' in df_numerico.columns:
        suma = pd.to_numeric(df_numerico['Ponderador'], errors='coerce').sum()
        total = len(df_numerico)
        if not np.isclose(suma, total, atol=1e-5):
            status_v9 = "Incorrecto"; content_v9 = f"Suma: {suma:.2f}, Total Filas: {total}"
        else: content_v9 = f"Coinciden (Suma: {suma:,.0f})."
    else: content_v9 = "No aplica."
    validation_results.append({'key': key_v9, 'status': status_v9, 'content': content_v9})

    # V14: Conteo Demos
    key_v14 = "Conteo de Demográficos"; content_v14 = ""; status_v14 = "Info"
    for col in ['gender', 'AGErange', 'NSE', 'Region']:
        if col in df_numerico_renamed.columns:
            counts = df_numerico_renamed[col].fillna('VACÍO').value_counts().reset_index()
            counts.columns = ['Categoría', 'Total']
            total = counts['Total'].sum()
            counts['Porcentaje'] = (counts['Total'] / total * 100).apply(lambda x: f"{x:.1f}%")
            content_v14 += f"<b>{col}:</b>" + counts.to_html(classes='df-style', index=False) + "<br>"
    validation_results.append({'key': key_v14, 'status': status_v14, 'content': content_v14})

    # --- RENDERIZADO FINAL ---
    st.success("Proceso de validación terminado.")
    
    if not df_para_descarga_abiertas.empty:
        st.markdown("### 🔽 Descargar Reporte de Abiertas")
        st.download_button(label="Descargar Listado de Abiertas (.xlsx)", data=to_excel(df_para_descarga_abiertas), file_name=f'abiertas_{pais_seleccionado_display}.xlsx')

    sort_order = {'Correcto': 1, 'Incorrecto': 2, 'Error': 3, 'Info': 4}
    sorted_results = sorted(validation_results, key=lambda v: sort_order.get(v['status'], 5))

    st.subheader("--- RESUMEN DE VALIDACIÓN ---", divider='violet')
    c_res = st.columns(4)
    c_res[0].metric("✅ Correctos", sum(1 for v in sorted_results if v['status'] == 'Correcto'))
    c_res[1].metric("❌ Incorrectos", sum(1 for v in sorted_results if v['status'] == 'Incorrecto'))
    c_res[2].metric("⚠️ Errores", sum(1 for v in sorted_results if v['status'] == 'Error'))
    c_res[3].metric("ℹ️ Reportes", sum(1 for v in sorted_results if v['status'] == 'Info'))

    st.subheader("--- REPORTE DETALLADO ---", divider='violet')
    for v in sorted_results:
        st.markdown(f"""<div class="validation-box status-{v['status'].lower()}"><h3>{v['key']}</h3>{v['content']}</div>""", unsafe_allow_html=True)

elif not uploaded_file_num or not uploaded_file_txt:
    st.info("Esperando la carga de los archivos Excel...")