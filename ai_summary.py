import streamlit as st
import requests
import json
import pandas as pd
import os
import msoffcrypto
import io

def get_openai_api_key():
    """Recupera a chave da API da OpenAI dos secrets do Streamlit."""
    try:
        api_key = st.secrets["openai"]["api_key"]
        if not api_key.startswith('sk-'):
            st.error('Formato da chave da API OpenAI inválido')
            return None
        return api_key
    except Exception:
        st.error('Chaves de API não encontradas nas configurações do Streamlit')
        return None

@st.cache_data(show_spinner=False)
def load_cargos_info():
    """Carrega informações de cargos do arquivo Excel para contexto, suportando arquivos protegidos por senha."""
    try:
        file_path = os.path.join(os.getcwd(), 'CARGOS.xlsx')
        if not os.path.exists(file_path):
            return "Informações de cargos não disponíveis (Arquivo CARGOS.xlsx não encontrado)."
        
        # Tenta recuperar a senha dos secrets
        excel_password = None
        try:
            excel_password = st.secrets["excel"]["password"]

        except Exception:
            pass # Nenhuma senha configurada, segue fluxo normal
            
        if excel_password:
            try:
                # Fluxo para arquivo protegido
                decrypted_workbook = io.BytesIO()
                with open(file_path, "rb") as file:
                    office_file = msoffcrypto.OfficeFile(file)
                    office_file.load_key(password=excel_password)
                    office_file.decrypt(decrypted_workbook)
                
                df = pd.read_excel(decrypted_workbook)
            except Exception as crypto_error:
                # Se falhar a descriptografia, tenta abrir normal (pode ser que a senha não fosse necessária ou estava errada)
                # ou retorna o erro específico.
                return f"Erro ao abrir arquivo protegido (verifique a senha no secrets): {str(crypto_error)}"
        else:
            # Fluxo padrão sem senha
            df = pd.read_excel(file_path)
        
        # Cria uma string formatada com as informações relevantes
        cargos_context = "Lista de Colaboradores e Cargos da Rede Lius:\n"
        for _, row in df.iterrows():
            nome = str(row.get('NOME', '')).strip()
            cargo = str(row.get('CARGO', '')).strip()
            area = str(row.get('ÁREA', '')).strip()
            unidade = str(row.get('UNIDADE', '')).strip()
            
            if nome:
                cargos_context += f"- {nome}: {cargo} ({area} - {unidade})\n"
                
        return cargos_context
    except Exception as e:
        return f"Erro ao carregar informações de cargos: {str(e)}"

def summarize_repository(content, additional_instructions=None, model="gpt-4o-mini"):
    """
    Envia o conteúdo do repositório para a OpenAI e retorna um resumo estruturado.
    
    Args:
        content (str): O conteúdo do repositório (histórico de notas).
        additional_instructions (str, optional): Instruções extras do usuário (ex: foco em data X).
        model (str): O modelo da OpenAI a ser utilizado.
        
    Returns:
        str: O resumo estruturado gerado pela IA ou mensagem de erro.
    """
    api_key = get_openai_api_key()
    if not api_key:
        return "Erro: Chave da API não configurada."

    if not content or content == "(Histórico vazio)":
        return "O repositório está vazio. Nada para resumir."

    # Carrega contexto de cargos
    cargos_info = load_cargos_info()

    api_url = 'https://api.openai.com/v1/chat/completions'
    headers_api = {
        'Authorization': f'Bearer {api_key.strip()}',
        'Content-Type': 'application/json'
    }

    # Prepara o bloco de instruções adicionais, se houver
    instructions_block = ""
    if additional_instructions and additional_instructions.strip():
        instructions_block = f"""
    <user_instructions_override>
    {additional_instructions}
    </user_instructions_override>
    
    Por favor, priorize estas instruções acima ao gerar o resumo, adaptando o foco conforme solicitado (ex: filtrando por data, assunto ou pessoa específica).
    """

    prompt = f"""
    Você é um assistente executivo sênior integrado ao sistema Aurelius da Rede Lius.
    Sua tarefa é analisar o histórico de anotações de reuniões e criar um resumo executivo estruturado, utilizando o contexto corporativo fornecido.
    
    <corporate_context>
    {cargos_info}
    </corporate_context>

    {instructions_block}

    <analysis_instructions>
    1. **Identificação de Stakeholders**: Sempre que um nome for mencionado nas notas (ou se o usuário que fez o registro for identificado), tente correlacionar com a lista de cargos para dar contexto sobre quem está envolvido (ex: "A Diretora Márcia Nóbrega pontuou...").
    2. **Viés Corporativo**: Utilize linguagem formal e corporativa. Foque em decisões estratégicas, atribuições de responsabilidade e alinhamentos entre áreas.
    3. **Estrutura**: Organize a resposta de forma clara e hierárquica.
    </analysis_instructions>
    
    <notes_history>
    {content[:15000]}  # Limitando caracteres
    </notes_history>
    
    <expected_format>
    1. **Resumo Executivo**: Visão geral estratégica dos temas discutidos.
    2. **Principais Deliberações e Pontos de Atenção**: Lista de decisões tomadas e pontos críticos, citando os envolvidos e seus cargos quando possível.
    3. **Evolução dos Tópicos**: Breve análise cronológica de como os assuntos evoluíram.
    4. **Action Items / Pendências**: Tarefas ou pontos em aberto, identificando os responsáveis e suas áreas.
    </expected_format>
    """

    messages = [
        {"role": "system", "content": "Você é um assistente executivo sênior da Rede Lius, especialista em análise de atas e contexto corporativo."},
        {"role": "user", "content": prompt}
    ]

    body_message = {
        'model': model,
        'messages': messages,
        'temperature': 0.3,
        'max_tokens': 2500
    }

    try:
        with st.spinner('A IA está analisando o repositório, cruzando com dados corporativos e gerando o resumo...'):
            response_api = requests.post(api_url, headers=headers_api, json=body_message)
            response_api.raise_for_status()
            resposta = response_api.json()['choices'][0]['message']['content']
            return resposta
    except Exception as e:
        return f"Erro ao comunicar com a IA: {str(e)}"


