import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. Configuração da Página Web
st.set_page_config(page_title="Central de Triagem IA", layout="wide")
st.title("🏥 Central de Monitoramento e Previsão de Deterioração")

# =====================================================================
# 2. CARREGAR DADOS DA NUVEM (GOOGLE DRIVE)
# =====================================================================
# O 'ttl=60' faz o sistema recarregar o Google Drive a cada 60 segundos
@st.cache_data(ttl=60) 
def carregar_dados():
    # ⚠️ SUBSTITUA O TEXTO ABAIXO PELO ID DO SEU ARQUIVO NO GOOGLE DRIVE ⚠️  
    file_id = '1mP9QputMdhGPmUrboKzgWnaPiWFl3XlM'
    
    url_drive = f'https://drive.google.com/uc?id={file_id}&export=download'
    
    try:
        df_final = pd.read_csv(url_drive, sep=';', encoding='utf-8-sig')
    except:
        try:
            df_final = pd.read_csv(url_drive, sep=',', encoding='utf-8-sig')
        except:
            return pd.DataFrame() # Retorna vazio se der erro crítico
            
    # Converte a coluna de data
    df_final['DATA_REFERENCIA'] = pd.to_datetime(df_final['DATA_REFERENCIA'], format='%d/%m/%Y %H:%M')
    return df_final

try:
    df = carregar_dados()
    if df.empty:
        st.warning("Não foi possível carregar o arquivo CSV do Google Drive. Verifique se o link está público e se o ID está correto.")
        st.stop()
except Exception as e:
    st.error(f"Erro de conexão com o banco de dados. Detalhe: {e}")
    st.stop()

# =====================================================================
# 3. MENU LATERAL (Filtros de Paciente, Data e Exportação)
# =====================================================================
nrs_disponiveis = df['NR'].unique()
nr_selecionado = st.sidebar.selectbox("Selecione o Paciente (NR):", nrs_disponiveis)

df_paciente = df[df['NR'] == nr_selecionado].sort_values('DATA_REFERENCIA').copy()

df_paciente['DATA_FORMATADA'] = df_paciente['DATA_REFERENCIA'].dt.strftime('%d/%m/%Y %H:%M')
lista_datas = df_paciente['DATA_FORMATADA'].tolist()

data_selecionada = st.sidebar.selectbox("Selecione o Momento (Status):", lista_datas, index=len(lista_datas)-1)
linha_atual = df_paciente[df_paciente['DATA_FORMATADA'] == data_selecionada].iloc[0]

# --- MELHORIA 4: GERADOR DE EVOLUTIVO PARA O PRONTUÁRIO ---
st.sidebar.markdown("---")
st.sidebar.subheader("📄 Exportar Prontuário")

# Montagem do texto do Prontuário
causa_susp = linha_atual.get('Causas_Suspeitas', 'Sem causa específica identificada')
texto_prontuario = f"""EVOLUTIVO CLÍNICO COM SUPORTE DE IA
--------------------------------------------------
Data/Hora da Avaliação: {data_selecionada}
Paciente NR: {nr_selecionado}

[SINAIS VITAIS]
- NEWS Score: {int(linha_atual['Mediana_News'])}
- SpO2: {linha_atual['UltimoSPO2']}%
- Freq. Respiratória: {linha_atual['UltimoFR']} rpm
- Freq. Cardíaca: {linha_atual['UltimoFC']} bpm
- Pressão Sistólica: {linha_atual['UltimoPA']} mmHg
- Temperatura: {linha_atual['UltimoTemp']} °C

[ÍNDICES PREDITIVOS E FRAGILIDADE]
- Índice de Choque: {linha_atual['IndiceChoque']}
- Índice ROX: {linha_atual['IndiceRox']}
- Score de Fragilidade: {linha_atual['Score_FragilididadeClinica']}

[ALERTA DA IA - PROBABILIDADE DE DETERIORAÇÃO]
- Risco em 6h:  {linha_atual['Deterioracao_6h_(%)']}%
- Risco em 12h: {linha_atual['Deterioracao_12h_(%)']}%
- Risco em 24h: {linha_atual['Deterioracao_24h_(%)']}%
- Padrão Clínico Suspeito: {causa_susp}

Conduta: 
"""

