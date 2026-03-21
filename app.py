import streamlit as st
import streamlit.components.v1 as components

st.title("🎯 Roleta Tracker - 12 Segundos")

# 1. MEMÓRIA RÁPIDA E CHAVE DE LIMPEZA
if 'historico' not in st.session_state:
    st.session_state.historico = []
if 'chave_input' not in st.session_state:
    st.session_state.chave_input = 0

def registrar_numero():
    nome_da_chave = f"num_{st.session_state.chave_input}"
    num = st.session_state[nome_da_chave]
    if num is not None:
        st.session_state.historico.append(int(num))
        st.session_state.chave_input += 1 

# 2. FUNÇÕES DE MAPEAMENTO (Apenas IPT e 123 ativas)
def qual_ipt(n):
    if n == 0: return '0'
    if 1 <= n <= 24:
        return 'I' if n % 2 != 0 else 'P'
    if 25 <= n <= 36:
        return 'T'

def qual_123(n):
    if n == 0: return '0'
    if n in [1, 7, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]: return '1'
    if n in [2, 8, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29]: return '2'
    if n in [3, 4, 5, 6, 9, 30, 31, 32, 33, 34, 35, 36]: return '3'

# --- ABASTECIMENTO EM LOTE ---
with st.expander("📥 Inserir Histórico Inicial (Lote)"):
    lote_input = st.text_input("Cole os números separados por vírgula:")
    if st.button("Carregar Histórico"):
        try:
            st.session_state.historico = [int(x.strip()) for x in lote_input.split(',') if x.strip().isdigit()][::-1]
            st.session_state.chave_input += 1
            st.success(f"✅ {len(st.session_state.historico)} números carregados com sucesso!")
        except Exception as e:
            st.error("Erro ao carregar. Certifique-se de usar apenas números e vírgulas.")
st.write("---")

# 3. O CÉREBRO E OS ALERTAS CRUZADOS
alertas = []

if len(st.session_state.historico) > 0:
    # Filtra os zeros (o "fantasma" que não interfere na regra)
    numeros_validos = [n for n in st.session_state.historico if n != 0]
    
    # Precisamos de pelo menos 2 números não-zero para cruzar a estratégia
    if len(numeros_validos) >= 2:
        # Pega os dois últimos giros válidos
        n1 = numeros_validos[-2] # Penúltimo
        n2 = numeros_validos[-1] # Último (mais recente)
        
        ipt1, ipt2 = qual_ipt(n1), qual_ipt(n2)
        g1_1, g1_2 = qual_123(n1), qual_123(n2)
        
        # REGRA A: IPT igual E 123 diferente -> Alerta IPT ⚡
        if ipt1 == ipt2 and g1_1 != g1_2:
            if ipt2 == 'I':
                alertas.append(f"⚡ **CRUZAMENTO IPT:** ({n1} e {n2}) repetiram o Grupo **I**, mas espalharam no 123. APOSTE: **P** + **T**.")
            elif ipt2 == 'P':
                alertas.append(f"⚡ **CRUZAMENTO IPT:** ({n1} e {n2}) repetiram o Grupo **P**, mas espalharam no 123. APOSTE: **I** + **T**.")
            elif ipt2 == 'T':
                alertas.append(f"⚡ **CRUZAMENTO IPT:** ({n1} e {n2}) repetiram o Grupo **T**, mas espalharam no 123. APOSTE: **I** + **P**.")

        # REGRA B: 123 igual E IPT diferente -> Alerta 123 🔥
        elif g1_1 == g1_2 and ipt1 != ipt2:
            if g1_2 == '1':
                alertas.append(f"🔥 **CRUZAMENTO 123:** ({n1} e {n2}) repetiram o Conjunto **1**, mas espalharam no IPT. APOSTE: **2** + **3**.")
            elif g1_2 == '2':
                alertas.append(f"🔥 **CRUZAMENTO 123:** ({n1} e {n2}) repetiram o Conjunto **2**, mas espalharam no IPT. APOSTE: **1** + **3**.")
            elif g1_2 == '3':
                alertas.append(f"🔥 **CRUZAMENTO 123:** ({n1} e {n2}) repetiram o Conjunto **3**, mas espalharam no IPT. APOSTE: **1** + **2**.")

# 4. EXIBINDO OS ALERTAS
if alertas:
    for alerta in alertas:
        st.success(alerta) # Usei a cor Verde (success) para ficar bem destacado na hora de apostar
else:
    if len(st.session_state.historico) > 0:
        st.info("Aguardando cruzamento de estratégias... Digite o próximo número.")

# 5. ÁREA DE ENTRADA
st.write("**Digite o número e aperte ENTER (0 a 36):**")
col_input, col_limpar = st.columns([3, 1])

with col_input:
    st.number_input(
        "Digite", min_value=0, max_value=36, step=1, value=None, 
        key=f"num_{st.session_state.chave_input}", 
        on_change=registrar_numero, label_visibility="collapsed"
    )

with col_limpar:
    if st.button("🗑️ Limpar Tudo"):
        st.session_state.historico = []
        st.session_state.chave_input += 1
        st.rerun()

# --- TRUQUE DO FOCO AUTOMÁTICO ---
components.html(
    f"""
    <script id="foco_{st.session_state.chave_input}">
    setTimeout(function() {{
        const doc = window.parent.document;
        const inputs = doc.querySelectorAll('input[type="number"]');
        if (inputs.length > 0) {{
            inputs[0].focus();
        }}
    }}, 100);
    </script>
    """,
    height=0, width=0
)
# ---------------------------------------------

st.write("---")

# 6. HISTÓRICO VISUAL (Novo formato compacto solicitado)
if len(st.session_state.historico) > 0:
    historico_visual = []
    
    # Lê de trás para frente (Mais recentes primeiro)
    for n in reversed(st.session_state.historico):
        if n == 0:
            historico_visual.append("**0**")
        else:
            grp_ipt = qual_ipt(n)
            grp_123 = qual_123(n)
            # Novo formato: (15:I-1)
            historico_visual.append(f"**({n}:{grp_ipt}-{grp_123})**")
            
    texto_historico = " - ".join(historico_visual)
    
    st.write("**Últimos giros (Mais recentes primeiro):**")
    st.markdown(texto_historico)
else:
    st.info("Nenhum número registrado no momento.")
