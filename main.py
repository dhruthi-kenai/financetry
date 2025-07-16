import streamlit as st
import pandas as pd
from helper import generate_answer, reindex_documents
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from PIL import Image
import os

# Load Kenai logo
logo = Image.open("kenai_logo1.png")

st.set_page_config(page_title="Finance Assist", page_icon=logo)

# Sidebar with logo
st.sidebar.image(logo, use_column_width=True)
st.sidebar.title("Finance Assist")

st.title("Finance Assist ")
st.write("You can ask anything — from invoices & documents to general questions like 'Hi, how are you?' — and I will respond!")

col1, col2 = st.columns([4,1])

with col1:
    user_query = st.text_input("Your question:", "Hi, how are you?")

with col2:
    if st.button("🔄 Reindex Docs"):
        with st.spinner("Reindexing documents with FAISS..."):
            reindex_documents()
        st.success("Documents reindexed with FAISS!")

if st.button("Submit"):
    with st.spinner("Thinking..."):
        sql_df, answer = generate_answer(user_query)

    if not sql_df.empty:
        st.markdown("### Latest SQL Data:")
        st.dataframe(sql_df)

    st.markdown("### Answer:")
    st.markdown(answer, unsafe_allow_html=True)

    # Thin line separator
    st.markdown("<hr style='border: 1px solid #ddd;'>", unsafe_allow_html=True)

# Note: SQL data is shown in table, LLM answers can also be in Markdown tables when appropriate.