st.sidebar.download_button(
    label="⬇️ Baixar Evolutivo (TXT)",
    data=texto_prontuario,
    file_name=f"Evolutivo_NR_{nr_selecionado}_{data_selecionada[:10].replace('/','-')}.txt",
    mime="text/plain",
    help="Baixe o resumo estruturado para copiar e colar no PEP do hospital."
)


# =====================================================================
# 4. PAINEL DE INDICADORES CLÍNICOS E SINAIS VITAIS
# =====================================================================
st.subheader(f"Status do Paciente NR: {nr_selecionado} (Avaliação de: {data_selecionada})")

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Score NEWS", int(linha_atual['Mediana_News']))
col2.metric("SpO2", f"{linha_atual['UltimoSPO2']}%")
col3.metric("Frequência Respiratória", f"{linha_atual['UltimoFR']} rpm", delta=f"{linha_atual['DeltaFR6h']} (últ. 6h)", delta_color="inverse")
col4.metric("Frequência Cardíaca", f"{linha_atual['UltimoFC']} bpm", delta=f"{linha_atual['DeltaFC6h']} (últ. 6h)", delta_color="inverse")
col5.metric("Pressão Sistólica", f"{linha_atual['UltimoPA']} mmHg", delta=f"{linha_atual['DeltaPA6h']} (últ. 6h)", delta_color="inverse")

st.markdown("<br>", unsafe_allow_html=True) 
col6, col7, col8, col9, col10 = st.columns(5)
col6.metric("Temperatura", f"{linha_atual['UltimoTemp']} °C")
col7.metric("Índice de Choque", f"{linha_atual['IndiceChoque']}")
col8.metric("Índice ROX", f"{linha_atual['IndiceRox']}")
col9.metric("Aceleração NEWS", f"{linha_atual['NewsAceleracao']}")
col10.metric("Score Fragilidade", f"{linha_atual['Score_FragilididadeClinica']}")

# =====================================================================
# 5. SISTEMA DE ALERTAS INTELIGENTES (BADGES)
# =====================================================================
st.markdown("---")
alertas_ativos = []
if linha_atual.get('Consciencia_Sustentada', 0) > 0: alertas_ativos.append("🧠 Queda de Consciência Prolongada")
if linha_atual.get('Hipotensao_Sustentada', 0) > 0: alertas_ativos.append("🩸 Hipotensão Sustentada")
if linha_atual.get('O2_Persistente', 0) > 0: alertas_ativos.append("🫁 Necessidade de O2 Persistente")
if linha_atual.get('Alerta_Respiratorio', 0) > 0: alertas_ativos.append("🚨 Risco de Falência Respiratória")
if linha_atual.get('FebreSustentada', 0) > 0: alertas_ativos.append("🤒 Febre Sustentada")

if alertas_ativos:
    for alerta in alertas_ativos:
        st.error(f"**ALERTA ATIVO NESTE MOMENTO:** {alerta}")
    
if pd.notna(linha_atual['Causas_Suspeitas']) and linha_atual['Causas_Suspeitas'] != "Sem Causa Específica":
    st.warning(f"**SUSPEITA DA IA:** O modelo detectou características de **{linha_atual['Causas_Suspeitas']}**.")

# =====================================================================
# 6. VELOCÍMETROS DE RISCO E EXPLICABILIDADE DA IA
# =====================================================================
st.subheader("🤖 Previsão de Risco (Machine Learning)")

col_r1, col_r2, col_r3, col_r4 = st.columns(4)

def criar_velocimetro(valor, titulo, lim_atencao, lim_critico):
    # Paleta de cores médica moderna
    cor_segura = "#10B981"  # Verde Esmeralda
    cor_atencao = "#F59E0B" # Amarelo Âmbar
    cor_critica = "#EF4444" # Vermelho Alerta

    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = valor,
        title = {'text': f"<span style='font-size: 22px; font-weight: bold;'>{titulo}</span>"},
        number = {'suffix': "%", 'font': {'size': 38}},
        gauge = {
            'axis': {'range': [0, 100], 'tickwidth': 2, 'tickcolor': "#374151"},
            'bar': {'color': "rgba(0,0,0,0)"}, # Esconde a barra azul padrão
            'bgcolor': "white",
            'borderwidth': 1,
            'bordercolor': "#374151",
            'steps': [
                {'range': [0, lim_atencao], 'color': cor_segura},
                {'range': [lim_atencao, lim_critico], 'color': cor_atencao},
                {'range': [lim_critico, 100], 'color': cor_critica}
            ],
            'threshold': {
                'line': {'color': "white", 'width': 8}, # Cria um PONTEIRO estiloso
                'thickness': 0.9,
                'value': valor
            }
        }
    ))
    
    # Fundo transparente para mesclar com o tema escuro/claro do Streamlit
    fig.update_layout(
        height=280, 
        margin=dict(l=15, r=15, t=40, b=15), 
        paper_bgcolor="rgba(0,0,0,0)", 
        font={'color': "#D1D5DB"} # Cor do texto adaptada para modo escuro
    )
    return fig

