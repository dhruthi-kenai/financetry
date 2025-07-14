import streamlit as st
import pandas as pd
from helper import route_query, fetch_txt_files_from_sharepoint, embeddings
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os

# 📦 Page setup
st.set_page_config(page_title="💰 Finance Chatbot", layout="wide")

# Clean layout
st.markdown("""
    <style>
    div[data-testid="stForm"] {
        border: none;
        padding: 0;
    }
    div[data-testid="column"] {
        padding-bottom: 0rem;
    }
    </style>
""", unsafe_allow_html=True)

# 🧭 Top row: logo + title + reindex button
topcol1, topcol2 = st.columns([6, 1])

with topcol1:
    logo_col, title_col = st.columns([1, 6])
    with logo_col:
        st.image("kenai_logo1.png", width=150)
    with title_col:
        st.markdown("<h1 style='margin-bottom: 0; padding-top: 2px;'> Finance Chatbot</h1>", unsafe_allow_html=True)

with topcol2:
    if st.button("♻️ Reindex Docs"):
        with st.spinner("Reindexing SharePoint documents..."):
            try:
                docs = fetch_txt_files_from_sharepoint()
                if not docs:
                    st.error("No documents found in SharePoint.")
                else:
                    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
                    chunks = splitter.split_documents(docs)
                    vectorstore = FAISS.from_documents(chunks, embeddings)
                    vectorstore.save_local("./vector_index")
                    st.success("✅ Reindexing complete.")
            except Exception as e:
                st.error(f"❌ Reindexing failed: {e}")

# Initialize chat history
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Chat input form
with st.form("chat_form", clear_on_submit=True):
    col1, col2 = st.columns([5, 1])
    with col1:
        query = st.text_input("Ask a finance-related question:", key="query", label_visibility="collapsed")
    with col2:
        submitted = st.form_submit_button("Submit")

# Process query
if submitted and query:
    with st.spinner("Thinking..."):
        try:
            result = route_query(query)

            if result["type"] == "table":
                st.session_state.chat_history.insert(0, ("Bot-Summary", result["summary"]))
                st.session_state.chat_history.insert(0, ("You", query))

            elif result["type"] == "text":
                st.session_state.chat_history.insert(0, ("Bot", result["content"]))
                st.session_state.chat_history.insert(0, ("You", query))

            elif result["type"] == "error":
                st.session_state.chat_history.insert(0, ("Bot", result["content"]))
                st.session_state.chat_history.insert(0, ("You", query))

            elif result["type"] == "info":
                st.session_state.chat_history.insert(0, ("Bot", result["content"]))
                st.session_state.chat_history.insert(0, ("You", query))

        except Exception as e:
            st.session_state.chat_history.insert(0, ("Error", f"Something went wrong: {e}"))
            st.session_state.chat_history.insert(0, ("You", query))

# Show chat history
for role, content in st.session_state.chat_history:
    if role == "You":
        st.markdown(f"<div style='font-weight:bold; font-size:18px;'> You: {content}</div>", unsafe_allow_html=True)

    elif role == "Summary":
        st.markdown(f" <b>Summary:</b>", unsafe_allow_html=True)
        st.markdown(content, unsafe_allow_html=True)

    elif role == "Bot":
        st.markdown(f"<div style='margin-top: 0.5rem; font-size:16px;'> {content}</div>", unsafe_allow_html=True)

    elif role == "Error":
        st.error(content)
