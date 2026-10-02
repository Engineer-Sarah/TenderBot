# rag_engine.py - Company Knowledge Base (Backend Person 1)

Company ke documents (NTN, PEC, audit report, experience letters) yaad rakhta hai aur
**sirf unhi documents se** jawab deta hai. Agar info documents me nahi hai to LLM ko call hi
nahi karta -> hallucination impossible.

## Setup
```bash
pip install -r requirements.txt
cp .env.example .env        # GEMINI_API_KEY daalo
echo -e ".env\nchroma_db/" >> .gitignore
python -m pytest test_rag_engine.py -v     # 22 offline tests, no API key needed
```

## Flow
`upload_docs` -> read (pypdf / python-docx / txt) -> `chunk_text` (500 words, 50 overlap, page-aware)
-> `create_embeddings` (Gemini `gemini-embedding-001`, 768-d) -> ChromaDB (persistent, cosine)
-> `query_docs` / `check_requirement` (embed query -> top-k search -> grounded LLM answer)

## API for Person 2 / main.py
```python
from rag_engine import upload_docs, query_docs, check_requirement, list_documents

upload_docs(["ntn.pdf", "pec.pdf"], company_id="demo")          # also accepts Streamlit UploadedFile
query_docs("Hamari company ke paas PEC license hai?", "demo")
check_requirement("Minimum annual turnover PKR 5 crore", "demo") # <- Matcher agent tool
```

### `check_requirement()` returns
```json
{
  "requirement": "PEC license category C5",
  "status": "partial",            // "met" | "partial" | "missing"
  "match_percent": 82.4,          // best-evidence semantic similarity 0-100
  "reason": "Company holds C6, tender needs C5.",
  "evidence": [{"source": "pec.pdf", "pages": "1", "similarity": 0.824, "snippet": "..."}]
}
```
Overall eligibility % (for the Writer agent) = mean of per-requirement scores, e.g.
met=1.0, partial=0.5, missing=0.

### `query_docs()` returns
`{question, answer, found, match_percent, confidence ("high"|"medium"|"low"|"none"), sources, warning}`

### `upload_docs()` returns (one dict per file, never raises)
`{filename, status: "ok"|"error", doc_id, chunks, pages, error}`

## Notes
* One Chroma collection per `company_id` (data isolation).
* Re-uploading the same file is safe (content-hash ids -> upsert).
* Scanned/image PDFs have no text layer -> clear error message (OCR not supported).
* Thresholds `MIN_SIMILARITY=0.55` / strong `0.75` are tunable via env; tune them on your real docs.
* Uses the current `google-genai` SDK (the older `google-generativeai` package is deprecated).