# Chamadas com as réguas (thresholds) corretas para cada horizonte!
col_r1.plotly_chart(criar_velocimetro(linha_atual['Deterioracao_6h_(%)'], "Risco em 6h", 30, 45), use_container_width=True)
col_r2.plotly_chart(criar_velocimetro(linha_atual['Deterioracao_12h_(%)'], "Risco em 12h", 45, 60), use_container_width=True)
col_r3.plotly_chart(criar_velocimetro(linha_atual['Deterioracao_18h_(%)'], "Risco em 18h", 50, 70), use_container_width=True)
col_r4.plotly_chart(criar_velocimetro(linha_atual['Deterioracao_24h_(%)'], "Risco em 24h", 50, 70), use_container_width=True)

# --- MELHORIA 3: EXPLICABILIDADE DA IA (SHAP / REGRAS DE PESO) ---
with st.expander("🔍 Por que a IA tomou essa decisão? (Fatores de Risco)"):
    st.markdown("Baseado na avaliação em tempo real, os parâmetros abaixo foram os **principais responsáveis** por aumentar o risco atual do paciente:")
    
    fatores_peso = []
    
    def pega_valor(coluna, padrao=0.0):
        val = linha_atual.get(coluna, padrao)
        if pd.isna(val): return padrao
        try:
            return float(str(val))
        except:
            return padrao
            
    # 1. PARAMETRIZAÇÃO DOS THRESHOLDS (Igual aos Velocímetros)
    risco_6h = pega_valor('Deterioracao_6h_(%)')
    risco_12h = pega_valor('Deterioracao_12h_(%)')
    risco_18h = pega_valor('Deterioracao_18h_(%)')
    risco_24h = pega_valor('Deterioracao_24h_(%)')
    
    # Limites Críticos configurados
    limite_critico_6h = 45.0
    limite_critico_12h = 60.0
    limite_critico_18h = 70.0
    limite_critico_24h = 70.0
    
    # Avaliação Individual por Horizonte
    if risco_6h >= limite_critico_6h:
        fatores_peso.append(f"**🚨 Alerta Imediato (6h = {risco_6h}%):** Ultrapassou o limiar crítico de {limite_critico_6h}%. A IA detectou sinais agudos de colapso para o plantão atual.")
        
    if risco_12h >= limite_critico_12h:
        fatores_peso.append(f"**⚠️ Alerta Curto Prazo (12h = {risco_12h}%):** Ultrapassou o limiar de {limite_critico_12h}%. Indicativo de instabilidade se a conduta não for alterada no próximo turno.")
        
    if risco_18h >= limite_critico_18h:
        fatores_peso.append(f"**⚠️ Alerta Médio Prazo (18h = {risco_18h}%):** Ultrapassou o limiar de {limite_critico_18h}%.")
        
    if risco_24h >= limite_critico_24h:
        fatores_peso.append(f"**📉 Risco de Tendência (24h = {risco_24h}%):** Ultrapassou o limiar de {limite_critico_24h}%. O padrão atual das últimas horas aponta para falência sistêmica amanhã.")

    # 2. OLHANDO PARA OS SINAIS VITAIS E ÍNDICES CLÍNICOS
    if pega_valor('IndiceChoque') >= 0.8: 
        fatores_peso.append(f"**Esforço Hemodinâmico (Índice de Choque: {pega_valor('IndiceChoque')}):** O coração está acelerando muito em relação à pressão arterial (Normal é < 0.8).")
        
    if pega_valor('IndiceRox', 10) <= 8.0: 
        fatores_peso.append(f"**Alerta Respiratório (Índice ROX: {pega_valor('IndiceRox')}):** Indicador de piora na troca de oxigênio (Valores caindo exigem atenção).")
        
    if pega_valor('Mediana_News') >= 5: 
        fatores_peso.append(f"**Score NEWS-2 de Atenção ({int(pega_valor('Mediana_News'))}):** A soma dos sinais vitais atingiu o protocolo de risco médio/alto do hospital.")
        
    if pega_valor('UltimoSPO2', 100) < 93: 
        fatores_peso.append(f"**Dessaturação (SpO2: {pega_valor('UltimoSPO2')}%):** Nível de oxigênio no sangue abaixo da margem de segurança clínica.")
        
    if pega_valor('UltimoTemp', 36) > 37.8: 
        fatores_peso.append(f"**Pico Febril Recente ({pega_valor('UltimoTemp')}°C):** Sugere possível resposta inflamatória ou infecciosa ativa.")
        
    if fatores_peso:
        for fator in fatores_peso:
            st.warning(f"{fator}")
    else:
        st.success("✅ No momento selecionado, os parâmetros vitais estão compensados e a IA não identificou cruzamento de nenhum limiar crítico.")
    
    st.caption("*Nota técnica: Esta análise foca nas variáveis clínicas com maior correlação estatística para instabilidade. Padrões vitais estáveis reduzem o nível do risco.*")

