# TendorBot Pakistan 🇵🇰

**AI-Powered PPRA Tender Automation Agent**

TendorBot is an AI-powered tender intelligence and compliance assistant designed to help Pakistani businesses analyze PPRA tenders, extract requirements, verify eligibility, identify missing documents, and automate tender preparation.

The system combines **Retrieval-Augmented Generation (RAG), semantic similarity search, document processing, and LLM-powered workflow automation** to turn lengthy tender documents into actionable compliance insights.

### Core Workflow

**Tender PDF → Requirement Extraction → Semantic Matching → Eligibility Analysis → Document Generation**

### Key Features

* 📄 PPRA tender PDF parsing and analysis
* 🔎 RAG-based retrieval from tender documents
* 🧠 LLM-powered requirement extraction
* 📋 Structured `tender_requirements.json` intermediate artifact
* 🏢 Company document knowledge base
* 📊 Semantic matching between tender requirements and company credentials
* ⚠️ Automated eligibility and compliance-gap detection
* 📑 Missing-document identification
* ✍️ AI-generated cover letters and submission checklists
* 🌐 English + Urdu support
* ⚡ Fast LLM inference with Groq

### Technology Stack

**Frontend:** Streamlit
**PDF Processing:** pypdf
**Vector Database:** FAISS
**Embeddings:** Sentence Transformers — `all-MiniLM-L6-v2`
**LLM:** Groq / Llama 3.3 70B
**Language:** Python
