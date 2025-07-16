import mysql.connector
import requests
import openai
import pandas as pd
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from langchain.embeddings.openai import OpenAIEmbeddings
import os

DB_CONFIG = {
    'host': "118.139.183.37",
    'user': "kenaitech",
    'password': "Kenai@tech",
    'database': "RAG",
    'port': 3306
}

CLIENT_ID = "354e1512-776d-47b9-9278-3dc4c5e62e66"
CLIENT_SECRET = "uau8Q~~B3DnYJcNiFyB2DeaOGxkdt~al6Vqihcmt"
TENANT_ID = "787beb16-0600-4e9e-b636-9993f8d4b23a"
SHAREPOINT_HOST = "kenaiusa.sharepoint.com"
SITE_NAME = "ATeam"
DOC_LIB_PATH = "SharePoint/Docs2"
MISTRAL_API_KEY = "ycpI0FPUYnL8oA5aR1jdZyDxsAq3AM4j"

FAISS_INDEX_PATH = "faiss_index"

# MySQL Query - returns DataFrame
def query_mysql(sql):
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute(sql)
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    cursor.close()
    conn.close()
    df = pd.DataFrame(rows, columns=columns)
    return df

# Get Microsoft Graph Token
def get_graph_token():
    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": "https://graph.microsoft.com/.default"
    }
    resp = requests.post(url, data=data)
    resp.raise_for_status()
    return resp.json()["access_token"]

# List SharePoint Files
def list_sharepoint_files(token):
    headers = {"Authorization": f"Bearer {token}"}

    site_url = f"https://graph.microsoft.com/v1.0/sites/{SHAREPOINT_HOST}:/sites/{SITE_NAME}"
    site = requests.get(site_url, headers=headers).json()
    site_id = site['id']

    drive_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"
    drives = requests.get(drive_url, headers=headers).json()
    drive_id = drives['value'][0]['id']

    items_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{DOC_LIB_PATH}:/children"
    items = requests.get(items_url, headers=headers).json()

    return items['value']

# Download SharePoint files and return text content
def fetch_txt_files_from_sharepoint():
    token = get_graph_token()
    headers = {"Authorization": f"Bearer {token}"}
    files = list_sharepoint_files(token)
    texts = []

    for file in files:
        download_url = file['@microsoft.graph.downloadUrl']
        content = requests.get(download_url).text
        texts.append(Document(page_content=content, metadata={"name": file['name']}))
    return texts

# Reindex documents with FAISS
def reindex_documents():
    docs = fetch_txt_files_from_sharepoint()
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    split_docs = []
    for doc in docs:
        split_docs.extend(splitter.create_documents([doc.page_content]))

    embeddings = OpenAIEmbeddings()
    vectorstore = FAISS.from_documents(split_docs, embeddings)
    vectorstore.save_local(FAISS_INDEX_PATH)

# Search FAISS index
def search_faiss(query):
    embeddings = OpenAIEmbeddings()
    vectorstore = FAISS.load_local(FAISS_INDEX_PATH, embeddings)
    docs = vectorstore.similarity_search(query, k=3)
    return "\n".join([doc.page_content for doc in docs])

# Call Mistral LLM
def call_mistral(prompt):
    openai.api_key = MISTRAL_API_KEY

    response = openai.ChatCompletion.create(
        model="mistral-large-latest",
        messages=[
            {"role": "system", "content": "You are a helpful assistant. Answer general or document-related questions. If data is tabular, reply in Markdown table."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message["content"]

# Compose Context & Get Answer
def generate_answer(user_query):
    sql_df = query_mysql("SELECT * FROM ap_invoices ORDER BY date DESC LIMIT 5;")

    doc_context = search_faiss(user_query)

    context = f"Relevant documents:\n{doc_context}"

    full_prompt = f"{context}\n\nAnswer the user’s question: {user_query}. If possible, use a Markdown table."
    answer = call_mistral(full_prompt)

    return sql_df, answer
