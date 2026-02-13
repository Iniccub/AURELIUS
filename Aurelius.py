import streamlit as st
from datetime import datetime
import pandas as pd
from io import BytesIO
from mongodb_config import get_database
from ai_summary import summarize_repository, ask_repository

# Configuração da Página
st.set_page_config(
    page_title="Aurelius - Assistente de Atas",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="collapsed"
)

def local_css():
    st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    .stTextArea textarea {
        height: 200px;
    }
    </style>
    """, unsafe_allow_html=True)

local_css()

# Título
st.title("📝 Aurelius - O Assistente de IA da Rede Lius")

# Sidebar para Configurações e Modos
with st.sidebar:
    st.header("Sobre")
    st.info("O Aurelius ajuda você a estruturar e formatar suas atas de reunião de forma rápida e eficiente.")
    st.markdown("---")
    
    st.header("Modo de Uso")
    mode = st.radio("Selecione a funcionalidade:", ["Bloco de Notas", "Ata de Reunião"])
    
    st.markdown("---")
    
    if mode == "Ata de Reunião":
        st.header("Opções da Ata")
        theme = st.selectbox("Estilo da Ata", ["Corporativo", "Simples", "Criativo"])

# Lógica Principal baseada no Modo
if mode == "Ata de Reunião":
    st.markdown("Preencha os dados abaixo para gerar uma ata de reunião profissional e estruturada.")
    
    # Container Principal da Ata
    with st.container():
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("1. Detalhes da Reunião")
            topic = st.text_input("Assunto/Título da Reunião", placeholder="Ex: Planejamento Q3")
            date = st.date_input("Data", datetime.now())
            time = st.time_input("Horário", datetime.now())
            location = st.text_input("Local/Link", placeholder="Sala 1 ou Link do Teams/Zoom")
            
        with col2:
            st.subheader("2. Participantes")
            organizer = st.text_input("Organizador/Facilitador")
            attendees = st.text_area("Lista de Presentes (um por linha)", placeholder="João Silva\nMaria Souza\n...")
            absent = st.text_area("Ausentes (opcional)", placeholder="Carlos Pereira...")

        st.markdown("---")
        
        st.subheader("3. Conteúdo da Reunião")
        agenda = st.text_area("Pauta / Agenda", placeholder="- Item 1: Revisão de métricas\n- Item 2: Novos projetos")
        discussion = st.text_area("Discussão / Notas Detalhadas", placeholder="Descreva aqui o que foi discutido, decisões tomadas, etc...", height=300)

        st.markdown("---")
        
        st.subheader("4. Ações e Tarefas (Action Items)")
        
        if 'actions' not in st.session_state:
            st.session_state.actions = []

        with st.expander("Adicionar Nova Ação", expanded=True):
            c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
            with c1:
                act_desc = st.text_input("Descrição da Tarefa")
            with c2:
                act_owner = st.text_input("Responsável")
            with c3:
                act_deadline = st.date_input("Prazo", datetime.now())
            with c4:
                st.write("") # Spacer
                st.write("")
                if st.button("Adicionar"):
                    if act_desc and act_owner:
                        st.session_state.actions.append({
                            "Tarefa": act_desc,
                            "Responsável": act_owner,
                            "Prazo": act_deadline.strftime("%d/%m/%Y")
                        })
                        st.rerun()
                    else:
                        st.warning("Preencha descrição e responsável.")

        if st.session_state.actions:
            st.write("##### Lista de Ações:")
            df_actions = pd.DataFrame(st.session_state.actions)
            st.table(df_actions)
            if st.button("Limpar Ações"):
                st.session_state.actions = []
                st.rerun()

        st.markdown("---")

        # Geração da Ata
        if st.button("📄 Gerar Ata de Reunião", type="primary"):
            if not topic:
                st.error("Por favor, informe pelo menos o assunto da reunião.")
            else:
                # Formatação do Texto
                attendees_list = [a.strip() for a in attendees.split('\n') if a.strip()]
                absent_list = [a.strip() for a in absent.split('\n') if a.strip()]
                
                md_output = f"""# Ata de Reunião: {topic}

**Data:** {date.strftime("%d/%m/%Y")}  
**Horário:** {time.strftime("%H:%M")}  
**Local:** {location}  
**Organizador:** {organizer}

---

## 👥 Participantes
**Presentes:**
{chr(10).join([f'- {p}' for p in attendees_list]) if attendees_list else '- (Nenhum listado)'}

**Ausentes:**
{chr(10).join([f'- {p}' for p in absent_list]) if absent_list else '- (Nenhum)'}

---

## 📅 Pauta / Agenda
{agenda if agenda else 'Não especificada.'}

---

## 📝 Discussão e Decisões
{discussion if discussion else 'Nenhuma nota registrada.'}

---

