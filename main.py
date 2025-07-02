import streamlit as st
import pandas as pd
from helper import route_query, fetch_txt_files_from_sharepoint, embeddings
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os

# Page setup
st.set_page_config(page_title="💰 Finance Chatbot", layout="wide")

# CSS styling
st.markdown("""
    <style>
    body, .stApp {
        background-color: white;
    }
    div[data-testid="stForm"] {
        border: none;
        padding: 0;
    }
    div[data-testid="column"] {
        padding-bottom: 0rem;
    }
    .header-container {
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .header-logo {
        height: 38px;
        margin-right: 8px;
    }
    .header-title {
        font-size: 32px;
        font-weight: bold;
        color: #d11b1b;
    }
    </style>
""", unsafe_allow_html=True)

# Header row: Logo + Title + Chat Icon
topcol1, topcol2 = st.columns([6, 1])
with topcol1:
    st.markdown(
        """
        <div class="header-container">
            <img src="https://raw.githubusercontent.com/drhuthikenai/assets/main/kenai_logo.png" class="header-logo" />
            <img src="https://cdn-icons-png.flaticon.com/512/2462/2462719.png" class="header-logo" />
            <span class="header-title">Finance Chatbot</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
with topcol2:
    st.write("")  # Spacer
    st.write("")  # Spacer
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
        query = st.text_input("e.g. Show all paid invoices", key="query", label_visibility="collapsed")
    with col2:
        submitted = st.form_submit_button("Submit")

# Process query
if submitted and query:
    with st.spinner("Thinking..."):
        try:
            result = route_query(query)
            st.session_state.chat_history.insert(0, ("Bot", result))
            st.session_state.chat_history.insert(0, ("You", query))
        except Exception as e:
            st.session_state.chat_history.insert(0, ("Error", f"Something went wrong: {e}"))

# Display chat history
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
