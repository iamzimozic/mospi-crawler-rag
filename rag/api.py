import streamlit as st
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama.llms import OllamaLLM
from .retriever import get_vs
from .prompt import PROMPT_TMPL

def get_llm():
    if "llm" not in st.session_state:
        st.session_state.llm = OllamaLLM(model="llama3.1:8b")
    return st.session_state.llm

def retrieve_and_answer(question: str) -> str:
    vs = get_vs()
    retrieved = vs.similarity_search(question, k=10)
    if not retrieved:
        return "No indexed text yet. Please process some PDFs first."
    context = "\n\n".join(doc.page_content for doc in retrieved)
    prompt = ChatPromptTemplate.from_template(PROMPT_TMPL)
    return (prompt | get_llm()).invoke({"question": question, "context": context})