## ✅ Ações / Próximos Passos
"""
                if st.session_state.actions:
                    for idx, action in enumerate(st.session_state.actions, 1):
                        md_output += f"{idx}. **{action['Tarefa']}** - Resp: {action['Responsável']} (Até: {action['Prazo']})\n"
                else:
                    md_output += "Nenhuma ação definida.\n"
                
                md_output += "\n---\n*Gerado por Aurelius*"

                st.success("Ata gerada com sucesso!")
                
                # Preview
                st.markdown("### Pré-visualização")
                st.markdown(md_output)
                
                # Download Button
                st.download_button(
                    label="📥 Baixar Ata (.txt)",
                    data=md_output,
                    file_name=f"Ata_{topic.replace(' ', '_')}_{date}.txt",
                    mime="text/plain"
                )

elif mode == "Bloco de Notas":
    st.markdown("Modo simplificado para anotações rápidas e arquivamento, com integração com o Aurelius.")
    
    # Conexão com MongoDB
    db = None
    try:
        db = get_database()
        collection = db['repositorio']
        doc_id = "global_notepad_archive"
    except Exception as e:
        st.error(f"Erro ao conectar ao banco de dados: {e}")

    col_left, col_right = st.columns([1, 1], gap="large")
    
    with col_left:
        # Layout mais compacto para o cabeçalho da nota
        c1, c2 = st.columns([3, 1])
        with c1:
            st.subheader("📝 Descrição da Reunião")
        with c2:
            usuario = st.text_input("Usuário", value="", key="notepad_user", placeholder="Seu nome", label_visibility="collapsed")
            
        notes = st.text_area("Anotações", height=600, placeholder="Comece a digitar os pontos principais da reunião...", key="notepad_notes", label_visibility="collapsed")
        
        # Botão de download discretamente abaixo da área de texto
        if notes:
            ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
            st.download_button("📥 Baixar Notas (Txt)", notes, file_name=f"Notas_{ts}.txt", mime="text/plain", use_container_width=True)

    with col_right:
        # Uso de Tabs para organizar a complexidade
        tab_repo, tab_ai = st.tabs(["🗄️ Repositório & Arquivo", "🤖 Assistente Inteligente"])
        
        with tab_repo:
            st.caption("Gerencie o histórico centralizado de anotações.")
            
            # Inicializa variável no session_state
            if "archive_input_val" not in st.session_state:
                st.session_state.archive_input_val = ""

            with st.container(border=True):
                st.markdown("**Adicionar ao Arquivo**")
                new_archive_input = st.text_area("Nova nota:", height=100, key="new_archive_input", placeholder="Digite ou copie aqui...", value=st.session_state.archive_input_val, label_visibility="collapsed")
                
                c_btn1, c_btn2 = st.columns(2)
                with c_btn1:
                    if st.button("⬇️ Copiar das Notas", use_container_width=True):
                        if "notepad_notes" in st.session_state and st.session_state.notepad_notes:
                            st.session_state.archive_input_val = st.session_state.notepad_notes
                            st.rerun()
                        else:
                            st.toast("Nada para copiar!", icon="⚠️")
                            
                with c_btn2:
                    if st.button("➕ Salvar no Histórico", type="primary", use_container_width=True):
                         if new_archive_input:
                            if db is not None:
                                try:
                                    current_doc = collection.find_one({"_id": doc_id})
                                    current_text = current_doc["content"] if current_doc and "content" in current_doc else ""
                                    
                                    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
                                    user_str = f" | 👤 {usuario}" if usuario else ""
                                    new_entry = f"\n\n=== 📅 {timestamp}{user_str} ===\n{new_archive_input}"
                                    
                                    updated_text = (current_text + new_entry) if current_text else f"=== 📅 {timestamp}{user_str} ===\n{new_archive_input}"
                                    
                                    collection.update_one(
                                        {"_id": doc_id},
                                        {"$set": {"content": updated_text, "updated_at": datetime.now()}},
                                        upsert=True
                                    )
                                    st.toast("Salvo com sucesso!", icon="✅")
                                    st.session_state.archive_input_val = ""
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro: {e}")
                            else:
                                st.error("Sem conexão.")
                         else:
                            st.warning("Escreva algo para salvar.")

            st.markdown("### 📜 Histórico")
            # Recuperar histórico
            history_content = "Carregando..."
            if db is not None:
                saved_doc = collection.find_one({"_id": doc_id})
                history_content = saved_doc["content"] if saved_doc and "content" in saved_doc else "(Histórico vazio)"
            else:
                history_content = "Sem conexão."
                
            st.text_area("Histórico", value=history_content, height=350, disabled=True, label_visibility="collapsed")
            
            # Botão para baixar tudo
            if history_content != "(Histórico vazio)" or notes:
                full_content = f"ANOTAÇÕES ATUAIS:\n{notes if notes else '(Vazio)'}\n\n--- HISTÓRICO ---\n{history_content}"
                st.download_button("📥 Baixar Relatório Completo", full_content, file_name=f"Relatorio_Completo_{datetime.now().strftime('%Y-%m-%d')}.txt", use_container_width=True)

        with tab_ai:
            st.caption("Analise o histórico com o Aurélius.")
            
            with st.expander("📊 Gerador de Resumos", expanded=True):
                ai_instructions = st.text_input("Foco da análise (Opcional):", placeholder="Ex: Decisões de Janeiro...")
                if st.button("✨ Gerar Resumo Executivo", use_container_width=True):
                     resumo = summarize_repository(history_content, additional_instructions=ai_instructions)
                     st.markdown(resumo)
            
            st.markdown("---")
            
            with st.container(border=True):
                st.markdown("**💬 Chat com o Repositório**")
                user_question = st.text_input("Sua pergunta:", placeholder="O que foi falado sobre...?", label_visibility="collapsed")
                if st.button("Perguntar ao Aurélius", use_container_width=True):
                    if user_question:
                        answer = ask_repository(history_content, user_question)
                        st.info(answer)
                    else:
                        st.warning("Digite uma pergunta.")
