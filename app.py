import streamlit as st
import pandas as pd
from fpdf import FPDF
import base64
from datetime import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Dashboard Inventarios AFS",
    page_icon="📦",
    layout="wide"
)

# --- ESTILOS CSS PERSONALIZADOS (LOOK & FEEL AFS) ---
st.markdown("""
    <style>
    /* Colores principales: Rojo AFS (#D32F2F), Gris Oscuro, Blanco */
    .stApp {
        background-color: #f5f5f5;
    }
    div.stButton > button:first-child {
        background-color: #D32F2F;
        color: white;
        border-radius: 5px;
        border: none;
    }
    div.stButton > button:hover {
        background-color: #b71c1c;
        color: white;
    }
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        color: #D32F2F;
        font-weight: bold;
    }
    .main-header {
        font-size: 2.5rem;
        color: #333;
        font-weight: 700;
        margin-bottom: 0;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    /* Estilo para alertas personalizadas */
    .alert-box {
        padding: 15px;
        background-color: #ffebee;
        color: #c62828;
        border-left: 5px solid #c62828;
        border-radius: 4px;
        margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# --- FUNCIÓN PARA CARGAR DATOS ---
@st.cache_data
def load_data():
    # Nombre exacto de tu archivo. Asegúrate de que esté en la misma carpeta.
    file_path = "01 Diciembre 2025 - Inventario 01-12-2025.csv"
    
    try:
        # Intentamos leer con diferentes encodings por si acaso
        df = pd.read_csv(file_path, encoding='latin-1')
    except:
        df = pd.read_csv(file_path, encoding='utf-8')
    
    # --- LIMPIEZA DE DATOS ---
    
    # 1. Limpiar columna de Cobro (USD)
    # El formato parece ser "$0,00" (coma decimal) o "$1.200,50"
    if 'Cobro (USD)' in df.columns:
        # Eliminamos el signo $
        df['Cobro (USD_clean)'] = df['Cobro (USD)'].astype(str).str.replace('$', '', regex=False)
        # Eliminamos puntos de miles (si existen) y cambiamos coma decimal por punto
        # Asumiendo formato 1.000,00 -> remove '.' then replace ',' with '.'
        # Si el formato es simple (100,00), solo reemplazamos coma.
        df['Cobro (USD_clean)'] = df['Cobro (USD_clean)'].str.replace(',', '.', regex=False)
        df['Cobro (USD_clean)'] = pd.to_numeric(df['Cobro (USD_clean)'], errors='coerce').fillna(0)
    
    # 2. Asegurar que Días en bodega sea numérico
    if 'Días en bodega' in df.columns:
        df['Días en bodega'] = pd.to_numeric(df['Días en bodega'], errors='coerce').fillna(0)

    # 3. Formatear fechas si es necesario (opcional)
    
    return df

# --- FUNCIÓN GENERAR PDF ---
def create_pdf(df_filtered, client_name, total_debt):
    class PDF(FPDF):
        def header(self):
            # Intentar poner logo si existe
            try:
                # Ajusta las coordenadas y tamaño según tu logo
                self.image('cropped-Logo-plata-AFS-2021-768x702.png', 10, 8, 33)
            except:
                pass
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
    
    # Información del Cliente
    pdf.set_fill_color(200, 220, 255)
    pdf.cell(0, 10, f"Cliente: {client_name}", ln=True, align='L')
    pdf.cell(0, 10, f"Fecha de reporte: {datetime.now().strftime('%d-%m-%Y')}", ln=True, align='L')
    pdf.ln(10)
    
    # Resumen Financiero
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, f"Adeudo Total Estimado: ${total_debt:,.2f} USD", ln=True, align='L')
    pdf.ln(5)
    
    # Tabla de Items (Simplificada para PDF)
    pdf.set_font("Arial", 'B', 10)
    # Encabezados
    pdf.cell(40, 10, "Entrada", 1)
    pdf.cell(80, 10, "Descripción / Mercancía", 1)
    pdf.cell(30, 10, "Días Bodega", 1)
    pdf.cell(30, 10, "Cobro", 1)
    pdf.ln()
    
    # Filas
    pdf.set_font("Arial", size=9)
    for index, row in df_filtered.iterrows():
        # Truncar textos largos
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
    # Sidebar con Logo
    with st.sidebar:
        try:
            st.image("cropped-logo-chico-1.png", width=200)
        except:
            st.write("AFS LOGISTICS") # Fallback si no carga imagen
        
        st.header("Filtros de Control")
        
    # Cargar Datos
    try:
        df = load_data()
    except FileNotFoundError:
        st.error("Error: No se encuentra el archivo CSV. Asegúrate de subir '01 Diciembre 2025 - Inventario 01-12-2025.csv' al repositorio.")
        return

    # Filtros
    clientes_unicos = sorted(df['Cliente'].dropna().unique().tolist())
    
    # Opción "Seleccionar Todos" en el multiselect
    container = st.sidebar.container()
    all_selected = st.sidebar.checkbox("Seleccionar Todos los Clientes", value=True)
    
    if all_selected:
        selected_clients = container.multiselect("Seleccione Cliente(s):", clientes_unicos, default=clientes_unicos)
    else:
        selected_clients = container.multiselect("Seleccione Cliente(s):", clientes_unicos)

    # Filtrar DataFrame
    if not selected_clients:
        st.info("Por favor seleccione al menos un cliente en el panel izquierdo.")
        df_filtered = pd.DataFrame()
    else:
        df_filtered = df[df['Cliente'].isin(selected_clients)]

    # --- CUERPO PRINCIPAL ---
    col_logo, col_title = st.columns([1, 5])
    with col_logo:
        try:
            st.image("cropped-Logo-plata-AFS-2021-768x702.png", width=80)
        except:
            pass
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
                Se han detectado entradas con más de 80 días en bodega para los clientes seleccionados.
                Por favor revise las partidas marcadas en la tabla.
            </div>
            """, unsafe_allow_html=True)

        # 2. TARJETAS DE MÉTRICAS
        kpi1, kpi2, kpi3 = st.columns(3)
        with kpi1:
            st.metric("Adeudo Total Estimado (USD)", f"${total_debt:,.2f}")
        with kpi2:
            st.metric("Total Partidas", total_items)
        with kpi3:
            st.metric("Antigüedad Máxima (Días)", int(max_days))

        # 3. TABLA DE DATOS
        st.subheader("Detalle de Inventario")
        
        # Columnas a mostrar (según tu petición + relevantes)
        cols_to_show = [
            'Entrada de bodega', 
            'Cliente', 
            'Descripción', 
            'Días en bodega', 
            'Días Cobrados', 
            'Concepto',  # Asumiendo que esta dice si aplica cobro
            'Cobro (USD)'
        ]
        
        # Verificar que existan las columnas antes de mostrarlas
        valid_cols = [c for c in cols_to_show if c in df_filtered.columns]
        
        # Highlight de filas > 80 días
        def highlight_aging(row):
            if row['Días en bodega'] > 80:
                return ['background-color: #ffcccc; color: black'] * len(row)
            else:
                return [''] * len(row)

        st.dataframe(
            df_filtered[valid_cols].style.apply(highlight_aging, axis=1),
            use_container_width=True,
            height=400
        )

        # 4. EXPORTAR A PDF
        st.markdown("---")
        st.subheader("Exportar Informe")
        
        export_col1, export_col2 = st.columns([1, 4])
        with export_col1:
            if st.button("Generar PDF Formal"):
                # Nombre del cliente para el archivo (si son varios pone 'Varios')
                client_label = selected_clients[0] if len(selected_clients) == 1 else "Varios_Clientes"
                
                pdf_bytes = create_pdf(df_filtered, ", ".join(selected_clients[:3]), total_debt)
                
                st.download_button(
                    label="📥 Descargar PDF",
                    data=pdf_bytes,
                    file_name=f"Reporte_Inventario_{client_label}.pdf",
                    mime='application/pdf'
                )

if __name__ == "__main__":
    main()