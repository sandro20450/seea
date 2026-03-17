import streamlit as st

st.title("🎯 Roleta Tracker - 12 Segundos")

# 1. MEMÓRIA RÁPIDA
if 'historico' not in st.session_state:
    st.session_state.historico = []

# 2. FUNÇÕES DE MAPEAMENTO
def qual_duzia(n):
    if n == 0: return 0
    if 1 <= n <= 12: return 1
    if 13 <= n <= 24: return 2
    if 25 <= n <= 36: return 3

def qual_linha(n):
    if n == 0: return 0
    if n % 3 == 1: return 1
    if n % 3 == 2: return 2
    if n % 3 == 0: return 3

# 3. O CÉREBRO: FAZ OS CÁLCULOS ANTES DE DESENHAR A TELA
alertas_verdes = []

if len(st.session_state.historico) > 0:
    def contar_atraso(funcao_mapeamento, valor_alvo):
        atraso = 0
        for num in reversed(st.session_state.historico):
            if funcao_mapeamento(num) == valor_alvo:
                break
            atraso += 1
        return atraso

    # Calculando atrasos
    atrasos = {
        "d1": contar_atraso(qual_duzia, 1),
        "d2": contar_atraso(qual_duzia, 2),
        "d3": contar_atraso(qual_duzia, 3),
        "l1": contar_atraso(qual_linha, 1),
        "l2": contar_atraso(qual_linha, 2),
        "l3": contar_atraso(qual_linha, 3)
    }

    ultimo_num = st.session_state.historico[-1]
    duzia_atual = qual_duzia(ultimo_num)
    linha_atual = qual_linha(ultimo_num)

    # Prepara os alertas se houver atraso >= 5
    for i, atraso in enumerate([atrasos["d1"], atrasos["d2"], atrasos["d3"]], start=1):
        if atraso >= 5 and duzia_atual != 0:
            alertas_verdes.append(f"🚨 APOSTE: {i}ª Dúzia + {duzia_atual}ª Dúzia (Última que saiu). A {i}ª Dúzia está com {atraso} atrasos!")

    for i, atraso in enumerate([atrasos["l1"], atrasos["l2"], atrasos["l3"]], start=1):
        if atraso >= 5 and linha_atual != 0:
            alertas_verdes.append(f"🚨 APOSTE: {i}ª Linha + {linha_atual}ª Linha (Última que saiu). A {i}ª Linha está com {atraso} atrasos!")

# 4. EXIBINDO OS ALERTAS NO TOPO (st.success)
if alertas_verdes:
    for alerta in alertas_verdes:
        st.success(alerta)
elif len(st.session_state.historico) > 0:
    st.info("Monitorando padrões... Registre o próximo número.")

# 5. ÁREA DE ENTRADA RÁPIDA (Com os botões alinhados)
col_input, col_btn, col_limpar = st.columns([2, 1, 1])
with col_input:
    numero_sorteado = st.number_input("Digite o número (0 a 36):", min_value=0, max_value=36, step=1)
with col_btn:
    st.write("") # Empurra o botão para alinhar com o campo de texto
    st.write("")
    if st.button("Registrar"):
        st.session_state.historico.append(numero_sorteado)
        st.rerun()
with col_limpar:
    st.write("")
    st.write("")
    if st.button("🗑️ Limpar"):
        st.session_state.historico = []
        st.rerun()

st.write("---")

# 6. PAINEL DE ATRASOS COMPACTO E HISTÓRICO
if len(st.session_state.historico) > 0:
    st.write("**Atrasos Atuais:**")
    
    # Usando texto simples formatado para ocupar menos espaço
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        - 1ª Dúzia: **{atrasos['d1']}**
        - 2ª Dúzia: **{atrasos['d2']}**
        - 3ª Dúzia: **{atrasos['d3']}**
        """)
    with col2:
        st.markdown(f"""
        - 1ª Linha: **{atrasos['l1']}**
        - 2ª Linha: **{atrasos['l2']}**
        - 3ª Linha: **{atrasos['l3']}**
        """)
        
    st.caption(f"Últimos números registrados: {st.session_state.historico}")
else:
    st.info("Nenhum número registrado no momento.")
