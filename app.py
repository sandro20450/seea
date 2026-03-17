import streamlit as st

st.title("🎯 Roleta Tracker - 12 Segundos")

# 1. MEMÓRIA RÁPIDA E BOTÃO DE LIMPEZA
if 'historico' not in st.session_state:
    st.session_state.historico = []

col_input, col_btn = st.columns([3, 1])
with col_input:
    numero_sorteado = st.number_input("Digite o número (0 a 36):", min_value=0, max_value=36, step=1)
with col_btn:
    st.write("") # Espaço para alinhar o botão
    st.write("")
    if st.button("Registrar"):
        st.session_state.historico.append(numero_sorteado)
        st.rerun() # Atualiza a tela na hora

if st.button("🗑️ Limpar Registros"):
    st.session_state.historico = []
    st.rerun()

st.write("---")

# 2. FUNÇÕES DE MAPEAMENTO (Dúzias e Linhas/Colunas)
def qual_duzia(n):
    if n == 0: return 0
    if 1 <= n <= 12: return 1
    if 13 <= n <= 24: return 2
    if 25 <= n <= 36: return 3

def qual_linha(n):
    if n == 0: return 0
    if n % 3 == 1: return 1 # 1, 4, 7... 34
    if n % 3 == 2: return 2 # 2, 5, 8... 35
    if n % 3 == 0: return 3 # 3, 6, 9... 36

# 3. ANÁLISE E INDICADORES NATIVOS
st.write("### Análise da Mesa")
st.info(f"Últimos números: {st.session_state.historico}")

if len(st.session_state.historico) > 0:
    # Função para contar os atrasos
    def contar_atraso(funcao_mapeamento, valor_alvo):
        atraso = 0
        for num in reversed(st.session_state.historico):
            if funcao_mapeamento(num) == valor_alvo:
                break
            atraso += 1
        return atraso

    # Calculando os atrasos exatos
    atraso_d1 = contar_atraso(qual_duzia, 1)
    atraso_d2 = contar_atraso(qual_duzia, 2)
    atraso_d3 = contar_atraso(qual_duzia, 3)
    
    atraso_l1 = contar_atraso(qual_linha, 1)
    atraso_l2 = contar_atraso(qual_linha, 2)
    atraso_l3 = contar_atraso(qual_linha, 3)

    # Mostrando os atrasos com st.metric em colunas
    st.write("**Atrasos Atuais (Rodadas sem sair):**")
    col1, col2, col3 = st.columns(3)
    col1.metric("1ª Dúzia", atraso_d1)
    col2.metric("2ª Dúzia", atraso_d2)
    col3.metric("3ª Dúzia", atraso_d3)
    
    col4, col5, col6 = st.columns(3)
    col4.metric("1ª Linha", atraso_l1)
    col5.metric("2ª Linha", atraso_l2)
    col6.metric("3ª Linha", atraso_l3)

    # 4. A REGRA DE ALERTA (st.success)
    ultimo_num = st.session_state.historico[-1]
    duzia_atual = qual_duzia(ultimo_num)
    linha_atual = qual_linha(ultimo_num)

    # Verificando Dúzias Atrasadas >= 5
    for i, atraso in enumerate([atraso_d1, atraso_d2, atraso_d3], start=1):
        if atraso >= 5:
            if duzia_atual != 0: # Ignora se o último foi o zero
                st.success(f"🚨 ALERTA: {i}ª Dúzia com {atraso} atrasos! APOSTE: {i}ª Dúzia + {duzia_atual}ª Dúzia (Última que saiu).")
            else:
                st.info(f"⚠️ {i}ª Dúzia com {atraso} atrasos. O último número foi 0, aguarde o próximo para combinar.")

    # Verificando Linhas Atrasadas >= 5
    for i, atraso in enumerate([atraso_l1, atraso_l2, atraso_l3], start=1):
        if atraso >= 5:
            if linha_atual != 0:
                st.success(f"🚨 ALERTA: {i}ª Linha com {atraso} atrasos! APOSTE: {i}ª Linha + {linha_atual}ª Linha (Última que saiu).")
            else:
                st.info(f"⚠️ {i}ª Linha com {atraso} atrasos. O último número foi 0, aguarde.")
else:
    st.info("Nenhum número registrado. Comece a digitar para iniciar a contagem.")
