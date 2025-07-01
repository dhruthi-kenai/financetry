import streamlit as st
import pandas as pd
from helper import route_query, fetch_txt_files_from_sharepoint, embeddings
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os

# 📦 Page setup
st.set_page_config(page_title="💰 Finance Chatbot", layout="wide")

# 🖼️ Logo and title
col_logo, col_title = st.columns([1, 5])
with col_logo:
    st.image("kenai_logo1.png", width=90)  # Make sure this image is in the same folder
with col_title:
    st.markdown("<h1 style='margin-bottom: 0;'>Finance Chatbot</h1>", unsafe_allow_html=True)

# 🎨 Custom CSS for beige background
st.markdown("""
    <style>
    body, .stApp {
        background-color: #fdf6ec;
        font-family: 'Segoe UI', sans-serif;
    }
    div[data-testid="stForm"] {
        border: none;
        padding: 0;
    }
    div[data-testid="column"] {
        padding-bottom: 0rem;
    }
    h1 {
        color: #d62828;
    }
    </style>
""", unsafe_allow_html=True)

# 🔁 Reindex button
topcol1, topcol2 = st.columns([6, 1])
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

# 🔁 Initialize chat history
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# 💬 Chat input form
with st.form("chat_form", clear_on_submit=True):
    col1, col2 = st.columns([5, 1])
    with col1:
        query = st.text_input("Ask a finance-related question:", key="query", label_visibility="collapsed")
    with col2:
        submitted = st.form_submit_button("Submit")

# 🧠 Process query
if submitted and query:
    with st.spinner("Thinking..."):
        try:
            result = route_query(query)
            st.session_state.chat_history.insert(0, ("Bot", result))
            st.session_state.chat_history.insert(0, ("You", query))
        except Exception as e:
            st.session_state.chat_history.insert(0, ("Error", f"Something went wrong: {e}"))

# 🪵 Show chat history
for role, content in st.session_state.chat_history:
    if isinstance(content, pd.DataFrame):
        if role == "You":
            st.markdown(f"**You:**")
        if not content.empty:
            st.dataframe(content, use_container_width=True)
        else:
            st.info("No data found.")
    else:
        if role == "You":
            st.markdown(f"**You:** {content}")
        else:
            st.markdown(content)
