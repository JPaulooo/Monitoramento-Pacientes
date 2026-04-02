import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time 

# 1. Configuração da Página Web
st.set_page_config(page_title="Central de Triagem IA", layout="wide")
st.title("🏥 Central de Monitoramento e Previsão de Deterioração")

# =====================================================================
# 2. CARREGAR DADOS DA NUVEM (GOOGLE DRIVE)   
# =====================================================================
@st.cache_data(ttl=60) 
def carregar_dados():
    file_id = '1GHl4ACKit8D3RzFKyVlJGXNvyzj76SMo'
    url_drive = f'https://drive.google.com/uc?id={file_id}&export=download'
    
    try:
        df_final = pd.read_csv(url_drive, sep=';', encoding='utf-8-sig')
    except:
        try:
            df_final = pd.read_csv(url_drive, sep=',', encoding='utf-8-sig')
        except:
            return pd.DataFrame() 
            
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
# 3. MENU LATERAL E LÓGICA DE NAVEGAÇÃO (COM MEMÓRIA DE CLIQUE)
# =====================================================================
nrs_disponiveis = df['NR'].unique().tolist()
nrs_disponiveis.insert(0, "🌐 Todos os Pacientes")

# Inicia a memória de navegação
if 'paciente_selecionado' not in st.session_state:
    st.session_state['paciente_selecionado'] = "🌐 Todos os Pacientes"

# Inicia uma memória para a tabela não travar o clique
if 'chave_tabela' not in st.session_state:
    st.session_state['chave_tabela'] = str(time.time())

# Descobre a posição atual do menu com base na memória
try:
    idx_atual = nrs_disponiveis.index(st.session_state['paciente_selecionado'])
except:
    idx_atual = 0

# O menu lateral agora navega por INDEX, evitando erro de recarregamento
nr_selecionado = st.sidebar.selectbox(
    "Selecione a Visão ou o Paciente (NR):", 
    nrs_disponiveis,
    index=idx_atual
)

# Atualiza a memória com o clique do usuário no menu
st.session_state['paciente_selecionado'] = nr_selecionado

