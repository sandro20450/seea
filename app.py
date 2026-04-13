import streamlit as st
import pandas as pd
from datetime import date

# =============================================================================
# --- 1. CONFIGURAÇÕES GERAIS E VISUAIS ---
# =============================================================================
st.set_page_config(page_title="Portal do Aluno - Projeto Saber", page_icon="🎓", layout="wide")

# CSS para criar os "Botões Lúdicos" e Painéis
st.markdown("""
<style>
    .stApp { background-color: #f4f6f9; color: #333; }
    h1, h2, h3 { color: #1e3d59 !important; font-family: 'Arial', sans-serif; }
    
    /* Cards Lúdicos do Menu Principal */
    .card-menu {
        background-color: #ffffff;
        border-radius: 15px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        transition: transform 0.3s ease;
        border-bottom: 5px solid #007bff;
        margin-bottom: 20px;
    }
    .card-menu:hover { transform: translateY(-5px); }
    .icon-ludico { font-size: 3.5em; margin-bottom: 10px; }
    .titulo-card { font-size: 1.2em; font-weight: bold; color: #1e3d59; }
    
    /* Estilo para Área Restrita */
    .painel-restrito {
        background-color: #e9ecef;
        border-radius: 10px;
        padding: 20px;
        border-left: 5px solid #28a745;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# --- 2. SISTEMA DE AUTENTICAÇÃO (MOCKUP INICIAL) ---
# =============================================================================
# Aqui conectaremos ao Google Sheets depois. Por enquanto, dados de teste.
MOCK_USERS = {
    "pai123": {"senha": "123", "perfil": "responsavel", "nome": "João (Pai do Pedrinho)"},
    "prof456": {"senha": "456", "perfil": "professor", "nome": "Profª Maria (Matemática)"},
    "admin": {"senha": "admin", "perfil": "diretoria", "nome": "Diretor Carlos"}
}

if "usuario_logado" not in st.session_state:
    st.session_state.usuario_logado = None
if "perfil_logado" not in st.session_state:
    st.session_state.perfil_logado = None

def fazer_login(usuario, senha):
    if usuario in MOCK_USERS and MOCK_USERS[usuario]["senha"] == senha:
        st.session_state.usuario_logado = MOCK_USERS[usuario]["nome"]
        st.session_state.perfil_logado = MOCK_USERS[usuario]["perfil"]
        st.success("Acesso Concedido!")
        st.rerun()
    else:
        st.error("Usuário ou senha incorretos!")

def fazer_logout():
    st.session_state.usuario_logado = None
    st.session_state.perfil_logado = None
    st.rerun()

# =============================================================================
# --- 3. BARRA LATERAL (LOGIN / MENU) ---
# =============================================================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3106/3106194.png", width=100) # Ícone de escola genérico
    st.markdown("### 🏫 Escola Projeto Saber")
    st.markdown("---")
    
    if st.session_state.usuario_logado is None:
        st.markdown("### 🔐 Portal de Acesso")
        user_input = st.text_input("Usuário (RA ou Matrícula)")
        pass_input = st.text_input("Senha", type="password")
        if st.button("Entrar", use_container_width=True):
            fazer_login(user_input, pass_input)
            
        st.markdown("---")
        st.info("💡 **Dica de Teste:**\n\n- Pai: `pai123` / Senha: `123`\n- Prof: `prof456` / Senha: `456`\n- Dir: `admin` / Senha: `admin`")
    else:
        st.success(f"Olá, {st.session_state.usuario_logado}")
        st.info(f"Perfil: {st.session_state.perfil_logado.upper()}")
        if st.button("🚪 Sair (Logout)", use_container_width=True):
            fazer_logout()

# =============================================================================
# --- 4. TELA PRINCIPAL (FRONT-END PÚBLICO E PRIVADO) ---
# =============================================================================

# SE NINGUÉM ESTIVER LOGADO -> MOSTRA A VITRINE DA ESCOLA (Front-end Lúdico)
if st.session_state.usuario_logado is None:
    st.markdown("<h1 style='text-align: center;'>Bem-vindo à Escola Projeto Saber! 🎒</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #666;'>Educação de excelência para o futuro do seu filho. Selecione uma opção abaixo:</p><br>", unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="card-menu" style="border-color: #ff9900;">
            <div class="icon-ludico">📝</div>
            <div class="titulo-card">Matrículas 2026</div>
            <p style="font-size:0.9em; color:#666;">Garanta a vaga do seu filho hoje.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Ver Vagas", key="btn_mat"): st.toast("Redirecionando para formulário de matrícula...")
        
    with col2:
        st.markdown("""
        <div class="card-menu" style="border-color: #28a745;">
            <div class="icon-ludico">💰</div>
            <div class="titulo-card">Financeiro</div>
            <p style="font-size:0.9em; color:#666;">Mensalidades e materiais.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Ver Planos", key="btn_fin"): st.toast("Área de mensalidades em construção.")

    with col3:
        st.markdown("""
        <div class="card-menu" style="border-color: #dc3545;">
            <div class="icon-ludico">📍</div>
            <div class="titulo-card">Localização</div>
            <p style="font-size:0.9em; color:#666;">Nossa estrutura física.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Ver Mapa", key="btn_loc"): st.toast("Abrindo Google Maps...")

    with col4:
        st.markdown("""
        <div class="card-menu" style="border-color: #17a2b8;">
            <div class="icon-ludico">📞</div>
            <div class="titulo-card">Contatos</div>
            <p style="font-size:0.9em; color:#666;">Fale com a secretaria.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Falar no Zap", key="btn_zap"): st.toast("Abrindo WhatsApp da Escola...")

# SE ESTIVER LOGADO COMO PAI/RESPONSÁVEL
elif st.session_state.perfil_logado == "responsavel":
    st.header("🎓 Painel do Aluno")
    st.markdown('<div class="painel-restrito">Aqui você acompanha o desenvolvimento do Pedrinho.</div><br>', unsafe_allow_html=True)
    
    tab_notas, tab_avisos = st.tabs(["📝 Boletim Escolar", "🔔 Mural de Avisos"])
    with tab_notas:
        st.subheader("Notas do 1º Bimestre")
        # Exemplo visual de tabela de notas
        df_notas = pd.DataFrame({
            "Disciplina": ["Matemática", "Português", "História", "Ciências"],
            "Nota": [8.5, 9.0, 7.5, 10.0],
            "Faltas": [2, 0, 1, 0],
            "Situação": ["🟢 Aprovado", "🟢 Aprovado", "🟡 Em Exame", "🟢 Aprovado"]
        })
        st.dataframe(df_notas, use_container_width=True, hide_index=True)
    with tab_avisos:
        st.info("📅 **Reunião de Pais:** Dia 20/04 às 19h no auditório principal.")
        st.warning("⚽ **Jogos Escolares:** Inscrições abertas para o time de Futsal até sexta-feira.")

# SE ESTIVER LOGADO COMO PROFESSOR
elif st.session_state.perfil_logado == "professor":
    st.header("🍎 Diário de Classe - Professor")
    st.markdown('<div class="painel-restrito" style="border-color: #ff9900;">Lançamento de notas e presença das suas turmas.</div><br>', unsafe_allow_html=True)
    
    st.selectbox("Selecione a Turma:", ["6º Ano A", "7º Ano B", "8º Ano A"])
    st.selectbox("Bimestre:", ["1º Bimestre", "2º Bimestre", "3º Bimestre", "4º Bimestre"])
    
    st.markdown("### Lançar Notas:")
    col_a, col_b = st.columns([3, 1])
    with col_a: st.text_input("Nome do Aluno", "Pedrinho da Silva")
    with col_b: st.number_input("Nota", min_value=0.0, max_value=10.0, value=0.0)
    st.button("💾 Salvar Nota", type="primary")

# SE ESTIVER LOGADO COMO DIRETORIA (ADMIN)
elif st.session_state.perfil_logado == "diretoria":
    st.header("👑 Painel de Controle - Diretoria")
    st.markdown('<div class="painel-restrito" style="border-color: #dc3545;">Gestão total do sistema e banco de dados.</div><br>', unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Total de Alunos", "450", "+12 matrículas")
    c2.metric("Professores Ativos", "25", "100% presentes")
    c3.metric("Mensalidades Atrasadas", "5", "-2 regularizadas")
    
    st.markdown("---")
    st.subheader("Gerenciar Cadastros")
    st.selectbox("O que deseja gerenciar?", ["🏫 Alunos", "🍎 Professores", "💰 Financeiro"])
    st.button("➕ Adicionar Novo Registro")