def summarize_meeting_description(description, history, additional_instructions=None, model="gpt-4o-mini"):
    api_key = get_openai_api_key()
    if not api_key:
        return "Erro: Chave da API não configurada."

    if not description or not description.strip():
        return "A descrição da reunião está vazia. Preencha o campo antes de gerar o resumo."

    cargos_info = load_cargos_info()

    api_url = 'https://api.openai.com/v1/chat/completions'
    headers_api = {
        'Authorization': f'Bearer {api_key.strip()}',
        'Content-Type': 'application/json'
    }

    instructions_block = ""
    if additional_instructions and additional_instructions.strip():
        instructions_block = f"""
    <user_instructions_override>
    {additional_instructions}
    </user_instructions_override>
    """

    prompt = f"""
    Você é um assistente executivo sênior integrado ao sistema Aurelius da Rede Lius.
    Seu objetivo é gerar um RESUMO EXECUTIVO da reunião, com foco principal na descrição atual,
    usando o histórico apenas como complemento quando agregar contexto.
    
    <corporate_context>
    {cargos_info}
    </corporate_context>
    
    {instructions_block}
    
    <priority_content_current_meeting>
    {description[:8000]}
    </priority_content_current_meeting>
    
    <supporting_content_history>
    {(history or '')[:7000]}
    </supporting_content_history>
    
    <guidelines>
    1. Dê ÊNFASE ao campo de descrição atual. Use o histórico apenas para completar lacunas, confirmar decisões ou identificar recorrências.
    2. Use linguagem formal e corporativa, adequada a reporte para diretoria.
    3. Quando possível, conecte pessoas citadas aos cargos do contexto.
    </guidelines>
    
    <response_format>
    1. Resumo Executivo da Reunião
    2. Principais Decisões e Encaminhamentos
    3. Riscos, Alertas ou Conflitos Relevantes
    4. Próximos Passos Recomendados
    </response_format>
    """

    messages = [
        {
            "role": "system",
            "content": "Você é um assistente executivo da Rede Lius, especialista em transformar anotações de reunião em resumos executivos objetivos."
        },
        {"role": "user", "content": prompt},
    ]

    body_message = {
        "model": model,
        "messages": messages,
        "temperature": 0.25,
        "max_tokens": 2000,
    }

    try:
        with st.spinner("A IA está gerando o resumo executivo da descrição da reunião..."):
            response_api = requests.post(api_url, headers=headers_api, json=body_message)
            response_api.raise_for_status()
            resposta = response_api.json()["choices"][0]["message"]["content"]
            return resposta
    except Exception as e:
        return f"Erro ao comunicar com a IA: {str(e)}"

def ask_repository(content, question, model="gpt-4o-mini"):
    """
    Responde a uma pergunta específica do usuário baseada no repositório.
    
    Args:
        content (str): O conteúdo do repositório (histórico de notas).
        question (str): A pergunta do usuário.
        model (str): O modelo da OpenAI a ser utilizado.
        
    Returns:
        str: A resposta da IA.
    """
    api_key = get_openai_api_key()
    if not api_key:
        return "Erro: Chave da API não configurada."

    if not content or content == "(Histórico vazio)":
        return "O repositório está vazio. Não há informações para responder."

    cargos_info = load_cargos_info()

    api_url = 'https://api.openai.com/v1/chat/completions'
    headers_api = {
        'Authorization': f'Bearer {api_key.strip()}',
        'Content-Type': 'application/json'
    }

    prompt = f"""
    Você é Aurélius, o assistente virtual corporativo da Rede Lius.
    
    <history_context>
    {content[:15000]}
    </history_context>
    
    <corporate_context>
    {cargos_info}
    </corporate_context>
    
    <user_question>
    {question}
    </user_question>
    
    <response_guidelines>
    1. Responda APENAS com base nos dados fornecidos acima.
    2. Fale em primeira pessoa, como um assistente humano-profissional, de forma amigável e objetiva.
    3. Seja conciso: normalmente entre 2 e 5 frases curtas.
    4. Se a informação não estiver no histórico, diga claramente: "Não encontrei essa informação no histórico."
    5. Use os cargos para identificar as pessoas, quando isso ajudar a clareza da resposta.
    </response_guidelines>
    """

    messages = [
        {
            "role": "system",
            "content": "Você é Aurélius, assistente virtual corporativo da Rede Lius. Você responde de forma profissional, clara e amigável, sempre de maneira objetiva."
        },
        {"role": "user", "content": prompt}
    ]

    body_message = {
        'model': model,
        'messages': messages,
        'temperature': 0.1, # Temperatura baixa para ser mais factual
        'max_tokens': 500
    }

    try:
        with st.spinner('Consultando o repositório...'):
            response_api = requests.post(api_url, headers=headers_api, json=body_message)
            response_api.raise_for_status()
            resposta = response_api.json()['choices'][0]['message']['content']
            return resposta
    except Exception as e:
        return f"Erro ao consultar a IA: {str(e)}"
