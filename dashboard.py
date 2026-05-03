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

# --- CSS PARA IMPRESSÃO E AJUSTE DE TEMA ---
st.markdown("""
    <style>
    @media print {
        /* Esconde elementos de interface */
        [data-testid="stSidebar"], .stFileUploader, button, header, [data-testid="stDecoration"] {
            display: none !important;
        }
        /* Força quebra de página */
        .page-break {
            page-break-before: always !important;
            display: block;
        }
        /* Container para 4 gráficos por página (2x2) */
        .print-grid {
            display: grid !important;
            grid-template-columns: 1fr 1fr !important;
            gap: 10px !important;
        }
        /* Evita que o expander ou container corte no meio */
        .stExpander, .stContainer {
            page-break-inside: avoid !important;
        }
    }
    /* Ajuste de métricas */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
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
            st.error("Arquivo sem colunas obrigatórias.")
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

    fig.add_trace(go.Scatter(x=df_produtos["Produto"], y=df_produtos[col_valor_real], name="Vol. real", yaxis="y2", mode="lines+markers", line=dict(dash="dot", color="#888")))
    fig.add_hline(y=100, line_dash="solid", line_color="gray", line_width=2)
    fig.update_layout(
        title=titulo, height=350, barmode="group",
        yaxis=dict(title="Índice %", range=[0, 180], gridcolor="rgba(128,128,128,0.2)"),
        yaxis2=dict(title="Volume Real", overlaying="y", side="right", showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=50, b=10)
    )
    return fig, df_total

# --- INTERFACE ---
st.markdown("# :material/upload_file: Gestão de Projeções")
uploaded_file = st.file_uploader("Arraste o arquivo Excel aqui", type=["xlsx"])

if uploaded_file:
    df_raw = process_data(uploaded_file)
    
    if not df_raw.empty:
        with st.sidebar:
            st.title("⚙️ Filtros")
            todos_periodos = df_raw['Período'].unique().tolist()
            periodos_selecionados = st.multiselect("Filtrar Períodos:", options=todos_periodos, default=todos_periodos)

        if not periodos_selecionados: st.stop()
        df_filtered = df_raw[df_raw['Período'].isin(periodos_selecionados)]

        # --- PÁGINA 1: PANORAMA ---
        st.markdown("## :material/dashboard: Panorama Geral")
        cols_top = st.columns([1, 2])
        ultimo_p = periodos_selecionados[-1]
        df_pizza = df_raw[(df_raw['Período'] == ultimo_p) & (df_raw['Produto'].astype(str).str.upper() != "TOTAL")]

        with cols_top[0].container(border=True):
            st.markdown(f"### Mix de Volume ({ultimo_p})")
            fig_mix = px.pie(df_pizza, values=col_valor_real, names='Produto', hole=0.5, color_discrete_sequence=cores_vermelho_mix)
            fig_mix.update_layout(height=350, showlegend=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_mix, use_container_width=True)

        with cols_top[1].container(border=True):
            st.markdown("### Evolução por Produto")
            df_ev = df_filtered[df_filtered['Produto'].astype(str).str.upper() != "TOTAL"]
            chart_geral = alt.Chart(df_ev).mark_line(point=True).encode(
                x=alt.X('Período:N', sort=None), y='Soma de VolUC:Q', color='Produto:N'
            ).properties(height=300)
            st.altair_chart(chart_geral, use_container_width=True)

        st.markdown("### 🎯 Erro Médio de Projeção")
        ordem_produtos = df_ev.groupby('Produto')[col_valor_real].sum().sort_values(ascending=False).index.tolist()
        cols_detail = st.columns(4)

        for i, produto in enumerate(ordem_produtos):
            df_p_sum = df_filtered[df_filtered['Produto'] == produto][semanas + [col_valor_real]].sum()
            erro_medio = (((df_p_sum[semanas].sum()/4) / df_p_sum[col_valor_real]) - 1) * 100 if df_p_sum[col_valor_real] != 0 else 0
            with cols_detail[i % 4].container(border=True):
                st.metric(label=produto, value=f"{erro_medio:.1f}%", 
                          delta=f"{((df_p_sum['S4']/df_p_sum[col_valor_real])-1)*100:.1f}% S4", delta_color="inverse")
                # Mini gráfico do card (original)
                df_card = pd.DataFrame([{'S': s, 'E': ((df_p_sum[s]/df_p_sum[col_valor_real])-1)*100} for s in semanas])
                c_err = alt.Chart(df_card).mark_bar().encode(x='S:N', y='E:Q', color=alt.value('#8B0000')).properties(height=100)
                st.altair_chart(c_err, use_container_width=True)

        # --- PÁGINA 2+: ESTUDO DE PRECISÃO (IMPRESSÃO EM GRID 2x2) ---
        st.markdown('<div class="page-break"></div>', unsafe_allow_html=True)
        st.markdown("## :material/analytics: Estudo de Precisão por Mês")

        # Processa os períodos em blocos de 4 para garantir a quebra de página correta no PDF
        for i in range(0, len(periodos_selecionados), 4):
            batch = periodos_selecionados[i:i+4]
            
            # Div que agrupa 4 gráficos na impressão
            st.markdown('<div class="print-grid">', unsafe_allow_html=True)
            
            for periodo in batch:
                with st.container():
                    st.subheader(f"📅 {periodo}")
                    df_mes = df_raw[df_raw["Período"] == periodo]
                    col_a, col_b = st.columns([2.5, 1.5])
                    
                    fig_prod, df_mes_total = grafico_projeções_plotly(df_mes, "")
                    col_a.plotly_chart(fig_prod, use_container_width=True)

                    if not df_mes_total.empty:
                        total_val = df_mes_total.iloc[0]
                        v_total = [(total_val[s]/total_val[col_valor_real]*100) if total_val[col_valor_real] != 0 else 0 for s in semanas]
                        fig_t = go.Figure(go.Bar(x=semanas, y=v_total, marker_color=lista_vermelhos))
                        fig_t.add_hline(y=100, line_dash="solid", line_color="gray")
                        fig_t.update_layout(title="Média Mês", yaxis=dict(range=[0, 150]), height=350, 
                                            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
                        col_b.plotly_chart(fig_t, use_container_width=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Se houver mais de 4 períodos, adiciona outra quebra de página após o bloco atual
            if i + 4 < len(periodos_selecionados):
                st.markdown('<div class="page-break"></div>', unsafe_allow_html=True)

else:
    st.info("Aguardando arquivo Excel.")
