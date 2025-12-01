import streamlit as st
import pandas as pd
from fpdf import FPDF
import glob
from datetime import datetime
import unidecode  # Necesario para quitar acentos al comparar nombres si fuera necesario, pero usaremos lógica nativa

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Dashboard Inventarios AFS",
    page_icon="📦",
    layout="wide"
)

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #f5f5f5; }
    div.stButton > button:first-child {
        background-color: #D32F2F;
        color: white;
        border-radius: 5px;
        border: none;
    }
    div.stButton > button:hover { background-color: #b71c1c; color: white; }
    [data-testid="stMetricValue"] { font-size: 2rem; color: #D32F2F; font-weight: bold; }
    .main-header { font-size: 2.5rem; color: #333; font-weight: 700; margin-bottom: 0; }
    .sub-header { font-size: 1.2rem; color: #666; margin-bottom: 2rem; }
    .alert-box {
        padding: 15px; background-color: #ffebee; color: #c62828;
        border-left: 5px solid #c62828; border-radius: 4px; margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# --- FUNCIÓN DE LIMPIEZA DE COLUMNAS ---
def normalize_columns(df):
    """
    Esta función arregla los nombres de las columnas para evitar errores por acentos o espacios.
    """
    # 1. Quitar espacios al principio y final
    df.columns = df.columns.str.strip()
    
    # 2. Mapa de renombrado inteligente (busca variantes comunes)
    rename_map = {}
    for col in df.columns:
        col_lower = col.lower()
        # Detectar 'Dias en bodega' con o sin acento
        if "dias en bodega" in col_lower or "días en bodega" in col_lower:
            rename_map[col] = "Días en bodega"
        # Detectar Cobro USD
        elif "cobro" in col_lower and "usd" in col_lower:
            rename_map[col] = "Cobro (USD)"
        # Detectar Entrada
        elif "entrada" in col_lower and "bodega" in col_lower:
            rename_map[col] = "Entrada de bodega"
        # Detectar Descripcion
        elif "descripci" in col_lower:
            rename_map[col] = "Descripción"
            
    if rename_map:
        df = df.rename(columns=rename_map)
    
    return df

# --- FUNCIÓN CARGAR DATOS ---
@st.cache_data
def load_data():
    # Buscar archivo CSV automáticamente
    csv_files = glob.glob("*.csv")
    if not csv_files:
        return None
    
    file_path = csv_files[0]
    
    # Intentar leer con diferentes codificaciones
    try:
        df = pd.read_csv(file_path, encoding='latin-1')
    except:
        try:
            df = pd.read_csv(file_path, encoding='utf-8')
        except:
            # Último intento: ignorar errores de caracteres
            df = pd.read_csv(file_path, encoding='latin-1', errors='replace')
    
    # APLICAR LIMPIEZA DE COLUMNAS
    df = normalize_columns(df)
    
    # --- LIMPIEZA DE VALORES ---
    # Limpiar Cobro (USD)
    if 'Cobro (USD)' in df.columns:
        # Convertir a string, quitar símbolos de moneda y espacios
        df['Cobro (USD_clean)'] = df['Cobro (USD)'].astype(str).str.replace('$', '', regex=False).str.strip()
        # Manejo de comas y puntos (Formato: 1.000,00 o 1,000.00)
        # Asumimos que si hay coma, es decimal si no hay puntos antes
        df['Cobro (USD_clean)'] = df['Cobro (USD_clean)'].str.replace(',', '.', regex=False)
        # Si quedan múltiples puntos, dejamos solo el último (complejo, simplificamos a coerción)
        df['Cobro (USD_clean)'] = pd.to_numeric(df['Cobro (USD_clean)'], errors='coerce').fillna(0)
    else:
        # Si no existe la columna, creamos una dummy de 0
        df['Cobro (USD_clean)'] = 0

    # Limpiar Días en bodega
    if 'Días en bodega' in df.columns:
        df['Días en bodega'] = pd.to_numeric(df['Días en bodega'], errors='coerce').fillna(0)
    else:
         df['Días en bodega'] = 0

    return df

# --- PDF ---
def create_pdf(df_filtered, client_name, total_debt):
    class PDF(FPDF):
        def header(self):
            logos = glob.glob("*plata*.png") + glob.glob("*.png")
            if logos:
                try: self.image(logos[0], 10, 8, 33)
                except: pass
            self.set_font('Arial', 'B', 15)
            self.cell(80)
            self.cell(30, 10, 'Reporte de Estado de Inventario', 0, 0, 'C')
            self.ln(20)
        def footer(self):
            self.set_y(-15)
            self.set_font('Arial', 'I', 8)
            self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, f"Cliente: {client_name}", ln=True)
    pdf.cell(0, 10, f"Fecha: {datetime.now().strftime('%d-%m-%Y')}", ln=True)
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, f"Adeudo Total: ${total_debt:,.2f} USD", ln=True)
    pdf.ln(5)
    
    # Tabla simple PDF
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(35, 10, "Entrada", 1)
    pdf.cell(85, 10, "Descripción", 1)
    pdf.cell(30, 10, "Días", 1)
    pdf.cell(30, 10, "Cobro", 1)
    pdf.ln()
    
    pdf.set_font("Arial", size=8)
    for _, row in df_filtered.iterrows():
        desc = str(row.get('Descripción', 'N/A'))[:45]
        ent = str(row.get('Entrada de bodega', ''))
        dias = str(int(row.get('Días en bodega', 0)))
        cobro = f"${row.get('Cobro (USD_clean)', 0):.2f}"
        
        pdf.cell(35, 10, ent, 1)
        pdf.cell(85, 10, desc, 1)
        pdf.cell(30, 10, dias, 1)
        pdf.cell(30, 10, cobro, 1)
        pdf.ln()
    return pdf.output(dest='S').encode('latin-1', 'ignore')

# --- MAIN ---
def main():
    # Sidebar
    with st.sidebar:
        logos_chicos = glob.glob("*chico*.png") + glob.glob("*.png")
        if logos_chicos: st.image(logos_chicos[0], width=200)
        else: st.header("AFS LOGISTICS")
        st.header("Filtros")

    # Cargar y Validar
    df = load_data()
    if df is None:
        st.error("No se encontró archivo CSV.")
        return

    # Verificar columna Cliente
    if 'Cliente' not in df.columns:
        st.error("Error: No se detectó la columna 'Cliente'. Las columnas detectadas son:")
        st.write(df.columns.tolist())
        return

    # Filtros
    clientes = sorted(df['Cliente'].dropna().unique().tolist())
    container = st.sidebar.container()
    if st.sidebar.checkbox("Seleccionar Todos", value=True):
        sel_clients = container.multiselect("Cliente(s):", clientes, default=clientes)
    else:
        sel_clients = container.multiselect("Cliente(s):", clientes)

    if not sel_clients:
        df_filtered = pd.DataFrame()
    else:
        df_filtered = df[df['Cliente'].isin(sel_clients)]

    # Layout Principal
    c1, c2 = st.columns([1, 5])
    with c1:
        lg = glob.glob("*plata*.png")
        if lg: st.image(lg[0], width=80)
    with c2:
        st.title("Control de Inventarios")
        st.write(f"Fecha: {datetime.now().strftime('%d-%m-%Y')}")
    st.markdown("---")

    if not df_filtered.empty:
        # KPI Cálculos seguros
        total_debt = df_filtered['Cobro (USD_clean)'].sum()
        
        # Validación de columna 'Días en bodega' para cálculos
        if 'Días en bodega' in df_filtered.columns:
            max_days = df_filtered['Días en bodega'].max()
        else:
            max_days = 0
            st.warning("⚠️ No se pudo leer la columna de días para calcular antigüedades.")

        # Alerta
        if max_days > 80:
            st.markdown(f'<div class="alert-box">⚠️ ALERTA: Mercancía con {int(max_days)} días en bodega.</div>', unsafe_allow_html=True)

        # Métricas
        c1, c2, c3 = st.columns(3)
        c1.metric("Adeudo Total", f"${total_debt:,.2f}")
        c2.metric("Partidas", len(df_filtered))
        c3.metric("Antigüedad Máx", f"{int(max_days)} días")

        # Tabla
        st.subheader("Detalle")
        cols_show = ['Entrada de bodega', 'Cliente', 'Descripción', 'Días en bodega', 'Cobro (USD)']
        cols_final = [c for c in cols_show if c in df_filtered.columns]
        
        def highlight(row):
            # Solo colorear si existe la columna y cumple condición
            val = row.get('Días en bodega', 0)
            if val > 80: return ['background-color: #ffcccc; color: black'] * len(row)
            return [''] * len(row)

        st.dataframe(df_filtered[cols_final].style.apply(highlight, axis=1), use_container_width=True)

        # PDF
        st.markdown("---")
        if st.button("Descargar PDF"):
            nom = sel_clients[0] if len(sel_clients)==1 else "Reporte"
            b = create_pdf(df_filtered, nom, total_debt)
            st.download_button("📥 PDF", b, "reporte.pdf", "application/pdf")

if __name__ == "__main__":
    main()
