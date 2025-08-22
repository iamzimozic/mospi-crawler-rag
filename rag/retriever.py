import streamlit as st
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_ollama import OllamaEmbeddings

import chromadb
from langchain_community.vectorstores import Chroma

def get_vs():
    if "embeddings" not in st.session_state:
        st.session_state.embeddings = OllamaEmbeddings(model="llama3.1:8b")
    if "vector_store" not in st.session_state:
        persist_dir = "data/chroma_db"  # folder where vectors will be saved
        st.session_state.vector_store = Chroma(
            collection_name="rag_collection",
            embedding_function=st.session_state.embeddings,
            persist_directory=persist_dir
        )
    return st.session_state.vector_store


def chunk_and_index(text: str, meta_source: str):
    if not text.strip():
        return
    splitter = RecursiveCharacterTextSplitter(chunk_size=5000, chunk_overlap=200)
    docs = splitter.create_documents([text], metadatas=[{"source": meta_source}])
    vs = get_vs()
    vs.add_documents(docs)
    # Ensure vectors are flushed to disk so they persist across app restarts
    try:
        vs.persist()
    except Exception:
        # Some vector store implementations may not require/implement persist
        pass
    st.session_state.setdefault("indexed_sources", set()).add(meta_source)
