import streamlit as st
import pandas as pd
import altair as alt
import plotly.graph_objects as go
import plotly.express as px

# 1. Configuração da Página
st.set_page_config(
    page_title="Dashboard Unificado - Projeções",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS AVANÇADO PARA IMPRESSÃO ---
st.markdown("""
    <style>
    /* Estilos Gerais */
    [data-testid="stMetricValue"] { font-size: 1.8rem !important; }

    @media print {
        /* Esconde elementos desnecessários */
        [data-testid="stSidebar"], .stFileUploader, button, header, [data-testid="stDecoration"] {
            display: none !important;
        }
        
        /* Força a quebra de página após a seção de panorama */
        .page-break-after {
            page-break-after: always !important;
            display: block;
        }

        /* Container para os gráficos mensais: 2 por linha, totalizando 4 por página */
        .monthly-grid {
            display: grid !important;
            grid-template-columns: 1fr 1fr !important;
            gap: 20px !important;
        }

        /* Garante que o conteúdo não seja cortado */
        .stPlotlyChart {
            page-break-inside: avoid !important;
        }
        
        /* Ajuste de margens da página impressa */
        @page {
            margin: 1cm;
        }
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONFIGURAÇÕES VISUAIS ---
cores_vermelho_mix = ["#710000", "#8B0000", "#B22222", "#D32F2F", "#E53935", "#EF5350", "#FF8A80"]
cores_vermelho_semanas = {"S1": "#8B0000", "S2": "#B22222", "S3": "#FF4D4D", "S4": "#FFCCCC"}
lista_vermelhos = ["#8B0000", "#B22222", "#FF4D4D", "#FFCCCC"]
semanas = ["S1", "S2", "S3", "S4"]
col_valor_real = "Soma de VolUC"

# --- FUNÇÕES DE APOIO ---
@st.cache_data
def process_data(file):
    try:
        df = pd.read_excel(file)
        cols_obrigatorias = ['Produto', 'Período', col_valor_real] + semanas
        if not all(c in df.columns for c in cols_obrigatorias):
            st.error("Colunas obrigatórias ausentes.")
            return pd.DataFrame()
        if 'Período' in df.columns:
            df['Data_Ref'] = pd.to_datetime(df['Período'], format='%m/%y', errors='coerce')
            df = df.sort_values('Data_Ref')
            df['Período'] = df['Período'].astype(str)
        return df
    except Exception as e:
        st.error(f"Erro: {e}")
        return pd.DataFrame()

def grafico_projeções_plotly(df, titulo):
    if df.empty: return go.Figure(), pd.DataFrame()
    df_produtos = df[df["Produto"].str.upper() != "TOTAL"].sort_values(col_valor_real, ascending=False)
    df_total = df[df["Produto"].str.upper() == "TOTAL"]
    
    fig = go.Figure()
    for s in semanas:
        if s in df_produtos.columns:
            y_vals = df_produtos.apply(lambda row: (row[s] / row[col_valor_real] * 100) if row[col_valor_real] != 0 else 0, axis=1)
            fig.add_bar(x=df_produtos["Produto"], y=y_vals, name=s, marker_color=cores_vermelho_semanas[s])

    fig.add_trace(go.Scatter(x=df_produtos["Produto"], y=df_produtos[col_valor_real], name="Vol. Real", yaxis="y2", mode="lines+markers", line=dict(dash="dot", color="#888")))
    fig.add_hline(y=100, line_dash="solid", line_color="gray", line_width=2)
    fig.update_layout(
        title=titulo, height=350, barmode="group",
        yaxis=dict(title="%", range=[0, 180], gridcolor="rgba(128,128,128,0.2)"),
        yaxis2=dict(overlaying="y", side="right", showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=50, b=10)
    )
    return fig, df_total

# --- INTERFACE ---
st.markdown("# :material/upload_file: Gestão de Projeções")
uploaded_file = st.file_uploader("Upload Excel", type=["xlsx"], label_visibility="collapsed")

if uploaded_file:
    df_raw = process_data(uploaded_file)
    
    if not df_raw.empty:
        with st.sidebar:
            st.title("⚙️ Filtros")
            todos_periodos = df_raw['Período'].unique().tolist()
            periodos_selecionados = st.multiselect("Períodos:", options=todos_periodos, default=todos_periodos)

        if not periodos_selecionados: st.stop()
        df_filtered = df_raw[df_raw['Período'].isin(periodos_selecionados)]

        # --- SEÇÃO 1: PANORAMA (PÁGINA 1 DO PDF) ---
        st.container()
        st.markdown("## :material/dashboard: Panorama Geral")
        c1, c2 = st.columns([1, 2])
        
        ultimo_p = periodos_selecionados[-1]
        df_pizza = df_raw[(df_raw['Período'] == ultimo_p) & (df_raw['Produto'].astype(str).str.upper() != "TOTAL")]

        with c1.container(border=True):
            fig_mix = px.pie(df_pizza, values=col_valor_real, names='Produto', hole=0.5, color_discrete_sequence=cores_vermelho_mix)
            fig_mix.update_layout(height=300, showlegend=False, paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_mix, use_container_width=True)

        with c2.container(border=True):
            df_ev = df_filtered[df_filtered['Produto'].astype(str).str.upper() != "TOTAL"]
            chart_ev = alt.Chart(df_ev).mark_line(point=True).encode(
                x='Período:N', y='Soma de VolUC:Q', color='Produto:N'
            ).properties(height=250)
            st.altair_chart(chart_ev, use_container_width=True)

        st.markdown("### 🎯 Erro Médio por Produto")
        ordem_produtos = df_ev.groupby('Produto')[col_valor_real].sum().sort_values(ascending=False).index.tolist()
        cols_cards = st.columns(4)

        for i, produto in enumerate(ordem_produtos):
            df_p = df_filtered[df_filtered['Produto'] == produto][semanas + [col_valor_real]].sum()
            erro_m = (((df_p[semanas].sum() / 4) / df_p[col_valor_real]) - 1) * 100 if df_p[col_valor_real] != 0 else 0
            with cols_cards[i % 4].container(border=True):
                st.metric(label=produto, value=f"{erro_m:.1f}%", delta=f"{( (df_p['S4']/df_p[col_valor_real])-1)*100:.1f}% S4", delta_color="inverse")

        # DIVISOR DE PÁGINA PARA IMPRESSÃO
        st.markdown('<div class="page-break-after"></div>', unsafe_allow_html=True)

        # --- SEÇÃO 2: ESTUDO MENSAL (PÁGINA 2+ DO PDF) ---
        st.markdown("## :material/analytics: Estudo de Precisão Mensal")
        
        # Lógica para agrupar de 4 em 4 para a grade de impressão
        for i in range(0, len(periodos_selecionados), 4):
            batch = periodos_selecionados[i:i+4]
            
            # Container que vira Grid no CSS de impressão
            st.markdown('<div class="monthly-grid">', unsafe_allow_html=True)
            
            # No Streamlit usamos colunas normais, o CSS arruma no PDF
            m_cols = st.columns(2)
            for idx, periodo in enumerate(batch):
                target_col = m_cols[idx % 2]
                with target_col.container(border=True):
                    st.caption(f"Período: {periodo}")
                    df_mes = df_raw[df_raw["Período"] == periodo]
                    fig_p, _ = grafico_projeções_plotly(df_mes, "")
                    st.plotly_chart(fig_p, use_container_width=True, config={'displayModeBar': False})
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Adiciona quebra de página a cada 4 gráficos
            if i + 4 < len(periodos_selecionados):
                st.markdown('<div class="page-break-after"></div>', unsafe_allow_html=True)

else:
    st.info("Aguardando upload do arquivo Excel.")
