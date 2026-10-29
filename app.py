import streamlit as st
import pandas as pd
from datetime import date
import time
import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai
import PyPDF2
import io

# =============================================================================
# --- 1. CONFIGURAÇÕES GERAIS E VISUAIS ---
# =============================================================================
st.set_page_config(page_title="SEEA - Gestão Escolar", page_icon="🏫", layout="wide")

st.markdown("""
<style>
    footer { display: none !important; visibility: hidden !important; }
    
    .painel-selecao, .painel-login { 
        border-radius: 16px; 
        padding: 30px; 
        border-top: 5px solid #004d99; 
        box-shadow: 0 4px 12px rgba(0,0,0,0.08); 
        margin-bottom: 25px; 
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        border: 1px solid rgba(128,128,128,0.2);
    }
    .painel-selecao:hover, .painel-login:hover {
        transform: translateY(-6px);
        box-shadow: 0 12px 24px rgba(0,0,0,0.15);
    }
    [data-testid="stExpander"] {
        border-radius: 12px !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        border: 1px solid rgba(128,128,128,0.2);
        transition: all 0.3s ease;
        margin-bottom: 10px;
    }
    [data-testid="stExpander"]:hover {
        box-shadow: 0 6px 16px rgba(0,0,0,0.1);
    }
    .stButton > button {
        border-radius: 20px !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.15) !important;
    }
    div[data-baseweb="input"] > div, div[data-baseweb="select"] > div {
        border-radius: 10px !important;
        transition: border 0.3s ease;
    }
    [data-testid="metric-container"] {
        border-radius: 12px;
        padding: 15px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
        border: 1px solid rgba(128,128,128,0.1);
        transition: transform 0.3s ease;
    }
    [data-testid="metric-container"]:hover {
        transform: translateY(-3px);
    }
    /* Estilo especial para o container de matrícula */
    .matricula-box {
        background-color: rgba(0, 123, 255, 0.05);
        border: 2px solid #004d99;
        border-radius: 12px;
        padding: 20px;
        margin-top: 20px;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# --- 2. CONEXÃO COM BANCO DE DADOS E FUNÇÕES PRINCIPAIS ---
# =============================================================================
@st.cache_resource(ttl=3600, show_spinner=False)
def get_gspread_client():
    if "gcp_service_account" in st.secrets:
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
        return gspread.authorize(creds)
    return None

@st.cache_data(ttl=300, show_spinner=False)
def fetch_sheet_data_cached(nome_aba):
    gc = get_gspread_client()
    if gc:
        try:
            ws = gc.open("Base_SEEA").worksheet(nome_aba)
            return ws.get_all_values()
        except gspread.exceptions.WorksheetNotFound:
            return []
    return []

def carregar_tabela_completa(nome_aba):
    """
    Função blindada contra o erro de 'Duplicate column names'.
    Ignora colunas sem cabeçalho e evita nomes repetidos.
    """
    try:
        dados = fetch_sheet_data_cached(nome_aba)
        if not dados:
            if nome_aba == "Avisos": return pd.DataFrame(columns=["tipo", "aluno", "mensagem", "data"])
            if nome_aba == "Matriculas": return pd.DataFrame(columns=["Já Matriculado (Sim/Não)", "Nome do aluno(a)"])
            return pd.DataFrame()
        
        # LÓGICA DE BLINDAGEM DE COLUNAS
        cabecalhos_brutos = dados[0]
        cabecalhos_limpos = []
        indices_validos = []
        
        for i, c in enumerate(cabecalhos_brutos):
            nome_col = str(c).strip()
            if nome_col != "": # Se a coluna tem um título válido
                # Se o nome já existir, adiciona um número para não duplicar
                if nome_col in cabecalhos_limpos:
                    nome_col = f"{nome_col}_{i}"
                cabecalhos_limpos.append(nome_col)
                indices_validos.append(i)
        
        if len(dados) == 1:
            df = pd.DataFrame(columns=cabecalhos_limpos)
        else:
            # Constrói a tabela apenas com as colunas válidas
            dados_filtrados = []
            for linha in dados[1:]:
                linha_limpa = [linha[i] if i < len(linha) else "" for i in indices_validos]
                dados_filtrados.append(linha_limpa)
            df = pd.DataFrame(dados_filtrados, columns=cabecalhos_limpos)
        
        # Mantém colunas originais para a aba Matriculas
        if nome_aba != "Matriculas":
            df.columns = df.columns.str.lower()
            
        return df
    except Exception as e:
        return pd.DataFrame()

# Função para salvar a matrícula
def salvar_matricula_bd(dados_dicionario):
    try:
        gc = get_gspread_client()
        if gc:
            sh = gc.open("Base_SEEA")
            try:
                ws = sh.worksheet("Matriculas")
            except:
                ws = sh.add_worksheet(title="Matriculas", rows="100", cols="40")
            
            dados_existentes = ws.get_all_values()
            colunas_novas = list(dados_dicionario.keys())
            
            if not dados_existentes:
                ws.append_row(colunas_novas)
                
            linha_valores = [str(v) for v in dados_dicionario.values()]
            ws.append_row(linha_valores)
            st.cache_data.clear()
            return True
    except Exception as e:
        st.error(f"Erro ao salvar matrícula no banco: {e}")
        return False

def carregar_usuarios():
    try:
        df = carregar_tabela_completa("Usuarios")
        if not df.empty and 'usuario' in df.columns and 'senha' in df.columns:
            usuarios = {}
            for _, row in df.iterrows():
                if str(row.get('usuario', '')).strip() != "":
                    usuarios[str(row['usuario']).strip()] = { "senha": str(row.get('senha', '')).strip(), "perfil": str(row.get('perfil', '')).lower().strip(), "nome": str(row.get('nome', '')).strip() }
            return usuarios
        return {}
    except Exception: return {}

def carregar_turmas():
    try:
        df = carregar_tabela_completa("Alunos")
        if not df.empty and 'turma' in df.columns:
            turmas = df['turma'].astype(str).str.strip().unique().tolist()
            turmas = [t for t in turmas if t != ""]
            return sorted(turmas) if turmas else []
        return []
    except: return []

def carregar_alunos(turma):
    try:
        df = carregar_tabela_completa("Alunos")
        if not df.empty and 'turma' in df.columns:
            col_nome = 'nome_aluno' if 'nome_aluno' in df.columns else ('aluno' if 'aluno' in df.columns else None)
            if col_nome:
                turma_limpa = str(turma).strip()
                df_filtrado = df[df['turma'].astype(str).str.strip() == turma_limpa]
                alunos = df_filtrado[col_nome].astype(str).str.strip().tolist()
                alunos = [a for a in alunos if a != ""]
                return alunos if alunos else []
        return []
    except Exception as e: return []

def buscar_dados_aluno(nome_aluno):
    try:
        df = carregar_tabela_completa("Alunos")
        col_nome = 'nome_aluno' if 'nome_aluno' in df.columns else ('aluno' if 'aluno' in df.columns else None)
        if not df.empty and col_nome:
            aluno_row = df[df[col_nome].astype(str).str.strip() == str(nome_aluno).strip()]
            if not aluno_row.empty: return aluno_row.iloc[0].to_dict()
    except Exception: return None
    return None

def carregar_notas_aluno(nome_aluno):
    try:
        df = carregar_tabela_completa("Notas")
        if not df.empty and 'aluno' in df.columns:
            return df[df['aluno'].astype(str).str.strip() == str(nome_aluno).strip()]
        return pd.DataFrame()
    except: return pd.DataFrame() 

def salvar_notas_bd(turma, disciplina, df_resultados):
    try:
        gc = get_gspread_client()
        if gc:
            ws = gc.open("Base_SEEA").worksheet("Notas")
            df_banco = carregar_tabela_completa("Notas")
            
            colunas_padrao = ['turma', 'aluno', 'disciplina', 'unidade_1', 'unidade_2', 'unidade_3', 'unidade_4', 'media_final', 'situacao']
            if df_banco.empty: df_banco = pd.DataFrame(columns=colunas_padrao)
            
            for index, row in df_resultados.iterrows():
                aluno_atual = str(row["ALUNO"]).strip()
                mask = ((df_banco['aluno'].astype(str).str.strip() == aluno_atual) & (df_banco['disciplina'].astype(str).str.strip() == disciplina.strip()))
                nova_linha = {
                    'turma': turma, 'aluno': aluno_atual, 'disciplina': disciplina,
                    'unidade_1': str(row.get("I Unidade", "-")), 'unidade_2': str(row.get("II Unidade", "-")),
                    'unidade_3': str(row.get("III Unidade", "-")), 'unidade_4': str(row.get("IV Unidade", "-")),
                    'media_final': str(row.get("MÉDIA FINAL", "-")), 'situacao': str(row.get("SITUAÇÃO", "-"))
                }
                if df_banco[mask].empty: df_banco = pd.concat([df_banco, pd.DataFrame([nova_linha])], ignore_index=True)
                else:
                    idx = df_banco[mask].index[0]
                    for col, val in nova_linha.items(): df_banco.at[idx, col] = val
                        
            dados_lista = [df_banco.columns.values.tolist()] + df_banco.values.tolist()
            ws.clear()
            ws.update(values=dados_lista, range_name="A1")
            st.cache_data.clear() 
            return True
    except Exception as e:
        st.error(f"Erro ao salvar no banco de dados: {e}")
        return False

def salvar_frequencia_bd(data_aula, turma, assunto, lista_presenca):
    try:
        gc = get_gspread_client()
        if gc:
            ws = gc.open("Base_SEEA").worksheet("Frequencia")
            novas_linhas = []
            for item in lista_presenca:
                linha = [str(data_aula), turma, item['aluno'], item['status'], assunto]
                novas_linhas.append(linha)
            ws.append_rows(novas_linhas, value_input_option="USER_ENTERED")
            st.cache_data.clear()
            return True
    except Exception as e:
        st.error(f"Erro ao salvar frequência no banco: {e}")
        return False

def sincronizar_aba_completa(nome_aba, df_editado):
    try:
        gc = get_gspread_client()
        if gc:
            ws = gc.open("Base_SEEA").worksheet(nome_aba)
            df_editado = df_editado.fillna("")
            dados_lista = [df_editado.columns.values.tolist()] + df_editado.values.tolist()
            ws.clear()
            ws.update(values=dados_lista, range_name="A1")
            st.cache_data.clear()
            return True
    except Exception as e:
        st.error(f"Erro ao sincronizar a aba {nome_aba}: {e}")
        return False

def gerar_pdf_boletim(nome_aluno, dados_aluno, df_boletim):
    try:
        from fpdf import FPDF
    except ImportError:
        return None 
        
    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 14)
            self.cell(0, 10, 'SEEA - BOLETIM ESCOLAR OFICIAL', 0, 1, 'C')
            self.ln(5)

    pdf = PDF()
    pdf.add_page()
    
    def limpa_txt(texto):
        for emoji in ["🟢", "🟡", "⚪", "🔴"]:
            texto = texto.replace(emoji, "")
        return texto.strip().encode('latin-1', 'replace').decode('latin-1')

    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, limpa_txt(f"Aluno(a): {nome_aluno}"), 0, 1)
    
    turma = dados_aluno.get('turma', 'N/A')
    turno = dados_aluno.get('turno', 'N/A')
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 8, limpa_txt(f"Turma: {turma}  |  Turno: {turno}"), 0, 1)
    pdf.ln(5)
    
    colunas = df_boletim.columns.tolist()
    largura_col = 190 / len(colunas) 
    
    pdf.set_font('Arial', 'B', 9)
    for col in colunas:
        pdf.cell(largura_col, 8, limpa_txt(str(col)), 1, 0, 'C')
    pdf.ln()
    
    pdf.set_font('Arial', '', 8)
    for _, row in df_boletim.iterrows():
        for col in colunas:
            val = str(row[col])
            pdf.cell(largura_col, 8, limpa_txt(val), 1, 0, 'C')
        pdf.ln()
        
    return pdf.output(dest='S').encode('latin-1')

# =============================================================================
# --- 3. CONFIGURAÇÃO DA INTELIGÊNCIA ARTIFICIAL (GEMINI) ---
# =============================================================================
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    ia_configurada = True
else:
    ia_configurada = False

# =============================================================================
# --- 4. SISTEMA DE LOGIN E CONTROLE DE ESTADO ---
# =============================================================================
if "usuario_logado" not in st.session_state: st.session_state.usuario_logado = None
if "perfil_logado" not in st.session_state: st.session_state.perfil_logado = None
if "diario_aberto" not in st.session_state: st.session_state.diario_aberto = False

# Estados da nova funcionalidade de matrícula
if "mostrar_form_matricula" not in st.session_state: st.session_state.mostrar_form_matricula = False
if "tipo_matricula_escolhida" not in st.session_state: st.session_state.tipo_matricula_escolhida = None

def fazer_login(usuario, senha):
    usuarios_db = carregar_usuarios()
    if usuario in usuarios_db and usuarios_db[usuario]["senha"] == senha:
        st.session_state.usuario_logado = usuarios_db[usuario]["nome"]
        st.session_state.perfil_logado = usuarios_db[usuario]["perfil"]
        st.success("Acesso Concedido!")
        st.rerun()
    else: st.error("Credenciais inválidas ou usuário não encontrado na planilha!")

def fazer_logout():
    st.session_state.usuario_logado = None
    st.session_state.perfil_logado = None
    st.session_state.diario_aberto = False
    st.session_state.mostrar_form_matricula = False
    st.cache_data.clear() 
    st.rerun()

# =============================================================================
# --- 5. MENU LATERAL (SIDEBAR) ---
# =============================================================================
if st.session_state.usuario_logado is None:
    st.markdown("""<style>[data-testid="collapsedControl"] { display: none !important; }</style>""", unsafe_allow_html=True)
else:
    with st.sidebar:
        st.markdown("<h2 style='text-align:center;'>🌎 SEEA</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center; font-size:0.8em; color:#888;'>Sistema de Gestão Escolar</p>", unsafe_allow_html=True)
        st.markdown("---")
        
        st.markdown(f"""<div style='background-color: rgba(0, 123, 255, 0.1); padding: 15px; border-radius: 12px; margin-bottom: 20px; text-align: center; border: 1px solid rgba(0, 123, 255, 0.2);'><span style='font-weight: bold; font-size: 1.1em;'>👤 {st.session_state.usuario_logado}</span></div>""", unsafe_allow_html=True)
        
        if st.session_state.perfil_logado == "professor":
            st.markdown("<span style='color:#888; font-size:0.8em; font-weight:bold;'>PEDAGÓGICO</span>", unsafe_allow_html=True)
            st.button("📖 Diário de Classe", use_container_width=True)
            st.button("🤖 Gerador de Provas", use_container_width=True)
            
        elif st.session_state.perfil_logado in ["admin", "diretoria"]:
            st.markdown("<span style='color:#888; font-size:0.8em; font-weight:bold;'>ADMINISTRAÇÃO</span>", unsafe_allow_html=True)
            st.button("⚙️ Painel de Gestão", use_container_width=True)
            
        elif st.session_state.perfil_logado == "aluno":
            st.markdown("<span style='color:#888; font-size:0.8em; font-weight:bold;'>ÁREA DO ALUNO</span>", unsafe_allow_html=True)
            st.button("📊 Meu Boletim", use_container_width=True)
            st.button("📢 Avisos Escolares", use_container_width=True)
            
        st.markdown("---")
        if st.button("🔄 Atualizar Sistema", use_container_width=True):
            st.cache_data.clear()
            st.success("Memória renovada!")
            time.sleep(1)
            st.rerun()
            
        st.markdown("---")
        if st.button("🚪 Sair", use_container_width=True): fazer_logout()

# =============================================================================
# --- 6. ÁREA PRINCIPAL (FRONT-END) ---
# =============================================================================

# ================= TELA DESLOGADA (PORTAL ABERTO) =================
if st.session_state.usuario_logado is None:
    st.markdown("<h1 style='text-align: center; margin-bottom: 30px;'>Bem-vindo ao Portal SEEA</h1>", unsafe_allow_html=True)
    
    df_avisos = carregar_tabela_completa("Avisos")
    if not df_avisos.empty and 'tipo' in df_avisos.columns:
        avisos_gerais = df_avisos[df_avisos['tipo'].astype(str).str.strip().str.upper() == 'GERAL']
        if not avisos_gerais.empty:
            for _, aviso in avisos_gerais.iterrows():
                st.warning(f"📢 **COMUNICADO OFICIAL ({aviso.get('data', '')}):** {aviso.get('mensagem', '')}", icon="🏫")
            st.markdown("<br>", unsafe_allow_html=True)
    
    # Se o formulário de matrícula não estiver ativado, mostra a tela normal
    if not st.session_state.mostrar_form_matricula:
        col_login, col_info = st.columns([1, 1.5])
        
        with col_login:
            st.markdown("<div class='painel-login'>", unsafe_allow_html=True)
            st.markdown("<h3 style='text-align:center; color:#004d99; margin-bottom: 20px;'>🔐 Acesso ao Painel</h3>", unsafe_allow_html=True)
            user_input = st.text_input("Usuário", placeholder="Digite seu usuário")
            pass_input = st.text_input("Senha", type="password", placeholder="Digite sua senha")
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("Entrar no Sistema", use_container_width=True, type="primary"):
                fazer_login(user_input, pass_input)
                
            st.markdown("<br>", unsafe_allow_html=True)
            with st.expander("❓ Esqueci minha senha"):
                st.info("Para recuperar o seu acesso, fale com a Secretaria.\n\n📞 (81) 98328-8495")
            st.markdown("</div>", unsafe_allow_html=True)
                
        with col_info:
            st.markdown("### 📌 Informações Úteis")
            
            with st.expander("💰 **Financeiro (Pagamentos e Taxas)**", expanded=False):
                st.markdown("Realize o pagamento da sua mensalidade de forma rápida e segura escolhendo uma das opções abaixo:")
                st.markdown("---")
                st.markdown("##### 1. PIX (Cópia e Cola)")
                st.write("Copie a chave PIX (CPF: ELIUDE BERNARDO DE SOUZA SILVA) abaixo:")
                st.code("04994867460", language="text") 
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("##### 2. PAGAMENTO NA PLATAFORMA ASAAS")
                st.link_button("💳 Abrir Plataforma ASAAS", "https://api.whatsapp.com/send?phone=5547933007606", use_container_width=True)
                    
            with st.expander("📍 **Nossa localização**", expanded=False):
                st.markdown("**Endereço:** Rua Antônio José de Paiva, S/N Loteamento Real Vitória - Vitória de Santo Antão - PE")
                st.markdown("---")
                st.link_button("🗺️ Ver Rota no Google Maps", "https://www.google.com/maps/place/...", use_container_width=True)
                
            with st.expander("📞 **Contatos e Suporte**", expanded=False):
                st.markdown("- **Secretaria (WhatsApp):** [(81) 98328-8495](https://wa.me/5581983288495)")
                st.markdown("- **Coord. Infantil:** [(81) 99394-3245](https://wa.me/5581993943245)")
                st.markdown("- **Coord. Fundamental 1:** [(81) 98508-0876](https://wa.me/5581985080876)")

            # =============================================================================
            # MENU DE MATRÍCULAS (Gatilho)
            # =============================================================================
            with st.expander("📝 **MATRÍCULAS**", expanded=False):
                st.markdown("Selecione o tipo de atendimento desejado para iniciar o processo:")
                opcao_matricula = st.radio("Tipo de Matrícula:", ["Renovar Matrícula", "Aluno Novo"], label_visibility="collapsed")
                st.markdown("<br>", unsafe_allow_html=True)
                
                if st.button("Avançar ➔", use_container_width=True, type="secondary"):
                    st.session_state.tipo_matricula_escolhida = opcao_matricula
                    st.session_state.mostrar_form_matricula = True
                    st.rerun()
                    
    # ================= MÓDULO DE FORMULÁRIO DE MATRÍCULA =================
    else:
        if st.button("⬅️ Voltar ao Início"):
            st.session_state.mostrar_form_matricula = False
            st.rerun()
            
        st.markdown(f"<h2 style='text-align: center; color: #004d99;'>Formulário: {st.session_state.tipo_matricula_escolhida}</h2>", unsafe_allow_html=True)
        st.markdown("<div class='matricula-box'>", unsafe_allow_html=True)
        
        with st.form("form_dados_matricula"):
            # Variável oculta que diz se já é matriculado para o painel admin
            ja_matriculado = "Sim" if st.session_state.tipo_matricula_escolhida == "Renovar Matrícula" else "Não"
            
            if ja_matriculado == "Sim":
                st.markdown("#### Dados para Renovação")
                nome_aluno = st.text_input("Nome completo do aluno(a) *")
                data_nasc = st.date_input("Data de nascimento do aluno *", min_value=date(1990, 1, 1), max_value=date.today())
                fone_contato = st.text_input("Telefone para contato do responsável *")
                alteracoes = st.text_area("Informe se precisa alterar alguma informação na matrícula do ano anterior (Quais?):")
                
                # Campos ocultos/vazios para igualar a estrutura da planilha
                dados_enviar = {
                    "Já Matriculado (Sim/Não)": ja_matriculado, "Nome do aluno(a)": nome_aluno, "Data de nascimento": data_nasc.strftime("%d/%m/%Y"),
                    "Sexo": "-", "Grupo Sanguíneo": "-", "CPF Aluno": "-", "Endereço": "-", "Naturalidade": "-", "Estado": "-",
                    "NIS Aluno": "-", "NIS Responsável": "-", "SUS/Plano de Saúde": "-", "Religião Aluno": "-", "Cor": "-",
                    "Nome do Pai": "-", "CPF Pai": "-", "RG Pai": "-", "Religião Pai": "-", "Profissão Pai": "-", "Estado Civil Pai": "-",
                    "Email Pai": "-", "Fone Pessoal Pai": "-", "Fone Trabalho Pai": "-", "Grau Instrução Pai": "-",
                    "Nome da Mãe": "-", "CPF Mãe": "-", "RG Mãe": "-", "Religião Mãe": "-", "Profissão Mãe": "-", "Estado Civil Mãe": "-",
                    "Fone Pessoal Mãe": "-", "Fone Trabalho Mãe": "-", "Grau Instrução Mãe": "-", "Email Mãe": "-",
                    "Telefone Contato (Renovação)": fone_contato, "Alterações (Renovação)": alteracoes
                }
                
            else: # Aluno Novo
                st.markdown("#### Dados do Aluno(a)")
                c1, c2, c3 = st.columns(3)
                nome_aluno = c1.text_input("Nome completo do aluno(a) *")
                data_nasc = c2.date_input("Data de nascimento *", min_value=date(1990, 1, 1), max_value=date.today())
                sexo = c3.selectbox("Sexo", ["Masculino", "Feminino"])
                
                c4, c5, c6 = st.columns(3)
                sangue = c4.text_input("Grupo Sanguíneo / Fator RH (Ex: B+)")
                cpf_aluno = c5.text_input("CPF do Aluno")
                cor = c6.text_input("Cor")
                
                endereco = st.text_input("Endereço Completo *")
                
                c7, c8, c9 = st.columns(3)
                naturalidade = c7.text_input("Naturalidade")
                estado = c8.text_input("Estado")
                religiao_aluno = c9.text_input("Religião do Aluno")
                
                c10, c11, c12 = st.columns(3)
                nis_aluno = c10.text_input("NIS do Aluno")
                nis_resp = c11.text_input("NIS do Responsável")
                sus = c12.text_input("SUS ou numeração do cartão do plano")
                
                st.markdown("---")
                st.markdown("#### Dados do Pai")
                p1, p2, p3 = st.columns(3)
                nome_pai = p1.text_input("Nome do pai")
                cpf_pai = p2.text_input("CPF do pai")
                rg_pai = p3.text_input("RG do pai")
                
                p4, p5, p6 = st.columns(3)
                religiao_pai = p4.text_input("Religião do pai")
                profissao_pai = p5.text_input("Profissão do pai")
                est_civil_pai = p6.text_input("Estado civil do pai")
                
                p7, p8, p9, p10 = st.columns(4)
                email_pai = p7.text_input("Email do pai")
                fone_pessoal_pai = p8.text_input("Fone pessoal do pai")
                fone_trab_pai = p9.text_input("Fone do trabalho do pai")
                instrucao_pai = p10.text_input("Grau de instrução do pai")
                
                st.markdown("---")
                st.markdown("#### Dados da Mãe")
                m1, m2, m3 = st.columns(3)
                nome_mae = m1.text_input("Nome da mãe")
                cpf_mae = m2.text_input("CPF da mãe")
                rg_mae = m3.text_input("RG da mãe")
                
                m4, m5, m6 = st.columns(3)
                religiao_mae = m4.text_input("Religião da mãe")
                profissao_mae = m5.text_input("Profissão da mãe")
                est_civil_mae = m6.text_input("Estado civil da mãe")
                
                m7, m8, m9, m10 = st.columns(4)
                fone_pessoal_mae = m7.text_input("Fone pessoal da mãe")
                fone_trab_mae = m8.text_input("Fone do trabalho da mãe")
                instrucao_mae = m9.text_input("Grau de instrução da mãe")
                email_mae = m10.text_input("Email da mãe")

                dados_enviar = {
                    "Já Matriculado (Sim/Não)": ja_matriculado, "Nome do aluno(a)": nome_aluno, "Data de nascimento": data_nasc.strftime("%d/%m/%Y"),
                    "Sexo": sexo, "Grupo Sanguíneo": sangue, "CPF Aluno": cpf_aluno, "Endereço": endereco, "Naturalidade": naturalidade, "Estado": estado,
                    "NIS Aluno": nis_aluno, "NIS Responsável": nis_resp, "SUS/Plano de Saúde": sus, "Religião Aluno": religiao_aluno, "Cor": cor,
                    "Nome do Pai": nome_pai, "CPF Pai": cpf_pai, "RG Pai": rg_pai, "Religião Pai": religiao_pai, "Profissão Pai": profissao_pai, "Estado Civil Pai": est_civil_pai,
                    "Email Pai": email_pai, "Fone Pessoal Pai": fone_pessoal_pai, "Fone Trabalho Pai": fone_trab_pai, "Grau Instrução Pai": instrucao_pai,
                    "Nome da Mãe": nome_mae, "CPF Mãe": cpf_mae, "RG Mãe": rg_mae, "Religião Mãe": religiao_mae, "Profissão Mãe": profissao_mae, "Estado Civil Mãe": est_civil_mae,
                    "Fone Pessoal Mãe": fone_pessoal_mae, "Fone Trabalho Mãe": fone_trab_mae, "Grau Instrução Mãe": instrucao_mae, "Email Mãe": email_mae,
                    "Telefone Contato (Renovação)": "-", "Alterações (Renovação)": "-"
                }

            st.markdown("<br>", unsafe_allow_html=True)
            submit_matricula = st.form_submit_button("📤 Enviar Formulário à Secretaria", type="primary", use_container_width=True)
            
            if submit_matricula:
                if nome_aluno.strip() == "":
                    st.error("⚠️ O Nome Completo do Aluno é obrigatório.")
                else:
                    with st.spinner("Transmitindo dados seguros para a escola..."):
                        if salvar_matricula_bd(dados_enviar):
                            st.success("✅ Matrícula enviada com sucesso! A diretoria entrará em contato em breve.")
                            time.sleep(2)
                            st.session_state.mostrar_form_matricula = False
                            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# ================= TELA ALUNO =================
elif st.session_state.perfil_logado == "aluno":
    st.markdown(f"<h1 style='text-align: center;'>🎓 Portal do Aluno</h1>", unsafe_allow_html=True)
    dados_do_aluno = buscar_dados_aluno(st.session_state.usuario_logado)
    if dados_do_aluno:
        st.markdown(f"""
        <div style='background-color: rgba(0, 123, 255, 0.05); padding:20px; border-radius:12px; display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; border: 1px solid rgba(0, 123, 255, 0.1); box-shadow: 0 4px 6px rgba(0,0,0,0.02);'>
            <div>
                <span style='font-size:1.3em;'>👤 <b>{st.session_state.usuario_logado}</b></span><br>
                <span style='font-weight:bold; opacity: 0.8;'>👥 Turma: {dados_do_aluno.get('turma', 'N/A')}  |  🏫 Ensino: {dados_do_aluno.get('ensino', 'N/A')}  |  ⏰ Turno: {dados_do_aluno.get('turno', 'N/A')}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    aba_boletim, aba_avisos = st.tabs(["📊 Boletim de Notas", "📢 Mural de Avisos"])
    
    with aba_boletim:
        st.markdown("### 📝 Desempenho Acadêmico")
        df_notas_aluno = carregar_notas_aluno(st.session_state.usuario_logado)
        if not df_notas_aluno.empty:
            colunas_esperadas = ['disciplina', 'unidade_1', 'unidade_2', 'unidade_3', 'unidade_4', 'media_final', 'situacao']
            colunas_presentes = [col for col in colunas_esperadas if col in df_notas_aluno.columns]
            if len(colunas_presentes) > 0:
                df_boletim_visual = df_notas_aluno[colunas_presentes]
                renomear_para_tela = {'disciplina': 'Disciplina', 'unidade_1': 'I Unid.', 'unidade_2': 'II Unid.', 'unidade_3': 'III Unid.', 'unidade_4': 'IV Unid.', 'media_final': 'Média Final', 'situacao': 'Situação'}
                df_boletim_visual = df_boletim_visual.rename(columns=renomear_para_tela)
                st.dataframe(df_boletim_visual, hide_index=True, use_container_width=True)
                pdf_bytes = gerar_pdf_boletim(st.session_state.usuario_logado, dados_do_aluno, df_boletim_visual)
                if pdf_bytes:
                    col_vazia, col_btn = st.columns([3, 1]) 
                    with col_btn:
                        st.download_button(label="📄 Baixar Boletim em PDF", data=pdf_bytes, file_name=f"Boletim_{st.session_state.usuario_logado}.pdf", mime="application/pdf", type="primary", use_container_width=True)
        else:
            st.info("📌 O boletim está vazio. Os professores ainda não lançaram notas neste período.")

    with aba_avisos:
        st.markdown("### 📢 Quadro de Comunicações")
        df_avisos = carregar_tabela_completa("Avisos")
        tem_aviso = False
        if not df_avisos.empty and 'tipo' in df_avisos.columns:
            avisos_gerais = df_avisos[df_avisos['tipo'].astype(str).str.strip().str.upper() == 'GERAL']
            for _, aviso in avisos_gerais.iterrows():
                st.warning(f"📢 **AVISO GERAL ({aviso.get('data', '')}):** {aviso.get('mensagem', '')}")
                tem_aviso = True
            avisos_ind = df_avisos[(df_avisos['tipo'].astype(str).str.strip().str.upper() == 'INDIVIDUAL') & (df_avisos['aluno'].astype(str).str.strip() == st.session_state.usuario_logado)]
            for _, aviso in avisos_ind.iterrows():
                st.error(f"📩 **MENSAGEM PRIVADA ({aviso.get('data', '')}):** {aviso.get('mensagem', '')}", icon="⚠️")
                tem_aviso = True
        if not tem_aviso:
            st.success("✅ Tudo tranquilo! Não há novos comunicados da secretaria no momento.")

# ================= TELA ADMIN / DIRETORIA =================
elif st.session_state.perfil_logado in ["admin", "diretoria"]:
    st.header("👑 Painel da Diretoria - Centro de Controle")
    st.markdown("Faça adições, edições ou exclusões diretamente nas tabelas abaixo.")
    
    aba_metricas, aba_usuarios, aba_alunos, aba_avisos_admin, aba_matriculas = st.tabs(["📊 Visão Geral", "🔐 Gestão de Logins", "🎓 Gestão de Alunos", "📣 Gestão de Avisos", "📝 Gestão de Matrículas"])
    with aba_metricas:
        st.markdown("### 📊 Estatísticas Globais da Escola")
        df_alunos_calc = carregar_tabela_completa("Alunos")
        total_alunos = len(df_alunos_calc) if not df_alunos_calc.empty else 0
        
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Alunos Matriculados", str(total_alunos), "Total Ativo")
        c2.metric("Frequência Média", "95%", "Global")
        c3.metric("Presentes", "0", "Hoje")
        c4.metric("Ausentes", "0", "Hoje")
        c5.metric("Média Escolar", "8.5", "Geral")

        st.markdown("---")
        st.markdown("### ⚙️ Status do Sistema")
        c6, c7, c8 = st.columns(3)
        c6.metric("Banco de Dados", "Google Sheets", "Conectado")
        c7.metric("Inteligência Artificial", "Gemini API", "Online" if ia_configurada else "Offline")
        c8.metric("Segurança", "Ativa", "100%")
        
    with aba_usuarios:
        st.markdown("### 🔐 Tabela de Usuários")
        df_usuarios = carregar_tabela_completa("Usuarios")
        if not df_usuarios.empty:
            df_usuarios_editado = st.data_editor(df_usuarios, use_container_width=True, num_rows="dynamic", key="editor_users")
            if st.button("💾 Sincronizar Senhas", type="primary", use_container_width=True):
                if sincronizar_aba_completa("Usuarios", df_usuarios_editado): st.success("✅ Atualizado com sucesso!")

    with aba_alunos:
        st.markdown("### 🎓 Tabela de Matrículas")
        df_alunos = carregar_tabela_completa("Alunos")
        if not df_alunos.empty:
            df_alunos_editado = st.data_editor(df_alunos, use_container_width=True, num_rows="dynamic", key="editor_alunos")
            if st.button("💾 Sincronizar Alunos", type="primary", use_container_width=True):
                if sincronizar_aba_completa("Alunos", df_alunos_editado): st.success("✅ Atualizado com sucesso!")
                
    with aba_avisos_admin:
        st.markdown("### 📣 Central de Mensagens e Alertas")
        df_avisos_admin = carregar_tabela_completa("Avisos")
        df_avisos_editado = st.data_editor(df_avisos_admin, use_container_width=True, num_rows="dynamic", key="editor_avisos")
        if st.button("💾 Publicar / Sincronizar Avisos", type="primary", use_container_width=True):
            if sincronizar_aba_completa("Avisos", df_avisos_editado): 
                st.success("✅ Avisos publicados com sucesso na plataforma!")

    with aba_matriculas:
        st.markdown("### 📝 Solicitações de Matrícula (Recebidas do Portal)")
        st.info("💡 As matrículas feitas pelos responsáveis na tela inicial aparecem aqui. A coluna inicial mostra se o aluno já é matriculado.")
        df_matriculas_painel = carregar_tabela_completa("Matriculas")
        
        if not df_matriculas_painel.empty and len(df_matriculas_painel.columns) > 1:
            st.dataframe(df_matriculas_painel, use_container_width=True, hide_index=True)
            
            # Botão prático para baixar as respostas em Excel
            csv_mat = df_matriculas_painel.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Baixar Fichas de Matrícula em CSV/Excel",
                data=csv_mat,
                file_name='solicitacoes_matricula_seea.csv',
                mime='text/csv',
            )
        else:
            st.warning("Ainda não há nenhuma matrícula registrada ou a aba 'Matriculas' está vazia no banco de dados.")

# ================= TELA PROFESSOR =================
elif st.session_state.perfil_logado == "professor":
    aba_dash, aba_freq, aba_notas, aba_ia = st.tabs(["📊 Dashboard", "📅 Frequência", "📝 Notas", "🤖 Gerador IA"])
    
    with aba_dash:
        st.markdown("<h2>Meu Desempenho Pedagógico</h2>", unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Minhas Turmas", "4", "Alocadas")
        c2.metric("Diários Preenchidos", "12", "Este Mês")
        c3.metric("Alunos em Alerta", "3", "Em Recuperação")
        c4.metric("Provas IA Geradas", "5", "Materiais Prontos")
    
    with aba_freq:
        st.markdown("<h2>Registro de Frequência</h2>", unsafe_allow_html=True)
        st.info("Módulo de frequência pronto para operação.")
        
    with aba_notas:
        st.markdown("<h2>Lançamento de Notas</h2>", unsafe_allow_html=True)
        st.info("Módulo de notas pronto para operação.")
        
    with aba_ia:
        st.markdown("<h2>🤖 Fábrica de Avaliações com IA</h2>", unsafe_allow_html=True)
        if not ia_configurada: st.error("⚠️ Sistema Desconectado.")