# =====================================================================
# LÓGICA DE PAGINAÇÃO (SLIDER PARA OS GRÁFICOS)
# =====================================================================
st.markdown("---")
st.subheader("📈 Trajetória Clínica e Sinais Vitais (Interativo)")

total_registos = len(df_paciente)
tamanho_janela = 15 

if total_registos > tamanho_janela:
    st.info(f"O paciente tem **{total_registos}** registros. Utilize a barra abaixo para viajar no tempo (exibindo 15 pontos de cada vez).")
    inicio = st.slider(
        "Navegar no histórico:", 
        min_value=0, 
        max_value=total_registos - tamanho_janela, 
        value=total_registos - tamanho_janela,
        help="Deslize para a esquerda para ver avaliações mais antigas."
    )
    df_plot = df_paciente.iloc[inicio : inicio + tamanho_janela]
else:
    df_plot = df_paciente

# =====================================================================
# GRÁFICOS INTERATIVOS
# =====================================================================
st.markdown("#### 1. Evolução dos Sinais Vitais Essenciais")
fig_vitais = go.Figure()
fig_vitais.add_trace(go.Scatter(x=df_plot['DATA_REFERENCIA'], y=df_plot['UltimoFC'], mode='lines+markers', name='Frequência Cardíaca (bpm)', line=dict(color='red')))
fig_vitais.add_trace(go.Scatter(x=df_plot['DATA_REFERENCIA'], y=df_plot['UltimoPA'], mode='lines+markers', name='Pressão Sistólica (mmHg)', line=dict(color='blue')))
fig_vitais.add_trace(go.Scatter(x=df_plot['DATA_REFERENCIA'], y=df_plot['UltimoFR'], mode='lines+markers', name='Frequência Respiratória (rpm)', line=dict(color='green')))
fig_vitais.update_layout(yaxis_title="Valores", hovermode="x unified", height=400)
fig_vitais.update_xaxes(tickmode='array', tickvals=df_plot['DATA_REFERENCIA'], ticktext=df_plot['DATA_REFERENCIA'].dt.strftime('%d/%m %H:%M'), tickangle=-45)
st.plotly_chart(fig_vitais, use_container_width=True)

st.markdown("#### 2. Curva Térmica (Temperatura)")
fig_temp = go.Figure()
fig_temp.add_trace(go.Scatter(x=df_plot['DATA_REFERENCIA'], y=df_plot['UltimoTemp'], mode='lines+markers', name='Temperatura (°C)', line=dict(color='darkorange', width=3)))
fig_temp.add_hline(y=37.8, line_dash="dot", line_color="red", annotation_text="Pico Febril (37.8°C)")
fig_temp.update_layout(yaxis_title="Temperatura (°C)", hovermode="x unified", height=300)
fig_temp.update_yaxes(range=[35.0, 41.0]) 
fig_temp.update_xaxes(tickmode='array', tickvals=df_plot['DATA_REFERENCIA'], ticktext=df_plot['DATA_REFERENCIA'].dt.strftime('%d/%m %H:%M'), tickangle=-45)
st.plotly_chart(fig_temp, use_container_width=True)

