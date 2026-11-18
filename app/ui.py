import requests
import streamlit as st
st.set_page_config(page_title='AriNova AI Lab')
st.title('AriNova AI Knowledge Assistant')
st.caption('Learn retrieval, LLMs, citations, guardrails, and observability')
question = st.text_input('Ask a question', 'How many paid leave days do employees get?')
use_llm = st.checkbox('Use local Ollama model', value=False)
if st.button('Ask'):
    try:
        response = requests.post('http://localhost:8000/ask', json={'question': question, 'use_llm': use_llm}, timeout=100)
        response.raise_for_status()
        data = response.json()
        st.write(data['answer'])
        st.caption(f"Sources: {', '.join(data['sources']) or 'none'} | {data['latency_ms']} ms | Mode: {data['mode']}")
    except requests.RequestException as exc:
        st.error(f'API request failed: {exc}')
