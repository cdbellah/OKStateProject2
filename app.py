import streamlit as st
import io
import requests
from pypdf import PdfReader
from docx import Document
from bs4 import BeautifulSoup

def get_file_text(uploaded_file):
    if uploaded_file is None:
        return ""

    name = uploaded_file.name.lower()
    uploaded_file.seek(0)

    # TXT
    if name.endswith(".txt"):
        try:
            return uploaded_file.read().decode("utf-8", errors="ignore")
        except:
            uploaded_file.seek(0)
            return uploaded_file.read().decode("latin-1", errors="ignore")
    # PDF
    elif name.endswith(".pdf"):
        text = ""
        reader = PdfReader(uploaded_file)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text
    # DOCX
    elif name.endswith(".docx"):
        bytes_data = io.BytesIO(uploaded_file.read())
        doc = Document(bytes_data)
        text = ""
        for para in doc.paragraphs:
            text += para.text + "\n"
        return text
    # HTML
    elif name.endswith(".html") or name.endswith(".htm"):
        raw = uploaded_file.read().decode("utf-8", errors="ignore")
        soup = BeautifulSoup(raw, "html.parser")
        return soup.get_text(separator="\n")
    # fallback
    else:
        return uploaded_file.read().decode("utf-8", errors="ignore")

def ask_ollama(model_name, question, context):
    url = "http://localhost:11434/api/chat"
    system_message = (
        "You are a helpful assistant. Use the document context if it helps. "
        "If you don't know from the context, say you don't know."
    )

    if context.strip() != "":
        user_message = "Context:\n" + context + "\n\nQuestion: " + question
    else:
        user_message = question

    data = {
        "model": model_name, 
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ],
        "stream": False
    }

    try:
        response = requests.post(url, json=data, timeout=120)
        response.raise_for_status()
        json_data = response.json()
        answer = json_data.get("message", {}).get("content", "")
        return answer
    except Exception as e:
        return f"Error talking to Ollama: {e}"

def main():
    st.title("Input to AI")
    question = st.text_area("Enter your question:", height=50)
    uploaded_files = st.file_uploader(
        "Upload attachment:",
        type=["txt", "pdf", "docx", "html", "htm"],
        accept_multiple_files=True
    )
    model_name = "llama3.2:1b"

    if st.button("Ask"):
        if question.strip() == "":
            st.warning("Please type a question first.")
        else:
            with st.spinner("Reading documents and contacting Ollama..."):
                context = ""
                if uploaded_files:
                    for f in uploaded_files:
                        text = get_file_text(f)
                        context += "\n--- " + f.name + " ---\n" + text
                
                answer = ask_ollama(model_name, question, context)
                st.write("Question:", question)
                st.subheader("Answer")
                st.write(answer)

if __name__ == "__main__":
    main()