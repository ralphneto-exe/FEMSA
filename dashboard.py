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

# --- CSS PARA IMPRESSÃO E ESTILO ---
st.markdown("""
    <style>
    @media print {
        [data-testid="stSidebar"], .stFileUploader, button, .stMetric {
            display: none !important;
        }
        .break-page {
            page-break-before: always;
        }
    }
    /* Ajuste para as métricas ficarem mais compactas */
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
        # Validação de Colunas
        cols_obrigatorias = ['Produto', 'Período', col_valor_real] + semanas
        missing = [c for c in cols_obrigatorias if c not in df.columns]
        if missing:
            st.error(f"O arquivo está sem as colunas obrigatórias: {', '.join(missing)}")
            return pd.DataFrame()

        if 'Período' in df.columns:
            df['Data_Ref'] = pd.to_datetime(df['Período'], format='%m/%y', errors='coerce')
            df = df.sort_values('Data_Ref')
            df['Período'] = df['Período'].astype(str)
        return df
    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {e}")
        return pd.DataFrame()

def grafico_projeções_plotly(df, titulo):
    if df.empty: return go.Figure(), pd.DataFrame()
    df_produtos = df[df["Produto"].str.upper() != "TOTAL"].sort_values(col_valor_real, ascending=False)
    df_total = df[df["Produto"].str.upper() == "TOTAL"]
    df_plot = df_produtos.copy()

    fig = go.Figure()
    for s in semanas:
        if s in df_plot.columns:
            y_vals = df_plot.apply(lambda row: (row[s] / row[col_valor_real] * 100) if row[col_valor_real] != 0 else 0, axis=1)
            fig.add_bar(
                x=df_plot["Produto"], y=y_vals, name=s,
                marker_color=cores_vermelho_semanas[s],
                customdata=df_produtos[col_valor_real],
                hovertemplate="<b>%{x}</b><br>"+s+": %{y:.1f}%<br>Vol. Real: %{customdata:,.0f}<extra></extra>"
            )

    fig.add_trace(go.Scatter(
        x=df_plot["Produto"], y=df_produtos[col_valor_real],
        name="Volume real", yaxis="y2", mode="lines+markers", line=dict(dash="dot", color="#444")
    ))
    fig.add_hline(y=100, line_dash="solid", line_color="black", line_width=2)
    fig.update_layout(
        title=titulo, height=400, barmode="group",
        yaxis=dict(title="Índice %", range=[0, 180]),
        yaxis2=dict(title="Volume Real", overlaying="y", side="right"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor="white",
        hovermode="x unified",
        bargap=0.15
    )
    return fig, df_total

# --- INTERFACE ---
st.markdown("# :material/upload_file: Gestão de Projeções")
uploaded_file = st.file_uploader("Arraste o arquivo Projecoes_semanais.xlsx aqui", type=["xlsx"])

if uploaded_file:
    with st.spinner('📊 Carregando e processando dados...'):
        df_raw = process_data(uploaded_file)
    
    if not df_raw.empty:
        with st.sidebar:
            st.title("⚙️ Filtros")
            todos_periodos = df_raw['Período'].unique().tolist()
            periodos_selecionados = st.multiselect("Filtrar Períodos:", options=todos_periodos, default=todos_periodos)

        if not periodos_selecionados:
            st.warning("Selecione ao menos um período.")
            st.stop()

        df_filtered = df_raw[df_raw['Período'].isin(periodos_selecionados)]

        # --- PÁGINA 1: PANORAMA ---
        st.markdown("## :material/dashboard: Panorama Geral")
        cols_top = st.columns([1, 2])
        
        ultimo_p = periodos_selecionados[-1]
        df_pizza = df_raw[(df_raw['Período'] == ultimo_p) & (df_raw['Produto'].astype(str).str.upper() != "TOTAL")]
        df_pizza = df_pizza.sort_values(col_valor_real, ascending=False)

        with cols_top[0].container(border=True):
            st.markdown(f"### Mix de Volume ({ultimo_p})")
            fig_mix = px.pie(df_pizza, values=col_valor_real, names='Produto', hole=0.5, color_discrete_sequence=cores_vermelho_mix)
            fig_mix.update_traces(textposition='inside', textinfo='percent+label')
            fig_mix.update_layout(margin=dict(t=30, b=10, l=10, r=10), height=350, showlegend=False)
            st.plotly_chart(fig_mix, use_container_width=True)

        with cols_top[1].container(border=True):
            st.markdown("### Evolução por Produto")
            df_ev = df_filtered[df_filtered['Produto'].astype(str).str.upper() != "TOTAL"]
            chart_geral = alt.Chart(df_ev).mark_line(point=True).encode(
                x=alt.X('Período:N', sort=None),
                y=alt.Y('Soma de VolUC:Q', title="Volume Real"),
                color=alt.Color('Produto:N', scale=alt.Scale(range=cores_vermelho_mix), sort='-y'),
                tooltip=['Produto', 'Período', 'Soma de VolUC']
            ).properties(height=300).interactive()
            st.altair_chart(chart_geral, use_container_width=True)

        # --- SEÇÃO DE CARDS ---
        st.markdown("### 🎯 Erro Médio de Projeção (Acumulado Período)")
        ordem_produtos = df_ev.groupby('Produto')[col_valor_real].sum().sort_values(ascending=False).index.tolist()
        cols_detail = st.columns(4)

        for i, produto in enumerate(ordem_produtos):
            df_p_sum = df_filtered[df_filtered['Produto'] == produto][semanas + [col_valor_real]].sum()
            dados_card = []
            for s in semanas:
                real = df_p_sum[col_valor_real]
                proj = df_p_sum[s]
                erro = ((proj / real) - 1) * 100 if real != 0 else 0
                dados_card.append({'Semana': s, 'Erro_Percentual': erro})
            
            df_card = pd.DataFrame(dados_card)
            erro_medio = df_card['Erro_Percentual'].mean()
            
            with cols_detail[i % 4].container(border=True):
                # Usando Metric para destaque rápido
                st.metric(
                    label=f"Avg Error: {produto}", 
                    value=f"{erro_medio:.1f}%",
                    delta=f"{df_card.iloc[-1]['Erro_Percentual']:.1f}% (S4)",
                    delta_color="inverse" # Vermelho se positivo (erro pra cima)
                )
                
                c_err = alt.Chart(df_card).mark_bar().encode(
                    x=alt.X('Semana:N', title=None, sort=semanas),
                    y=alt.Y('Erro_Percentual:Q', title="Erro %"),
                    color=alt.condition(
                        "datum.Erro_Percentual > 0",
                        alt.value('#8B0000'), 
                        alt.value('#E57373') 
                    ),
                    tooltip=[alt.Tooltip('Erro_Percentual:Q', format='.1f', title='Erro %')]
                ).properties(height=120)
                
                linha_zero = alt.Chart(pd.DataFrame({'y': [0]})).mark_rule(color='black').encode(y='y')
                st.altair_chart(c_err + linha_zero, use_container_width=True)

        # --- PÁGINA 2: ESTUDO DE PRECISÃO ---
        st.markdown('<div class="break-page"></div>', unsafe_allow_html=True)
        st.markdown("## :material/analytics: Estudo de Precisão por Mês")
        
        for periodo in periodos_selecionados:
            with st.expander(f"📅 Detalhes: {periodo}", expanded=True):
                df_mes = df_raw[df_raw["Período"] == periodo]
                col_a, col_b = st.columns([3, 1])
                
                fig_prod, df_mes_total = grafico_projeções_plotly(df_mes, f"Precisão - {periodo}")
                col_a.plotly_chart(fig_prod, use_container_width=True)

                if not df_mes_total.empty:
                    total_val = df_mes_total.iloc[0]
                    v_total = [(total_val[s] / total_val[col_valor_real] * 100) if total_val[col_valor_real] != 0 else 0 for s in semanas]
                    fig_t = go.Figure(go.Bar(x=semanas, y=v_total, marker_color=lista_vermelhos))
                    fig_t.add_hline(y=100, line_dash="solid", line_color="black")
                    fig_t.update_layout(title="Média do Mês", yaxis=dict(range=[0, 150]), height=400, plot_bgcolor="white")
                    col_b.plotly_chart(fig_t, use_container_width=True)
                
                # Dados brutos para conferência rápida
                if st.checkbox(f"Mostrar dados brutos - {periodo}", key=f"check_{periodo}"):
                    st.dataframe(df_mes.drop(columns=['Data_Ref']), use_container_width=True)

else:
    st.info("Aguardando upload do arquivo Excel para gerar o dashboard.")
