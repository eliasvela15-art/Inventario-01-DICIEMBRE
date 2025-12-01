import streamlit as st
import pandas as pd
from fpdf import FPDF
import base64
from datetime import datetime
import os
import glob

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

# --- FUNCIÓN INTELIGENTE PARA CARGAR DATOS ---
@st.cache_data
def load_data():
    # Buscamos cualquier archivo que termine en .csv en la carpeta actual
    csv_files = glob.glob("*.csv")
    
    if not csv_files:
        return None
    
    # Tomamos el primer archivo que encuentre (así no importa el nombre exacto)
    file_path = csv_files[0]
    
    try:
        df = pd.read_csv(file_path, encoding='latin-1')
    except:
        df = pd.read_csv(file_path, encoding='utf-8')
    
    # --- LIMPIEZA DE DATOS ---
    if 'Cobro (USD)' in df.columns:
        df['Cobro (USD_clean)'] = df['Cobro (USD)'].astype(str).str.replace('$', '', regex=False)
        # Reemplazar comas europeas/latinas por puntos si es necesario
        df['Cobro (USD_clean)'] = df['Cobro (USD_clean)'].str.replace('.', '', regex=False) # Quita separador de miles
        df['Cobro (USD_clean)'] = df['Cobro (USD_clean)'].str.replace(',', '.', regex=False) # Cambia coma decimal
        df['Cobro (USD_clean)'] = pd.to_numeric(df['Cobro (USD_clean)'], errors='coerce').fillna(0)
    
    if 'Días en bodega' in df.columns:
        df['Días en bodega'] = pd.to_numeric(df['Días en bodega'], errors='coerce').fillna(0)

    return df

# --- FUNCIÓN GENERAR PDF ---
def create_pdf(df_filtered, client_name, total_debt):
    class PDF(FPDF):
        def header(self):
            # Busca logo automáticamente
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
    pdf.set_fill_color(200, 220, 255)
    pdf.cell(0, 10, f"Cliente: {client_name}", ln=True, align='L')
    pdf.cell(0, 10, f"Fecha de reporte: {datetime.now().strftime('%d-%m-%Y')}", ln=True, align='L')
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, f"Adeudo Total Estimado: ${total_debt:,.2f} USD", ln=True, align='L')
    pdf.ln(5)
    
    # Tabla
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(40, 10, "Entrada", 1)
    pdf.cell(80, 10, "Descripción", 1)
    pdf.cell(30, 10, "Días", 1)
    pdf.cell(30, 10, "Cobro", 1)
    pdf.ln()
    
    pdf.set_font("Arial", size=9)
    for index, row in df_filtered.iterrows():
        desc = str(row.get('Descripción', ''))[:35]
        entrada = str(row.get('Entrada de bodega', ''))
        dias = str(int(row.get('Días en bodega', 0)))
        cobro = f"${row.get('Cobro (USD_clean)', 0):.2f}"
        pdf.cell(40, 10, entrada, 1)
        pdf.cell(80, 10, desc, 1)
        pdf.cell(30, 10, dias, 1)
        pdf.cell(30, 10, cobro, 1)
        pdf.ln()

    return pdf.output(dest='S').encode('latin-1')

# --- MAIN APP ---
def main():
    # Sidebar
    with st.sidebar:
        # Busca cualquier imagen png para el logo chico
        logos_chicos = glob.glob("*chico*.png") + glob.glob("*.png")
        if logos_chicos:
            st.image(logos_chicos[0], width=200)
        else:
            st.header("AFS LOGISTICS")
        
        st.header("Filtros de Control")
        
    # Cargar Datos
    df = load_data()
    
    if df is None:
        st.error("🚨 ERROR CRÍTICO: No se encontró ningún archivo CSV en el repositorio.")
        st.info("Por favor sube tu archivo de Excel guardado como CSV a GitHub.")
        return

    # Filtros
    if 'Cliente' in df.columns:
        clientes_unicos = sorted(df['Cliente'].dropna().unique().tolist())
        container = st.sidebar.container()
        all_selected = st.sidebar.checkbox("Seleccionar Todos los Clientes", value=True)
        if all_selected:
            selected_clients = container.multiselect("Seleccione Cliente(s):", clientes_unicos, default=clientes_unicos)
        else:
            selected_clients = container.multiselect("Seleccione Cliente(s):", clientes_unicos)
            
        if not selected_clients:
            df_filtered = pd.DataFrame()
        else:
            df_filtered = df[df['Cliente'].isin(selected_clients)]
    else:
        st.error("El archivo CSV no tiene una columna llamada 'Cliente'. Verifica el formato.")
        return

    # --- CUERPO PRINCIPAL ---
    col_logo, col_title = st.columns([1, 5])
    with col_logo:
        # Busca logo grande
        logos_grandes = glob.glob("*plata*.png")
        if logos_grandes: st.image(logos_grandes[0], width=80)
            
    with col_title:
        st.markdown('<p class="main-header">Control de Inventarios & Adeudos</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="sub-header">Fecha de corte: {datetime.now().strftime("%d-%m-%Y")}</p>', unsafe_allow_html=True)

    st.markdown("---")

    if not df_filtered.empty:
        # CÁLCULOS KPI
        total_debt = df_filtered['Cobro (USD_clean)'].sum()
        max_days = df_filtered['Días en bodega'].max()
        total_items = len(df_filtered)

        # 1. ALERTAS
        if max_days > 80:
            st.markdown(f"""
            <div class="alert-box">
                ⚠️ <strong>ALERTA DE ALMACENAJE PROLONGADO</strong><br>
                Se han detectado entradas con más de 80 días ({int(max_days)} días) en bodega.
            </div>
            """, unsafe_allow_html=True)

        # 2. TARJETAS DE MÉTRICAS
        k1, k2, k3 = st.columns(3)
        k1.metric("Adeudo Total (USD)", f"${total_debt:,.2f}")
        k2.metric("Total Partidas", total_items)
        k3.metric("Antigüedad Máxima", f"{int(max_days)} días")

        # 3. TABLA
        st.subheader("Detalle de Inventario")
        
        cols_possible = ['Entrada de bodega', 'Cliente', 'Descripción', 'Días en bodega', 'Días Cobrados', 'Concepto', 'Cobro (USD)']
        cols_final = [c for c in cols_possible if c in df_filtered.columns]
        
        def highlight_aging(row):
            if row['Días en bodega'] > 80:
                return ['background-color: #ffcccc; color: black'] * len(row)
            else:
                return [''] * len(row)

        st.dataframe(df_filtered[cols_final].style.apply(highlight_aging, axis=1), use_container_width=True, height=400)

        # 4. EXPORTAR
        st.markdown("---")
        if st.button("Generar PDF Formal"):
            client_label = selected_clients[0] if len(selected_clients) == 1 else "Varios"
            pdf_bytes = create_pdf(df_filtered, client_label, total_debt)
            st.download_button("📥 Descargar PDF", pdf_bytes, f"Reporte_{client_label}.pdf", 'application/pdf')

if __name__ == "__main__":
    main()
