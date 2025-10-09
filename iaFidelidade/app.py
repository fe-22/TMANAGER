import os
import streamlit as st
from groq import Groq

st.set_page_config(page_title="IA ADFidelidade",
                   page_icon="f_icon.zip", layout="wide",
                   initial_sidebar_state="expanded")

# Adicionar imagem no topo da página - CORRIGIDO
try:
    # Tente carregar a imagem local
    st.image("imagem/photo.png", 
             use_container_width=True, 
             caption="Igreja ADFidelidade")
except Exception as e:
    # Se não conseguir, use uma imagem placeholder ou URL
    st.image("https://via.placeholder.com/800x200/4B0082/FFFFFF?text=ADFidelidade", 
             use_container_width=True, 
             caption="Igreja ADFidelidade")
    st.warning("Imagem local não encontrada. Usando imagem placeholder.")

CUSTOM_PROMPT = """
Você é um assistente virtual especializado na biblia e dedicado ao ensino da palavra de Deus para membros da igreja ADFidelidade, fornecendo informações claras e precisas.
REGRAS DE OPERAÇÃO: 
1. **Sempre responda de forma clara e precisa, utilizando a linguagem da bíblia.
2. Mantenha um tom amigável e acolhedor, refletindo os valores da igreja ADFidelidade.
3. Evite discussões teológicas complexas que possam confundir os membros.
4. Sempre que possível, forneça referências bíblicas para apoiar suas respostas.
5. Respeite a diversidade de interpretações dentro do cristianismo, focando na perspectiva da igreja ADFidelidade.
6. Nunca forneça informações que possam ser consideradas ofensivas ou inadequadas para o público da igreja.
7. Se não souber a resposta para uma pergunta, admita honestamente e sugira buscar orientação com um líder espiritual.
8. Mantenha a confidencialidade e o respeito pelas questões pessoais dos membros.
"""

with st.sidebar:
    st.title("Configurações")
    
    # Configuração da API Groq (principal)
    groq_api_key = st.text_input("Insira sua chave de API Groq:", type="password")
    
    if not groq_api_key:
        st.warning("Por favor, insira sua chave de API Groq para continuar.")
        st.stop()
    
    # Inicializar cliente Groq
    try:
        client = Groq(api_key=groq_api_key)
        st.success("Conectado ao Groq com sucesso!")
    except Exception as e:
        st.error(f"Erro ao conectar ao Groq: {e}")
        st.stop()
    
    # Configurações do modelo
    st.markdown("---")
    st.markdown("### Configurações do Modelo")
    
    model = st.selectbox("Selecione o modelo:",
                         ["llama-3.1-8b-instant", 
                          "llama-3.1-70b-versatile",
                          "llama-3.2-1b-preview",
                          "llama-3.2-3b-preview",
                          "llama-3.3-70b-specdec",
                          "mixtral-8x7b-32768",
                          "gemma2-9b-it"])
    
    max_tokens = st.slider(
        "Máximo de tokens na resposta:", min_value=100, max_value=4000, value=1024, step=100)

    temperature = st.slider(
        "Temperatura (criatividade da resposta):", min_value=0.0, max_value=1.0, value=0.7, step=0.1)

    top_p = st.slider(
        "Top P (diversidade da resposta):", min_value=0.0, max_value=1.0, value=1.0, step=0.1)

    frequency_penalty = st.slider(
        "Penalidade de frequência:", min_value=0.0, max_value=2.0, value=0.0, step=0.1)

    presence_penalty = st.slider(
        "Penalidade de presença:", min_value=0.0, max_value=2.0, value=0.0, step=0.1)
    
    st.markdown("---")
    st.markdown("## Sobre") 
    st.markdown("Este é um assistente virtual da igreja ADFidelidade, projetado para ajudar os membros a encontrar informações e recursos relacionados à Bíblia.")  
    
    # Informação do Líder/Coordenador do Ministério de Ensino
    st.markdown("---")
    st.markdown("### 🎓 Ministério de Ensino")
    st.markdown("**Líder/Coordenador:** PR Alex Messias")
    
    st.markdown("---")
    st.markdown("Desenvolvido por [fthec](https://home-page-76ks.onrender.com/).")

