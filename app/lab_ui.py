"""Streamlit lab: run with streamlit run app/lab_ui.py."""
import os
import requests
import streamlit as st

st.set_page_config(page_title='AriNova AI Engineering Lab', layout='wide')
st.title('AriNova AI Engineering Lab')
st.caption('AriNova learning lab — authenticated persistent RAG')
api = st.sidebar.text_input('API URL', os.getenv('LAB_API_URL', 'http://localhost:8000'))
jwt_token = st.sidebar.text_input('JWT bearer token', type='password')
headers = {'Authorization': f'Bearer {jwt_token}'} if jwt_token else {}

def call(method, path, **kwargs):
    r = requests.request(method, api + path, headers=headers, timeout=120, **kwargs)
    r.raise_for_status()
    return r.json()

chat, tools, docs, evals, learn = st.tabs(['Chat + Context', 'Agent Tools', 'Documents + RAG', 'Evals + Traces', '10 Skills'])
with chat:
    st.info('Legacy unscoped chat is disabled. Use Documents + RAG for tenant-scoped questions.')
with tools:
    product = st.selectbox('Product', ['starter', 'premium'])
    qty = st.number_input('Quantity', 1, 100, 2)
    discount = st.slider('Discount %', 0, 50, 10)
    if st.button('Run price tool'):
        try: st.json(call('POST', '/lab/price', json={'product': product, 'quantity': qty, 'discount_percent': discount}))
        except requests.RequestException as exc: st.error(str(exc))
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
with docs:
    st.divider()
    st.subheader('Phase 2 — PDF and hybrid retrieval')
    pdf_upload = st.file_uploader('Upload PDF/TXT for background ingestion', type=['pdf', 'txt'], key='phase2_upload')
    if pdf_upload and st.button('Queue document'):
        try:
            st.json(call('POST', '/rag/upload', files={'file': (pdf_upload.name, pdf_upload.getvalue())}))
        except requests.RequestException as exc:
            st.error(str(exc))
    job_id = st.text_input('Ingestion job ID')
    if job_id and st.button('Check job status'):
        try:
            st.json(call('GET', '/rag/jobs/' + job_id))
        except requests.RequestException as exc:
            st.error(str(exc))
    hybrid_question = st.text_input('Hybrid RAG question', key='hybrid_question')
    rerank_enabled = st.checkbox('Use local cross-encoder reranker', value=False)
    hybrid_llm = st.checkbox('Generate with Ollama (hybrid)', value=False)
    if st.button('Ask hybrid RAG'):
        try:
            result = call('POST', '/rag/hybrid-answer', json={
                'question': hybrid_question, 'rerank': rerank_enabled,
                'use_llm': hybrid_llm, 'limit': 3})
            st.write(result['answer'])
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
