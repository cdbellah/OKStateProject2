import os
import io
import requests
import streamlit as st
from pypdf import PdfReader
from docx import Document
from bs4 import BeautifulSoup


# -----------------------------
# Helper: extract text from files
# -----------------------------
def get_file_text(uploaded_file):
    """
    Return plain text from an uploaded file.
    Supports: .txt, .pdf, .docx, .html/.htm
    """
    if uploaded_file is None:
        return ""

    name = uploaded_file.name.lower()
    uploaded_file.seek(0)  # reset pointer

    # TXT
    if name.endswith(".txt"):
        try:
            return uploaded_file.read().decode("utf-8", errors="ignore")
        except AttributeError:
            # sometimes it's already str
            return uploaded_file.read()

    # PDF
    if name.endswith(".pdf"):
        reader = PdfReader(io.BytesIO(uploaded_file.read()))
        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            text_parts.append(page_text)
        return "\n".join(text_parts)

    # DOCX
    if name.endswith(".docx"):
        doc = Document(io.BytesIO(uploaded_file.read()))
        paragraphs = [p.text for p in doc.paragraphs]
        return "\n".join(paragraphs)

    # HTML / HTM
    if name.endswith(".html") or name.endswith(".htm"):
        raw = uploaded_file.read()
        try:
            decoded = raw.decode("utf-8", errors="ignore")
        except AttributeError:
            decoded = raw
        soup = BeautifulSoup(decoded, "html.parser")
        return soup.get_text(separator="\n")

    # Fallback
    return f"[Unsupported file type for {uploaded_file.name}]"


# -----------------------------
# Hosted LLM call (replaces local Ollama)
# -----------------------------
def ask_ollama(model_name: str, question: str, context: str) -> str:
    """
    Call a hosted LLM via OpenRouter instead of local Ollama.

    Priority for API key:
    1) st.secrets["OPENROUTER_API_KEY"] (Streamlit Cloud)
    2) environment variable OPENROUTER_API_KEY (local dev)
    """

    # Try Streamlit secrets first (for deployment)
    api_key = None
    try:
        if "OPENROUTER_API_KEY" in st.secrets:
            api_key = st.secrets["OPENROUTER_API_KEY"]
    except Exception:
        # st.secrets may not exist locally; ignore
        pass

    # Fallback to environment variable (local dev)
    if not api_key:
        api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key:
        return (
            "Error: No OpenRouter API key found.\n\n"
            "Set OPENROUTER_API_KEY in your environment, or add it to "
            "Streamlit secrets as OPENROUTER_API_KEY."
        )

    url = "https://openrouter.ai/api/v1/chat/completions"

    # Build user message with optional context
    if context.strip():
        user_message = f"Context:\n{context}\n\nQuestion: {question}"
    else:
        user_message = question

    data = {
        "model": model_name,  # e.g. "meta-llama/llama-3.1-8b-instruct"
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.2,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "X-Title": "OKStateProject2-App",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=120)
        response.raise_for_status()
        json_data = response.json()
        return json_data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Error calling hosted LLM API: {e}"


# -----------------------------
# Streamlit UI
# -----------------------------
def main():
    st.set_page_config(page_title="OKState Project 2", page_icon="📄", layout="wide")

    st.title("OKState Project 2 – Document Question Answering")
    st.write(
        "Upload one or more documents, enter a question, and the app will use a "
        "hosted LLM (via OpenRouter) to answer using the document content as context."
    )

    # Layout: sidebar-ish controls and main area
    col_left, col_right = st.columns([1, 2])

    with col_left:
        st.subheader("Model & Question")

        model_name = st.selectbox(
            "Choose a model",
            options=[
                "meta-llama/llama-3.1-8b-instruct",
                "qwen/qwen-2.5-7b-instruct",
                "mistralai/mistral-7b-instruct",
            ],
            index=0,
            help="These are common, free-tier-friendly models on OpenRouter.",
        )

        question = st.text_area(
            "Your question",
            placeholder="Type your question about the uploaded document(s) here...",
            height=120,
        )

        submit = st.button("Ask", type="primary")

    with col_right:
        st.subheader("Upload documents")
        uploaded_files = st.file_uploader(
            "Upload .txt, .pdf, .docx, or .html files",
            type=["txt", "pdf", "docx", "html", "htm"],
            accept_multiple_files=True,
        )

        if uploaded_files:
            st.caption("Files selected:")
            for f in uploaded_files:
                st.write(f"- {f.name}")

    # When user clicks "Ask"
    if submit:
        if not question.strip():
            st.warning("Please enter a question before asking.")
            return

        with st.spinner("Reading documents and contacting the hosted LLM..."):
            context = ""

            # Build combined context from all uploaded files
            if uploaded_files:
                for f in uploaded_files:
                    text = get_file_text(f)
                    context += f"\n\n--- {f.name} ---\n{text}"

            answer = ask_ollama(model_name, question, context)

        st.markdown("---")
        st.subheader("Result")
        st.write("**Question:** ", question)
        st.markdown("**Answer:**")
        st.write(answer)


if __name__ == "__main__":
    main()