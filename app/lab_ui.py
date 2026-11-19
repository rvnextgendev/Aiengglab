"""Streamlit lab: run with streamlit run app/lab_ui.py."""
import os
import requests
import streamlit as st

st.set_page_config(page_title='AriNova AI Engineering Lab', layout='wide')
st.title('AriNova AI Engineering Lab')
st.caption('One practical app for Python, LLMs, context, RAG, agents, evals, deployment, security, fine-tuning and product design')
api = st.sidebar.text_input('API URL', os.getenv('LAB_API_URL', 'http://localhost:8000'))
key = st.sidebar.text_input('API key (optional)', type='password')
jwt_token = st.sidebar.text_input('JWT bearer token', type='password')
headers = {'Authorization': f'Bearer {jwt_token}'} if jwt_token else {}
use_llm = st.sidebar.checkbox('Use Ollama LLM', False)
if 'session' not in st.session_state:
    st.session_state.session = None

def call(method, path, **kwargs):
    r = requests.request(method, api + path, headers=headers, timeout=120, **kwargs)
    r.raise_for_status()
    return r.json()

chat, tools, docs, evals, learn = st.tabs(['Chat + Context', 'Agent Tools', 'Documents + RAG', 'Evals + Traces', '10 Skills'])
with chat:
    question = st.text_input('Ask about AriNova', 'How many paid leave days do employees get?')
    if st.button('Ask assistant'):
        try:
            data = call('POST', '/lab/ask', json={'question': question, 'session_id': st.session_state.session, 'use_llm': use_llm})
            st.session_state.session = data['session_id']
            st.write(data['answer'])
            st.caption(f"Tool: {data['tool']} | History turns: {data['history_length']} | {data['latency_ms']} ms")
            st.json(data['sources'])
        except requests.RequestException as exc:
            st.error(str(exc))
with tools:
    product = st.selectbox('Product', ['starter', 'premium'])
    qty = st.number_input('Quantity', 1, 100, 2)
    discount = st.slider('Discount %', 0, 50, 10)
    if st.button('Run price tool'):
        try: st.json(call('POST', '/lab/price', json={'product': product, 'quantity': qty, 'discount_percent': discount}))
        except requests.RequestException as exc: st.error(str(exc))
with docs:
    uploaded = st.file_uploader('Upload a small UTF-8 text document', type=['txt'])
    if uploaded and st.button('Add document'):
        try: st.json(call('POST', '/lab/documents', json={'filename': uploaded.name, 'content': uploaded.getvalue().decode('utf-8')}))
        except (UnicodeDecodeError, requests.RequestException) as exc: st.error(str(exc))
with docs:
    st.divider()
    st.subheader('Persistent RAG (PostgreSQL + pgvector)')
    st.caption('Requires a signed JWT, migrated PostgreSQL, and requirements-foundation.txt.')
    persistent_upload = st.file_uploader('Persistent RAG TXT document', type=['txt'], key='persistent_upload')
    if persistent_upload and st.button('Save in PostgreSQL'):
        try:
            st.json(call('POST', '/rag/ingest', json={
                'filename': persistent_upload.name,
                'content': persistent_upload.getvalue().decode('utf-8')}))
        except (UnicodeDecodeError, requests.RequestException) as exc:
            st.error(str(exc))
    rag_question = st.text_input('Ask persistent RAG', 'What is the return policy?')
    rag_llm = st.checkbox('Generate answer with Ollama', value=False, key='rag_llm')
    min_score = st.slider('Minimum similarity score', 0.0, 1.0, 0.35, 0.05)
    if st.button('Search PostgreSQL and answer'):
        try:
            result = call('POST', '/rag/answer', json={
                'question': rag_question, 'use_llm': rag_llm, 'min_score': min_score})
            st.write(result['answer'])
            st.caption(f"Mode: {result['mode']} | {result['latency_ms']} ms")
            st.json(result['sources'])
        except requests.RequestException as exc:
            st.error(str(exc))
with evals:
    if st.button('Run evaluation suite'):
        try:
            result = call('GET', '/lab/evaluate')
            st.metric('Heuristic accuracy', f"{result['accuracy']:.0%}")
            st.dataframe(result['details'])
        except requests.RequestException as exc: st.error(str(exc))
with learn:
    st.markdown("""
    1. **Python**: inspect `app/advanced.py`.
    2. **LLMs**: enable Ollama and compare generated answers with excerpts.
    3. **Context**: inspect grounded prompts and session history.
    4. **RAG**: compare keyword fallback and optional embedding search.
    5. **Agents**: observe rule-based routing to document search or price calculator.
    6. **Evals**: run the test cases and inspect latency.
    7. **LLMOps**: use Docker, health checks and GitHub CI.
    8. **Security**: test API key, input validation and injection rejection.
    9. **Fine-tuning**: inspect sample training records; training is not automated.
    10. **System design**: read the architecture and limitations in README.
    """)