# Inicializar histórico de mensagens
if "messages" not in st.session_state:
    st.session_state.messages = []

# Título principal com informações da liderança
col1, col2 = st.columns([3, 1])
with col1:
    st.title("🤖 Assistente Virtual ADFidelidade")
    st.markdown("### Bem-vindo ao seu assistente bíblico virtual!")
with col2:
    st.info("🎓 **Ministério de Ensino**\n\n**Líder/Coordenador:**\nPR Alex Messias")

# Exibir histórico de mensagens
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Captura a entrada do usuário no chat
if prompt := st.chat_input("Qual sua dúvida sobre a Bíblia?"):
    
    # Armazena a mensagem do usuário no estado da sessão
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Exibe a mensagem do usuário no chat
    with st.chat_message("user"):
        st.markdown(prompt)

    # Prepara mensagens para enviar à API, incluindo prompt de sistema
    messages_for_api = [{"role": "system", "content": CUSTOM_PROMPT}]
    for msg in st.session_state.messages:
        messages_for_api.append(msg)

    # Cria a resposta do assistente no chat
    with st.chat_message("assistant"):
        
        with st.spinner("Analisando sua pergunta..."):
            
            try:
                # Chama a API da Groq para gerar a resposta do assistente
                chat_completion = client.chat.completions.create(
                    messages=messages_for_api,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    top_p=top_p,
                    frequency_penalty=frequency_penalty,
                    presence_penalty=presence_penalty,
                    stream=False
                )
                
                # Extrai a resposta gerada pela API
                resposta = chat_completion.choices[0].message.content
                
                # Exibe a resposta no Streamlit
                st.markdown(resposta)
                
                # Armazena resposta do assistente no estado da sessão
                st.session_state.messages.append({"role": "assistant", "content": resposta})

            # Caso ocorra erro na comunicação com a API, exibe mensagem de erro
            except Exception as e:
                st.error(f"Ocorreu um erro ao se comunicar com a API da Groq: {e}")

# Botão para limpar o histórico
col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    if st.button("🧹 Limpar Conversa"):
        st.session_state.messages = []
        st.rerun()

# Informações sobre os modelos disponíveis
with st.expander("ℹ️ Sobre os modelos disponíveis"):
    st.markdown("""
    **Modelos Groq disponíveis:**
    
    **🦙 Llama 3.1 Series:**
    - **llama-3.1-8b-instant**: Rápido e eficiente para respostas instantâneas
    - **llama-3.1-70b-versatile**: Mais preciso e detalhado para tarefas complexas
    
    **🦙 Llama 3.2 Series:**
    - **llama-3.2-1b-preview**: Modelo leve e rápido
    - **llama-3.2-3b-preview**: Equilíbrio entre velocidade e qualidade
    
    **🦙 Llama 3.3 Series:**
    - **llama-3.3-70b-specdec**: Modelo avançado para tarefas complexas
    
    **🤖 Outros Modelos:**
    - **mixtral-8x7b-32768**: Excelente para raciocínio complexo
    - **gemma2-9b-it**: Modelo Gemma 2 do Google, eficiente e preciso
    
    **💡 Recomendação:** Use `llama-3.1-8b-instant` para respostas rápidas ou `llama-3.1-70b-versatile` para respostas mais detalhadas.
    """)

# Rodapé com informações da liderança
st.markdown("---")
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.markdown(
        """
        <div style="text-align: center; color: gray;">
            <p><strong>Assistente Virtual ADFidelidade</strong></p>
            <p>Auxiliando no estudo da Palavra de Deus</p>
            <p style="margin-top: 10px;">🎓 <strong>Ministério de Ensino</strong><br>
            <em>Líder/Coordenador: PR Alex Messias</em></p>
        </div>
        """,
        unsafe_allow_html=True
    )