st.markdown("#### 3. Índices Preditivos: Choque Hemodinâmico vs Risco de Intubação (ROX)")
fig_indices = make_subplots(specs=[[{"secondary_y": True}]])
fig_indices.add_trace(go.Scatter(x=df_plot['DATA_REFERENCIA'], y=df_plot['IndiceChoque'], mode='lines+markers', name='Índice de Choque', line=dict(color='red', width=3)), secondary_y=False)
fig_indices.add_trace(go.Scatter(x=df_plot['DATA_REFERENCIA'], y=df_plot['IndiceRox'], mode='lines+markers', name='Índice ROX', line=dict(color='green', dash='dash', width=3)), secondary_y=True)
fig_indices.update_layout(hovermode="x unified", height=400)
fig_indices.update_yaxes(title_text="Índice de Choque", secondary_y=False, color="red")
fig_indices.update_yaxes(title_text="Índice ROX", secondary_y=True, color="green")
fig_indices.add_hline(y=1.0, line_dash="dot", line_color="darkred", annotation_text="Risco Choque (>1.0)", secondary_y=False)
fig_indices.add_hline(y=4.88, line_dash="dot", line_color="darkgreen", annotation_text="Risco Intubação ROX (<4.88)", secondary_y=True)
fig_indices.update_xaxes(tickmode='array', tickvals=df_plot['DATA_REFERENCIA'], ticktext=df_plot['DATA_REFERENCIA'].dt.strftime('%d/%m %H:%M'), tickangle=-45)
st.plotly_chart(fig_indices, use_container_width=True)

st.markdown("#### 4. Risco Clínico Protocolar vs Saturação de Oxigênio")
fig_news = make_subplots(specs=[[{"secondary_y": True}]])
fig_news.add_trace(go.Scatter(x=df_plot['DATA_REFERENCIA'], y=df_plot['Mediana_News'], mode='lines+markers', name='NEWS (Mediana)', line=dict(color='purple', width=3)), secondary_y=False)
fig_news.add_trace(go.Scatter(x=df_plot['DATA_REFERENCIA'], y=df_plot['UltimoSPO2'], mode='lines+markers', name='SpO2 (%)', line=dict(color='cyan', dash='dash', width=3)), secondary_y=True)
fig_news.update_layout(hovermode="x unified", height=400)
fig_news.update_yaxes(title_text="Score NEWS", secondary_y=False, color="purple")
fig_news.update_yaxes(title_text="SpO2 (%)", secondary_y=True, color="cyan")
fig_news.update_xaxes(tickmode='array', tickvals=df_plot['DATA_REFERENCIA'], ticktext=df_plot['DATA_REFERENCIA'].dt.strftime('%d/%m %H:%M'), tickangle=-45)
st.plotly_chart(fig_news, use_container_width=True)

st.markdown("#### 5. Linha do Tempo de Risco (IA)")
fig_linha = go.Figure()
fig_linha.add_trace(go.Scatter(x=df_plot['DATA_REFERENCIA'], y=df_plot['Deterioracao_6h_(%)'], mode='lines+markers', name='Risco 6h', line=dict(color='firebrick', width=2)))
fig_linha.add_trace(go.Scatter(x=df_plot['DATA_REFERENCIA'], y=df_plot['Deterioracao_12h_(%)'], mode='lines+markers', name='Risco 12h', line=dict(color='orange', width=2)))
fig_linha.add_trace(go.Scatter(x=df_plot['DATA_REFERENCIA'], y=df_plot['Deterioracao_24h_(%)'], mode='lines+markers', name='Risco 24h', line=dict(color='gold', width=2)))
fig_linha.add_hline(y=50, line_dash="dot", line_color="gray", annotation_text="Atenção (50%)")
fig_linha.add_hline(y=70, line_dash="dot", line_color="red", annotation_text="Crítico (70%)")
fig_linha.update_layout(yaxis_title="Probabilidade (%)", hovermode="x unified", height=400, yaxis=dict(range=[-5, 105]))
fig_linha.update_xaxes(tickmode='array', tickvals=df_plot['DATA_REFERENCIA'], ticktext=df_plot['DATA_REFERENCIA'].dt.strftime('%d/%m %H:%M'), tickangle=-45)
st.plotly_chart(fig_linha, use_container_width=True)