# =====================================================================
# MODO 1: VISÃO GERAL DA UTI (TRIAGEM INTELIGENTE)
# =====================================================================
if nr_selecionado == "🌐 Todos os Pacientes":
    st.subheader("🌐 Visão Geral dos Pacientes - Triagem por IA")
    
    # Pega a última avaliação cronológica de CADA paciente
    df_visao_geral = df.sort_values('DATA_REFERENCIA').drop_duplicates(subset=['NR'], keep='last').copy()
    
    # Converte colunas de risco para número e acha o pico máximo de perigo
    colunas_risco = ['Deterioracao_6h_(%)', 'Deterioracao_12h_(%)', 'Deterioracao_18h_(%)', 'Deterioracao_24h_(%)']
    for col in colunas_risco:
        df_visao_geral[col] = pd.to_numeric(df_visao_geral[col], errors='coerce').fillna(0)
        
    df_visao_geral['Risco_Max'] = df_visao_geral[colunas_risco].max(axis=1)
    
    def calcular_horizonte(linha):
        max_risco = linha['Risco_Max']
        if max_risco == 0: return "-"
        if linha.get('Deterioracao_6h_(%)', 0) == max_risco: return "🚨 Em 6h"
        if linha.get('Deterioracao_12h_(%)', 0) == max_risco: return "⚠️ Em 12h"
        if linha.get('Deterioracao_18h_(%)', 0) == max_risco: return "⚠️ Em 18h"
        if linha.get('Deterioracao_24h_(%)', 0) == max_risco: return "📉 Em 24h"
        return "-"
    df_visao_geral['Horizonte'] = df_visao_geral.apply(calcular_horizonte, axis=1)
    
    def formatar_news(valor):
        if pd.isna(valor): return "N/A"
        if valor >= 7: return f"🔴 {int(valor)}"
        if valor >= 5: return f"🟡 {int(valor)}"
        return f"🟢 {int(valor)}"
    df_visao_geral['NEWS_Status'] = df_visao_geral['Mediana_News'].apply(formatar_news)

    # Ordena a UTI do maior risco para o menor e reseta o índice
    df_visao_geral = df_visao_geral.sort_values(by='Risco_Max', ascending=False).reset_index(drop=True)
    
    # Monta a tabela limpa
    df_tabela = df_visao_geral[['NR', 'DATA_REFERENCIA', 'Risco_Max', 'Horizonte', 'NEWS_Status', 'IndiceChoque', 'IndiceRox', 'UltimoSPO2', 'UltimoFR', 'DeltaFR6h','UltimoFC', 'DeltaFC6h','UltimoPA', 'DeltaPA6h']].copy()
    
    # RESUMO EXECUTIVO (PAINEL DE TOPO)
    total_leitos = len(df_tabela)
    criticos = len(df_tabela[df_tabela['Risco_Max'] >= 70])
    atencao = len(df_tabela[(df_tabela['Risco_Max'] >= 50) & (df_tabela['Risco_Max'] < 70)])
    
    
    st.markdown("---")
    c1, c2, c3, c4 = st.columns(4)
    # Coloquei o caractere invisível antes do total_leitos
    c1.metric("🛌 Leitos Monitorados", f"⠀⠀{total_leitos}")
    c2.metric("🚨 Risco Crítico (>70%)", f"⠀⠀{criticos}")
    c3.metric("⚠️ Em Atenção (>50%)", f"⠀⠀{atencao}")
    c4.metric(" ✅ Estáveis", f"⠀{total_leitos - criticos - atencao}")
    st.markdown("---")
    
    st.markdown("**Selecione a linha de um paciente abaixo para abrir o prontuário detalhado:**")

    # --- MELHORIA: ALINHAMENTO CENTRALIZADO EM TODAS AS COLUNAS ---
    evento_clique = st.dataframe(
        df_tabela,
        key=st.session_state['chave_tabela'], 
        column_config={
            "NR": st.column_config.TextColumn("Nr Atendimento", width=5),
            "DATA_REFERENCIA": st.column_config.DatetimeColumn("Última Avaliação", format="DD/MM/YYYY HH:mm", width=5),
            "Risco_Max": st.column_config.ProgressColumn("Maior Risco IA (%)", format="%.1f", min_value=0, max_value=100, width=500),
            "Horizonte": st.column_config.TextColumn("Horizonte Crítico", width=5),
            "NEWS_Status": st.column_config.TextColumn("Mediana NEWS", width=5),
            "IndiceChoque": st.column_config.NumberColumn("Índice Choque", format="%.2f", width=5),
            "IndiceRox": st.column_config.NumberColumn("Índice ROX", format="%.2f", width=5),
            "UltimoSPO2": st.column_config.NumberColumn("SpO2 (%)"),
            "UltimoFR": st.column_config.TextColumn("FR (rpm)", width=5),
            "DeltaFR6h": st.column_config.TextColumn("DeltaFR", width=5),
            "UltimoFC": st.column_config.TextColumn("FC (bpm)", width=5),
            "DeltaFC6h": st.column_config.TextColumn("DeltaFC", width=5),
            "UltimoPA": st.column_config.TextColumn("PA Sistólica", width=5),
            "DeltaPA6h": st.column_config.TextColumn("DeltaPA", width=5)
        },
        hide_index=True,
        use_container_width=True,
        height=550,
        on_select="rerun",           
        selection_mode="single-row"  
    )
    
    # LÓGICA DE CAPTURA DE CLIQUE E REDIRECIONAMENTO
    if evento_clique.selection.rows:
        indice_clicado = evento_clique.selection.rows[0]
        nr_destino = df_tabela.iloc[indice_clicado]['NR']
        
        if st.session_state['paciente_selecionado'] != nr_destino:
            st.session_state['paciente_selecionado'] = nr_destino
            st.session_state['chave_tabela'] = str(time.time()) 
            st.rerun()

