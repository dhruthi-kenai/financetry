# helper.py

import mysql.connector
import requests
import openai
import pandas as pd
import streamlit as st
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from langchain.embeddings.openai import OpenAIEmbeddings
import os

FAISS_INDEX_PATH = "faiss_index"


# 🔷 MySQL Query - returns DataFrame
def query_mysql(sql):
    db_config = {
        'host': st.secrets["DB_HOST"],
        'user': st.secrets["DB_USER"],
        'password': st.secrets["DB_PASSWORD"],
        'database': st.secrets["DB_NAME"],
        'port': int(st.secrets["DB_PORT"])
    }

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute(sql)
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    cursor.close()
    conn.close()
    df = pd.DataFrame(rows, columns=columns)
    return df


# 🔷 Get Microsoft Graph Token
def get_graph_token():
    url = f"https://login.microsoftonline.com/{st.secrets['TENANT_ID']}/oauth2/v2.0/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": st.secrets["CLIENT_ID"],
        "client_secret": st.secrets["CLIENT_SECRET"],
        "scope": "https://graph.microsoft.com/.default"
    }
    resp = requests.post(url, data=data)
    resp.raise_for_status()
    return resp.json()["access_token"]


# 🔷 List SharePoint Files
def list_sharepoint_files(token):
    headers = {"Authorization": f"Bearer {token}"}

    site_url = f"https://graph.microsoft.com/v1.0/sites/{st.secrets['SHAREPOINT_HOST']}:/sites/{st.secrets['SITE_NAME']}"
    site = requests.get(site_url, headers=headers).json()
    site_id = site['id']

    drive_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"
    drives = requests.get(drive_url, headers=headers).json()
    drive_id = drives['value'][0]['id']

    items_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{st.secrets['DOC_LIB_PATH']}:/children"
    items = requests.get(items_url, headers=headers).json()

    return items['value']


# 🔷 Download SharePoint files and return text content
def fetch_txt_files_from_sharepoint():
    token = get_graph_token()
    files = list_sharepoint_files(token)
    texts = []

    for file in files:
        download_url = file['@microsoft.graph.downloadUrl']
        content = requests.get(download_url).text
        texts.append(Document(page_content=content, metadata={"name": file['name']}))
    return texts


# 🔷 Reindex documents with FAISS
def reindex_documents():
    docs = fetch_txt_files_from_sharepoint()
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    split_docs = []
    for doc in docs:
        split_docs.extend(splitter.create_documents([doc.page_content]))

    embeddings = OpenAIEmbeddings()
    vectorstore = FAISS.from_documents(split_docs, embeddings)
    vectorstore.save_local(FAISS_INDEX_PATH)


# 🔷 Search FAISS index
def search_faiss(query):
    embeddings = OpenAIEmbeddings()
    vectorstore = FAISS.load_local(FAISS_INDEX_PATH, embeddings)
    docs = vectorstore.similarity_search(query, k=3)
    return "\n".join([doc.page_content for doc in docs])


# 🔷 Call Mistral LLM
def call_mistral(prompt):
    openai.api_key = st.secrets["MISTRAL_API_KEY"]

    response = openai.ChatCompletion.create(
        model="mistral-large-latest",
        messages=[
            {"role": "system", "content": "You are a helpful assistant. Answer general or document-related questions. If data is tabular, reply in Markdown table."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message["content"]


# 🔷 Compose Context & Get Answer
def generate_answer(user_query):
    sql_df = query_mysql("SELECT * FROM ap_invoices ORDER BY date DESC LIMIT 5;")

    doc_context = search_faiss(user_query)

    context = f"Relevant documents:\n{doc_context}"

    full_prompt = f"{context}\n\nAnswer the user’s question: {user_query}. If possible, use a Markdown table."
    answer = call_mistral(full_prompt)

    return sql_df, answer