# =====================================================================
# MODO 2: VISÃO INDIVIDUAL DO PACIENTE 
# =====================================================================
else:
    # --- NOVO: BOTÃO DE VOLTAR ---
    if st.button("⬅️ Voltar para Visão Geral"):
        st.session_state['paciente_selecionado'] = "🌐 Todos os Pacientes"
        st.rerun()
        
    df_paciente = df[df['NR'] == nr_selecionado].sort_values('DATA_REFERENCIA').copy()

    df_paciente['DATA_FORMATADA'] = df_paciente['DATA_REFERENCIA'].dt.strftime('%d/%m/%Y %H:%M')
    lista_datas = df_paciente['DATA_FORMATADA'].tolist()

    data_selecionada = st.sidebar.selectbox("Selecione o Momento (Status):", lista_datas, index=len(lista_datas)-1)
    linha_atual = df_paciente[df_paciente['DATA_FORMATADA'] == data_selecionada].iloc[0]

    # Exportação para Prontuário
    st.sidebar.markdown("---")
    st.sidebar.subheader("📄 Exportar Prontuário")
    causa_susp = linha_atual.get('Causas_Suspeitas', 'Sem causa específica identificada')
    texto_prontuario = f"""EVOLUTIVO CLÍNICO COM SUPORTE DE IA
--------------------------------------------------
Data/Hora da Avaliação: {data_selecionada}
Paciente NR: {nr_selecionado}

[SINAIS VITAIS]
- Mediana NEWS Score: {int(linha_atual['Mediana_News'])}
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
        label="⬇️ Baixar Evolutivo (TXT)", data=texto_prontuario,
        file_name=f"Evolutivo_NR_{nr_selecionado}_{data_selecionada[:10].replace('/','-')}.txt", mime="text/plain"
    )

    # Painel Clínico
    st.subheader(f"Status do Paciente NR: {nr_selecionado} (Avaliação de: {data_selecionada})")

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Mediana NEWS", f"⠀{int(linha_atual['Mediana_News'])}")
    
    # Adicionado o delta com a coluna Spo2_Tendencia
    col2.metric("Ultima SpO2", f"{linha_atual['UltimoSPO2']}%", delta=f"{linha_atual['Spo2_Tendencia']} (Tendência)")
    
    col3.metric("Última Freq. Respiratória", f"{linha_atual['UltimoFR']} rpm", delta=f"{linha_atual['DeltaFR6h']} (Delta últ. 6h)", delta_color="inverse")
    col4.metric("Última Freq. Cardíaca", f"{linha_atual['UltimoFC']} bpm", delta=f"{linha_atual['DeltaFC6h']} (Delta últ. 6h)", delta_color="inverse")
    col5.metric("Pressão Sistólica", f"{linha_atual['UltimoPA']} mmHg", delta=f"{linha_atual['DeltaPA6h']} (Delta últ. 6h)", delta_color="inverse")

    st.markdown("<br>", unsafe_allow_html=True) 
    col6, col7, col8, col9, col10 = st.columns(5)
    col6.metric("Últ. Temperatura", f"{linha_atual['UltimoTemp']} °C")
    col7.metric("Índice de Choque", (f"⠀{linha_atual['IndiceChoque']}"),
    help="Cálculo: Frequência Cardíaca / Pressão Sistólica. Valores acima de 0.8 a 1.0 indicam alto risco de choque hemodinâmico oculto.")
    col8.metric("Índice ROX", (f"{linha_atual['IndiceRox']}"),
    help="Mede a capacidade respiratória:  > 4.88 Boa resposta ao Oxigenio | Entre 3.85 e 4.88 Zona de Atenção | < 3.88 Alto Risco de Falha Respiratória.")
    col9.metric("Mediana Freq. Resp.", f"⠀{linha_atual['Mediana_FR']}")
    col10.metric("Score Fragilidade", (f"⠀{linha_atual['Score_FragilididadeClinica']}"), 
    help="""Mede o quão “frágil” o paciente já é antes de piorar. Variáveis:
- Acamado (Peso 3)
- Consciência Sustentada (quanto pior a cognição basal → maior fragilidade)
- IdadeNormalizada 0-1 (Peso 2.5)
- Comorbidades: DNG, IC e CA (Peso 2) | DM (Peso 1.5) | HAS (Peso 0.5)

SCORE TOTAL: 0 - 2 Baixa Fragilidadde | 2 - 5 Moderada | 5 - 8 Alta | Maior ou igual a 8 Alta Fragilidade
""")

    st.markdown("<br>", unsafe_allow_html=True) 
    
    # --- TERCEIRA LINHA (NOVOS DADOS DE TENDÊNCIA) ---
    col11, col12, col13, col14, col15 = st.columns(5)
    # Adicionei "h" imaginando que o tempo é em horas e "rpm" na FR. Se for diferente no seu banco, é só apagar a letra!
    col15.metric("Aceleração NEWS", f"⠀{linha_atual['NewsAceleracao']}")
    col11.metric("Tendência NEWS", (f"⠀{linha_atual['News_Tendencia']}"),
    help="Direção para onde o quadro clínico geral está caminhando (melhorando:-1, piorando:1 ou estável:0).")             
    col12.metric("Tempo NEWS Alto", (f"⠀{linha_atual['Tempo_NewsAlto']} h"),
    help="Quantidade total de horas consecutivas que este paciente permaneceu na zona de perigo do protocolo NEWS. News maior ou igual a 6") 
    col13.metric("Volatilidade NEWS", (f"⠀{linha_atual['News_Volatilidade']}"),
    help="É o desvio padrão dos valores do NEWS. 0 - Sem piora |  1 - 2 Algumas pioras | Maior ou igual a 3 Piora Sustentada/instabilidade")            
    col14.metric("Piora Sustentada NEWS (Degrau)", (f"⠀⠀{linha_atual['News_PioraSustentadaDegrau']}"),
    help="Conta quantos aumentos consecutivos aconteceram no NEWS. 0 - 1 Estável |  1 - 2 Oscilação Moderada | > 2 Alta instabilidade") 

    # Sistema de Alertas
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

    # Velocímetros de Risco
    st.subheader("🤖 Previsão de Risco (Machine Learning)")
    col_r1, col_r2, col_r3, col_r4 = st.columns(4)

    def criar_velocimetro(valor, titulo, lim_atencao, lim_critico):
        cor_segura = "#10B981"  
        cor_atencao = "#F59E0B" 
        cor_critica = "#EF4444" 

        fig = go.Figure(go.Indicator(
            mode = "gauge+number", value = valor,
            title = {'text': f"<span style='font-size: 22px; font-weight: bold;'>{titulo}</span>"},
            number = {'suffix': "%", 'font': {'size': 38}},
            gauge = {
                'axis': {'range': [0, 100], 'tickwidth': 2, 'tickcolor': "#374151"},
                'bar': {'color': "rgba(0,0,0,0)"},
                'bgcolor': "white", 'borderwidth': 1, 'bordercolor': "#374151",
                'steps': [
                    {'range': [0, lim_atencao], 'color': cor_segura},
                    {'range': [lim_atencao, lim_critico], 'color': cor_atencao},
                    {'range': [lim_critico, 100], 'color': cor_critica}
                ],
                'threshold': {'line': {'color': "white", 'width': 8}, 'thickness': 0.9, 'value': valor}
            }
        ))
        fig.update_layout(height=280, margin=dict(l=15, r=15, t=40, b=15), paper_bgcolor="rgba(0,0,0,0)", font={'color': "#D1D5DB"})
        return fig

    col_r1.plotly_chart(criar_velocimetro(linha_atual['Deterioracao_6h_(%)'], "Risco em 6h", 30, 45), use_container_width=True)
    col_r2.plotly_chart(criar_velocimetro(linha_atual['Deterioracao_12h_(%)'], "Risco em 12h", 45, 60), use_container_width=True)
    col_r3.plotly_chart(criar_velocimetro(linha_atual['Deterioracao_18h_(%)'], "Risco em 18h", 50, 70), use_container_width=True)
    col_r4.plotly_chart(criar_velocimetro(linha_atual['Deterioracao_24h_(%)'], "Risco em 24h", 50, 70), use_container_width=True)

    with st.expander("🔍 Por que a IA tomou essa decisão? (Fatores de Risco)"):
        st.markdown("Baseado na avaliação em tempo real, os parâmetros abaixo foram os **principais responsáveis** por aumentar o risco atual do paciente:")
        fatores_peso = []
        def pega_valor(coluna, padrao=0.0):
            val = linha_atual.get(coluna, padrao)
            if pd.isna(val): return padrao
            try: return float(str(val))
            except: return padrao
                
        risco_6h = pega_valor('Deterioracao_6h_(%)')
        risco_12h = pega_valor('Deterioracao_12h_(%)')
        risco_18h = pega_valor('Deterioracao_18h_(%)')
        risco_24h = pega_valor('Deterioracao_24h_(%)')
        
        if risco_6h >= 45.0: fatores_peso.append(f"**🚨 Alerta Imediato (6h = {risco_6h}%):** Ultrapassou o limiar crítico de 45.0%. A IA detectou sinais agudos de colapso.")
        if risco_12h >= 60.0: fatores_peso.append(f"**⚠️ Alerta Curto Prazo (12h = {risco_12h}%):** Ultrapassou o limiar de 60.0%. Indicativo de instabilidade se a conduta não for alterada.")
        if risco_18h >= 70.0: fatores_peso.append(f"**⚠️ Alerta Médio Prazo (18h = {risco_18h}%):** Ultrapassou o limiar de 70.0%.")
        if risco_24h >= 70.0: fatores_peso.append(f"**📉 Risco de Tendência (24h = {risco_24h}%):** Ultrapassou o limiar de 70.0%. O padrão aponta para falência sistêmica amanhã.")

        if pega_valor('IndiceChoque') >= 0.8: fatores_peso.append(f"**Esforço Hemodinâmico (Índice de Choque: {pega_valor('IndiceChoque')}):** Coração acelerado em relação à pressão (Normal < 0.8).")
        if pega_valor('IndiceRox', 10) <= 8.0: fatores_peso.append(f"**Alerta Respiratório (Índice ROX: {pega_valor('IndiceRox')}):** Piora na troca de oxigênio.")
        if pega_valor('Mediana_News') >= 5: fatores_peso.append(f"**Score NEWS-2 de Atenção ({int(pega_valor('Mediana_News'))}):** Sinais vitais atingiram protocolo de risco.")
        if pega_valor('UltimoSPO2', 100) < 93: fatores_peso.append(f"**Dessaturação (SpO2: {pega_valor('UltimoSPO2')}%):** Oxigênio no sangue abaixo da margem de segurança.")
        if pega_valor('UltimoTemp', 36) > 37.8: fatores_peso.append(f"**Pico Febril Recente ({pega_valor('UltimoTemp')}°C):** Sugere possível resposta inflamatória/infecciosa.")
            
        if fatores_peso:
            for fator in fatores_peso: st.warning(f"{fator}")
        else:
            st.success("✅ No momento selecionado, os parâmetros vitais estão compensados.")

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
    fig_news.update_yaxes(title_text="Mediana Score NEWS", secondary_y=False, color="purple")
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
