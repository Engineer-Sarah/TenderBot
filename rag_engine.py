"""
rag_engine.py - Company Knowledge Base (RAG Engine)
===================================================
TenderBot Pakistan - Backend Person 1

Responsibility
--------------
Remember the company's documents (NTN, PEC certificate, audit reports, past
experience letters ...) and answer questions / verify tender requirements
using ONLY those documents (retrieval-augmented generation, no hallucination).

Pipeline
--------
    upload_docs()        read PDF / DOCX / TXT        (pypdf, python-docx)
        -> chunk_text()  500-word chunks, 50-word overlap, page-aware
        -> create_embeddings()  Gemini embeddings -> ChromaDB (persistent)
    query_docs()         embed question -> vector search -> grounded answer
    check_requirement()  requirement -> evidence -> verdict met/partial/missing
                         (this is the function Person 2's Matcher agent calls)

Public API (what Person 2 / main.py needs)
------------------------------------------
    from rag_engine import (upload_docs, query_docs, check_requirement,
                            list_documents, delete_document, clear_company)

Environment variables
---------------------
    GEMINI_API_KEY (or GOOGLE_API_KEY)   required
    CHROMA_DIR           default "./chroma_db"
    EMBED_MODEL          default "gemini-embedding-001"
    EMBED_DIM            default 768
    LLM_MODEL            default "gemini-2.5-flash"
    CHUNK_WORDS          default 500
    CHUNK_OVERLAP        default 50
    MIN_SIMILARITY       default 0.55   (below this => "not found in documents")
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import logging
import math
import os
import re
import time
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Sequence, Tuple, Union

from pypdf import PdfReader

try:  # optional: load .env if python-dotenv is installed
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass

logger = logging.getLogger("rag_engine")
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
CHROMA_DIR = os.getenv("CHROMA_DIR", "./chroma_db")
EMBED_MODEL = os.getenv("EMBED_MODEL", "gemini-embedding-001")
EMBED_DIM = int(os.getenv("EMBED_DIM", "768"))
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-3.8-flash")
CHUNK_WORDS = int(os.getenv("CHUNK_WORDS", "500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))
MIN_SIMILARITY = float(os.getenv("MIN_SIMILARITY", "0.55"))
STRONG_SIMILARITY = 0.75

EMBED_BATCH_SIZE = 50  # Gemini allows up to 100 texts per request; stay safe
MAX_RETRIES = 4
MAX_FILE_BYTES = 25 * 1024 * 1024  # 25 MB per file
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}

FileInput = Union[str, os.PathLike, Tuple[str, bytes], Any]  # path | (name, bytes) | file-like


# --------------------------------------------------------------------------- #
# Exceptions
# --------------------------------------------------------------------------- #
class RAGError(Exception):
    """Base class for all rag_engine errors."""


class RAGConfigError(RAGError):
    """Missing / invalid configuration (e.g. no API key)."""


class DocumentReadError(RAGError):
    """A document could not be read or contains no extractable text."""


class EmbeddingError(RAGError):
    """Embedding API failed after retries."""


# --------------------------------------------------------------------------- #
# Pure helpers (no external services - easy to unit test)
# --------------------------------------------------------------------------- #
def _window_indices(n: int, size: int, overlap: int) -> Iterator[Tuple[int, int]]:
    """Yield (start, end) word-index windows covering n words with overlap."""
    if size <= 0:
        raise ValueError("chunk size must be > 0")
    if overlap < 0 or overlap >= size:
        raise ValueError("overlap must be >= 0 and < chunk size")
    start = 0
    while start < n:
        end = min(start + size, n)
        yield start, end
        if end == n:
            break
        start = end - overlap


def chunk_text(text: str, chunk_size: int = CHUNK_WORDS, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split text into chunks of `chunk_size` words with `overlap` words shared
    between neighbouring chunks (so a sentence cut at a boundary is not lost)."""
    words = text.split()
    return [" ".join(words[s:e]) for s, e in _window_indices(len(words), chunk_size, overlap)]


def _chunk_pages(
    pages: Sequence[Tuple[int, str]], chunk_size: int = CHUNK_WORDS, overlap: int = CHUNK_OVERLAP
) -> List[Dict[str, Any]]:
    """Page-aware chunking. `pages` = [(page_number, page_text), ...].
    Returns [{"text", "page_start", "page_end"}, ...] so answers can cite pages."""
    words: List[str] = []
    word_page: List[int] = []
    for page_no, page_text in pages:
        for w in page_text.split():
            words.append(w)
            word_page.append(page_no)

    chunks: List[Dict[str, Any]] = []
    for s, e in _window_indices(len(words), chunk_size, overlap):
        chunks.append(
            {
                "text": " ".join(words[s:e]),
                "page_start": word_page[s],
                "page_end": word_page[e - 1],
            }
        )
    return chunks


def _normalize(vec: Sequence[float]) -> List[float]:
    norm = math.sqrt(sum(v * v for v in vec))
    return [float(v) for v in vec] if norm == 0 else [float(v) / norm for v in vec]


def _safe_collection_name(company_id: str) -> str:
    """Chroma names: 3-63 chars, [a-zA-Z0-9._-], start/end alphanumeric."""
    cleaned = re.sub(r"[^a-zA-Z0-9_-]", "_", str(company_id).strip()) or "default"
    name = f"company_{cleaned}"[:63]
    return name.rstrip("_-.") or "company_default"


def _label(similarity: float) -> str:
    if similarity >= STRONG_SIMILARITY:
        return "high"
    if similarity >= MIN_SIMILARITY:
        return "medium"
    return "low"


# --------------------------------------------------------------------------- #
# Document reading
# --------------------------------------------------------------------------- #
def _read_input(file: FileInput) -> Tuple[str, bytes]:
    """Normalise path / (name, bytes) / file-like (Streamlit UploadedFile) -> (name, bytes)."""
    if isinstance(file, tuple) and len(file) == 2:
        name, data = file
        return str(name), bytes(data)
    if isinstance(file, (str, os.PathLike)):
        path = Path(file)
        if not path.is_file():
            raise DocumentReadError(f"File not found: {path}")
        return path.name, path.read_bytes()
    if hasattr(file, "read") and hasattr(file, "name"):
        if hasattr(file, "seek"):
            try:
                file.seek(0)
            except Exception:  # noqa: BLE001
                pass
        data = file.read()
        if isinstance(data, str):
            data = data.encode("utf-8")
        return Path(str(file.name)).name, data
    raise DocumentReadError(f"Unsupported input type: {type(file).__name__}")


def _extract_pdf(data: bytes) -> List[Tuple[int, str]]:
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            if not reader.decrypt(""):
                raise DocumentReadError("PDF is password protected.")
        pages = []
        for i, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text() or ""
            except Exception as exc:  # noqa: BLE001  (one bad page must not kill the file)
                logger.warning("Could not read PDF page %d: %s", i, exc)
                text = ""
            pages.append((i, text))
        return pages
    except DocumentReadError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise DocumentReadError(f"Invalid or corrupted PDF: {exc}") from exc


def _extract_docx(data: bytes) -> List[Tuple[int, str]]:
    try:
        from docx import Document  # python-docx

        doc = Document(io.BytesIO(data))
    except Exception as exc:  # noqa: BLE001
        raise DocumentReadError(f"Invalid or corrupted DOCX: {exc}") from exc

    parts = [p.text for p in doc.paragraphs if p.text.strip()]
    for table in doc.tables:  # certificates / experience lists are often tables
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells if c.text.strip()]
            if cells:
                parts.append(" | ".join(cells))
    return [(1, "\n".join(parts))]


def _extract_txt(data: bytes) -> List[Tuple[int, str]]:
    for enc in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            return [(1, data.decode(enc))]
        except (UnicodeDecodeError, UnicodeError):
            continue
    return [(1, data.decode("utf-8", errors="ignore"))]


def _extract_pages(name: str, data: bytes) -> List[Tuple[int, str]]:
    ext = Path(name).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise DocumentReadError(
            f"Unsupported file type '{ext}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )
    if not data:
        raise DocumentReadError("File is empty.")
    if len(data) > MAX_FILE_BYTES:
        raise DocumentReadError(f"File too large (> {MAX_FILE_BYTES // (1024 * 1024)} MB).")

    pages = {".pdf": _extract_pdf, ".docx": _extract_docx, ".txt": _extract_txt}[ext](data)
    if not any(t.strip() for _, t in pages):
        raise DocumentReadError(
            "No extractable text found. The file looks like a scanned image - "
            "please upload a text-based PDF (OCR is not supported)."
        )
    return pages


# --------------------------------------------------------------------------- #
# Default (real) backends - imported lazily so the module imports without them
# --------------------------------------------------------------------------- #
def _api_key() -> str:
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        raise RAGConfigError("Set GEMINI_API_KEY (or GOOGLE_API_KEY) in your environment / .env file.")
    return key


class GeminiBackend:
    """Thin wrapper over the google-genai SDK: embeddings + text generation."""

    def __init__(self) -> None:
        self._client = None

    @property
    def client(self):
        if self._client is None:
            try:
                from google import genai
            except ImportError as exc:  # pragma: no cover
                raise RAGConfigError("Install the SDK: pip install google-genai") from exc
            self._client = genai.Client(api_key=_api_key())
        return self._client

    def embed(self, texts: List[str], task_type: str) -> List[List[float]]:
        from google.genai import types

        vectors: List[List[float]] = []
        for i in range(0, len(texts), EMBED_BATCH_SIZE):
            batch = texts[i : i + EMBED_BATCH_SIZE]
            for attempt in range(MAX_RETRIES):
                try:
                    resp = self.client.models.embed_content(
                        model=EMBED_MODEL,
                        contents=batch,
                        config=types.EmbedContentConfig(
                            task_type=task_type, output_dimensionality=EMBED_DIM
                        ),
                    )
                    got = [list(e.values) for e in resp.embeddings]
                    if len(got) != len(batch):
                        raise EmbeddingError("Embedding count mismatch from API.")
                    vectors.extend(got)
                    break
                except RAGConfigError:
                    raise
                except Exception as exc:  # noqa: BLE001
                    if attempt == MAX_RETRIES - 1:
                        raise EmbeddingError(f"Gemini embedding failed: {exc}") from exc
                    wait = 2**attempt
                    logger.warning("Embedding retry %d in %ds (%s)", attempt + 1, wait, exc)
                    time.sleep(wait)
        return vectors

    def generate(self, prompt: str, system: str, json_mode: bool = False) -> str:
        from google.genai import types

        cfg = {"system_instruction": system, "temperature": 0.1}
        if json_mode:
            cfg["response_mime_type"] = "application/json"
        last: Optional[Exception] = None
        for attempt in range(MAX_RETRIES):
            try:
                resp = self.client.models.generate_content(
                    model=LLM_MODEL, contents=prompt, config=types.GenerateContentConfig(**cfg)
                )
                return (resp.text or "").strip()
            except RAGConfigError:
                raise
            except Exception as exc:  # noqa: BLE001
                last = exc
                time.sleep(2**attempt)
        raise RAGError(f"Gemini generation failed: {last}")


def _default_chroma_client(path: str):
    try:
        import chromadb
        from chromadb.config import Settings
    except ImportError as exc:  # pragma: no cover
        raise RAGConfigError("Install ChromaDB: pip install chromadb") from exc
    Path(path).mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=path, settings=Settings(anonymized_telemetry=False))


# --------------------------------------------------------------------------- #
# Prompts
# --------------------------------------------------------------------------- #
_ANSWER_SYSTEM = (
    "You are the company-records assistant of TenderBot Pakistan. Answer ONLY from the "
    "CONTEXT excerpts taken from the company's own documents. If the context does not contain "
    "the answer, say clearly that it is not found in the company documents - never guess or "
    "invent facts, numbers, dates or certificate details. Reply in the same language/script as "
    "the question (English, Urdu or Roman Urdu). Be concise and cite sources like "
    "[file.pdf p.3]."
)

_VERIFY_SYSTEM = (
    "You verify whether a company satisfies ONE tender requirement using ONLY the CONTEXT "
    "excerpts from the company's documents. Be strict: compare numbers, categories, dates and "
    "validity periods exactly (e.g. PEC category C6 does not satisfy C5 if C5 is required - "
    "check the rule in the requirement itself). Respond with JSON only: "
    '{"verdict": "met" | "partial" | "missing", "reason": "<one or two sentences>"}. '
    '"met" = clear evidence the requirement is satisfied; "partial" = related evidence but '
    'incomplete, expired, or insufficient; "missing" = no relevant evidence.'
)


def _format_context(hits: List[Dict[str, Any]]) -> str:
    blocks = []
    for h in hits:
        pages = h["pages"]
        blocks.append(f"[{h['source']} p.{pages}]\n{h['text']}")
    return "\n\n---\n\n".join(blocks)


# --------------------------------------------------------------------------- #
# The engine
# --------------------------------------------------------------------------- #
class RAGEngine:
    """Company knowledge base. One Chroma collection per company_id, so several
    companies (or a demo + a real company) never see each other's documents."""

    def __init__(
        self,
        persist_dir: str = CHROMA_DIR,
        chroma_client: Any = None,
        embed_fn: Optional[Callable[[List[str], str], List[List[float]]]] = None,
        generate_fn: Optional[Callable[..., str]] = None,
    ) -> None:
        self._persist_dir = persist_dir
        self._chroma = chroma_client
        self._gemini = GeminiBackend()
        self._embed_fn = embed_fn or self._gemini.embed
        self._generate_fn = generate_fn or self._gemini.generate

    # -- internals ---------------------------------------------------------- #
    @property
    def chroma(self):
        if self._chroma is None:
            self._chroma = _default_chroma_client(self._persist_dir)
        return self._chroma

    def _collection(self, company_id: str):
        return self.chroma.get_or_create_collection(
            name=_safe_collection_name(company_id), metadata={"hnsw:space": "cosine"}
        )

    def _embed(self, texts: List[str], task_type: str) -> List[List[float]]:
        return [_normalize(v) for v in self._embed_fn(texts, task_type)]

    # -- 1. upload_docs ----------------------------------------------------- #
    def upload_docs(
        self, files: Union[FileInput, Sequence[FileInput]], company_id: str = "default"
    ) -> List[Dict[str, Any]]:
        """Read, chunk, embed and store one or many files.

        `files` may be a path, a (filename, bytes) tuple, a Streamlit UploadedFile /
        file-like object, or a list of those. Never raises for a single bad file -
        every file gets a result dict so the UI can show per-file status:
            {"filename", "status": "ok"|"error", "doc_id", "chunks", "pages", "error"}
        Re-uploading the same file is safe (idempotent - same content => same ids).
        """
        if (
            isinstance(files, tuple)
            and len(files) == 2
            and isinstance(files[0], str)
            and isinstance(files[1], (bytes, bytearray))
        ):
            files = [files]
        elif isinstance(files, (str, os.PathLike)) or hasattr(files, "read"):
            files = [files]  # type: ignore[list-item]

        results: List[Dict[str, Any]] = []
        for f in files:  # type: ignore[union-attr]
            result: Dict[str, Any] = {
                "filename": None,
                "status": "error",
                "doc_id": None,
                "chunks": 0,
                "pages": 0,
                "error": None,
            }
            try:
                if isinstance(f, (str, os.PathLike)):
                    result["filename"] = Path(f).name  # so errors still show the name
                name, data = _read_input(f)
                result["filename"] = name
                pages = _extract_pages(name, data)
                result["pages"] = len(pages)

                doc_id = hashlib.sha256(data).hexdigest()[:16]
                result["doc_id"] = doc_id

                chunks = _chunk_pages(pages)
                n = self.create_embeddings(
                    chunks=[c["text"] for c in chunks],
                    metadatas=[
                        {
                            "source": name,
                            "doc_id": doc_id,
                            "chunk_index": i,
                            "page_start": c["page_start"],
                            "page_end": c["page_end"],
                        }
                        for i, c in enumerate(chunks)
                    ],
                    ids=[f"{doc_id}:{i}" for i in range(len(chunks))],
                    company_id=company_id,
                )
                result.update(status="ok", chunks=n)
                logger.info("Indexed %s (%d chunks) for company '%s'", name, n, company_id)
            except RAGError as exc:
                result["error"] = str(exc)
                logger.error("Failed to index %s: %s", result["filename"], exc)
            except Exception as exc:  # noqa: BLE001
                result["error"] = f"Unexpected error: {exc}"
                logger.exception("Unexpected error indexing %s", result["filename"])
            results.append(result)
        return results

    # -- 3. create_embeddings ------------------------------------------------ #
    def create_embeddings(
        self,
        chunks: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str],
        company_id: str = "default",
    ) -> int:
        """Embed chunks with Gemini and upsert them into ChromaDB. Returns #stored."""
        if not (len(chunks) == len(metadatas) == len(ids)):
            raise ValueError("chunks, metadatas and ids must have the same length")
        if not chunks:
            return 0
        vectors = self._embed(chunks, "RETRIEVAL_DOCUMENT")
        
        # Force embeddings into plain Python floats before passing to Chroma.
        vectors = [[float(x) for x in vector] for vector in vectors]

        self._collection(company_id).upsert(
            ids=[str(x) for x in ids],
            documents=[str(x) for x in chunks],
            embeddings=vectors,
            metadatas=metadatas,
        )
        return len(chunks)

    # -- retrieval ----------------------------------------------------------- #
    def search_docs(
        self, question: str, company_id: str = "default", top_k: int = 4
    ) -> List[Dict[str, Any]]:
        """Vector similarity search. Returns hits sorted best-first, each:
        {"text", "source", "pages", "similarity" (0-1), "doc_id"}"""
        question = (question or "").strip()
        if not question:
            raise ValueError("question must not be empty")
        top_k = max(1, int(top_k))

        coll = self._collection(company_id)
        total = coll.count()
        if total == 0:
            return []
        q_vec = self._embed([question], "RETRIEVAL_QUERY")[0]
        res = coll.query(
            query_embeddings=[q_vec],
            n_results=min(top_k, total),
            include=["documents", "metadatas", "distances"],
        )
        hits = []
        for text, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
            ps, pe = meta.get("page_start"), meta.get("page_end")
            pages = str(ps) if ps == pe else f"{ps}-{pe}"
            hits.append(
                {
                    "text": text,
                    "source": meta.get("source", "unknown"),
                    "pages": pages,
                    "doc_id": meta.get("doc_id"),
                    "similarity": round(max(0.0, min(1.0, 1.0 - float(dist))), 4),
                }
            )
        hits.sort(key=lambda h: h["similarity"], reverse=True)
        return hits

    @staticmethod
    def _public_sources(hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [
            {
                "source": h["source"],
                "pages": h["pages"],
                "similarity": h["similarity"],
                "snippet": (h["text"][:300] + "...") if len(h["text"]) > 300 else h["text"],
            }
            for h in hits
        ]

    # -- 4. query_docs ------------------------------------------------------- #
    def query_docs(
        self,
        question: str,
        company_id: str = "default",
        top_k: int = 4,
        generate: bool = True,
    ) -> Dict[str, Any]:
        """Answer a question from the company's documents.

        Returns:
            {"question", "answer", "found", "match_percent", "confidence",
             "sources": [{"source","pages","similarity","snippet"}], "warning"}
        If nothing relevant is found, `answer` says so WITHOUT calling the LLM
        (guaranteed no hallucination).
        """
        hits = self.search_docs(question, company_id, top_k)
        best = hits[0]["similarity"] if hits else 0.0
        relevant = [h for h in hits if h["similarity"] >= MIN_SIMILARITY]
        out: Dict[str, Any] = {
            "question": question,
            "answer": None,
            "found": bool(relevant),
            "match_percent": round(best * 100, 1),
            "confidence": _label(best) if hits else "none",
            "sources": self._public_sources(relevant or hits[:1]),
            "warning": None,
        }
        if not hits:
            out["answer"] = "No company documents have been uploaded yet."
            return out
        if not relevant:
            out["answer"] = "Yeh information company ke uploaded documents me nahi mili."
            return out
        if not generate:
            return out

        prompt = f"CONTEXT:\n{_format_context(relevant)}\n\nQUESTION: {question}\n\nANSWER:"
        try:
            out["answer"] = self._generate_fn(prompt, _ANSWER_SYSTEM)
        except RAGError as exc:
            out["warning"] = f"LLM unavailable, returning evidence only: {exc}"
            logger.error(out["warning"])
        return out

    # -- 5. check_requirement (used by Person 2's Matcher agent) ------------- #
    def check_requirement(
        self, requirement: str, company_id: str = "default", top_k: int = 4, verify: bool = True
    ) -> Dict[str, Any]:
        """Check ONE tender requirement against the company's documents.

        Returns:
            {"requirement", "status": "met"|"partial"|"missing", "match_percent",
             "reason", "evidence": [...sources...]}
        `match_percent` is the semantic similarity of the best evidence (0-100);
        `status` comes from an LLM that compares exact numbers/categories, with a
        similarity-only fallback if the LLM is down.
        """
        hits = self.search_docs(requirement, company_id, top_k)
        best = hits[0]["similarity"] if hits else 0.0
        relevant = [h for h in hits if h["similarity"] >= MIN_SIMILARITY]
        result: Dict[str, Any] = {
            "requirement": requirement,
            "status": "missing",
            "match_percent": round(best * 100, 1),
            "reason": "No relevant document found in the company knowledge base.",
            "evidence": self._public_sources(relevant),
        }
        if not relevant:
            return result

        # similarity-only fallback verdict
        result["status"] = "met" if best >= STRONG_SIMILARITY else "partial"
        result["reason"] = "Relevant document found (verdict based on similarity only)."
        if not verify:
            return result

        prompt = (
            f"CONTEXT:\n{_format_context(relevant)}\n\nREQUIREMENT: {requirement}\n\nJSON:"
        )
        try:
            raw = self._generate_fn(prompt, _VERIFY_SYSTEM, json_mode=True)
            parsed = json.loads(re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.M).strip())
            verdict = str(parsed.get("verdict", "")).lower()
            if verdict in {"met", "partial", "missing"}:
                result["status"] = verdict
                result["reason"] = str(parsed.get("reason", "")).strip() or result["reason"]
        except (RAGError, ValueError, AttributeError) as exc:
            logger.warning("Verdict LLM failed, using similarity fallback: %s", exc)
        return result

    # -- management ---------------------------------------------------------- #
    def list_documents(self, company_id: str = "default") -> List[Dict[str, Any]]:
        """One entry per uploaded document: {"doc_id", "source", "chunks"}."""
        data = self._collection(company_id).get(include=["metadatas"])
        docs: Dict[str, Dict[str, Any]] = {}
        for meta in data.get("metadatas") or []:
            d = docs.setdefault(
                meta["doc_id"], {"doc_id": meta["doc_id"], "source": meta["source"], "chunks": 0}
            )
            d["chunks"] += 1
        return sorted(docs.values(), key=lambda d: d["source"].lower())

    def delete_document(self, doc_id: str, company_id: str = "default") -> int:
        """Remove one document (all its chunks). Returns number of chunks removed."""
        coll = self._collection(company_id)
        existing = coll.get(where={"doc_id": doc_id}, include=[])
        n = len(existing.get("ids") or [])
        if n:
            coll.delete(where={"doc_id": doc_id})
        return n

    def clear_company(self, company_id: str = "default") -> None:
        """Delete the company's whole knowledge base."""
        try:
            self.chroma.delete_collection(_safe_collection_name(company_id))
        except Exception as exc:  # noqa: BLE001  (collection may not exist)
            logger.info("clear_company: nothing to delete (%s)", exc)

    def stats(self, company_id: str = "default") -> Dict[str, Any]:
        docs = self.list_documents(company_id)
        return {
            "company_id": company_id,
            "documents": len(docs),
            "chunks": sum(d["chunks"] for d in docs),
        }


# --------------------------------------------------------------------------- #
# Module-level convenience API (lazy singleton) - this is what main.py imports
# --------------------------------------------------------------------------- #
_engine: Optional[RAGEngine] = None


def get_engine() -> RAGEngine:
    global _engine
    if _engine is None:
        _engine = RAGEngine()
    return _engine


def upload_docs(files, company_id: str = "default"):
    return get_engine().upload_docs(files, company_id)


def create_embeddings(chunks, metadatas, ids, company_id: str = "default"):
    return get_engine().create_embeddings(chunks, metadatas, ids, company_id)


def query_docs(question: str, company_id: str = "default", top_k: int = 4, generate: bool = True):
    return get_engine().query_docs(question, company_id, top_k, generate)


def check_requirement(requirement: str, company_id: str = "default", top_k: int = 4, verify: bool = True):
    return get_engine().check_requirement(requirement, company_id, top_k, verify)


def list_documents(company_id: str = "default"):
    return get_engine().list_documents(company_id)


def delete_document(doc_id: str, company_id: str = "default"):
    return get_engine().delete_document(doc_id, company_id)


def clear_company(company_id: str = "default"):
    return get_engine().clear_company(company_id)


# --------------------------------------------------------------------------- #
# CLI for quick manual testing:
#   python rag_engine.py ingest ntn.pdf pec.pdf
#   python rag_engine.py ask "Hamari company ke paas PEC license hai?"
#   python rag_engine.py check "Minimum turnover PKR 5 crore"
#   python rag_engine.py list
# --------------------------------------------------------------------------- #
def _cli() -> None:
    p = argparse.ArgumentParser(description="TenderBot company RAG engine")
    p.add_argument("--company", default="default")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ingest").add_argument("files", nargs="+")
    sub.add_parser("ask").add_argument("question")
    sub.add_parser("check").add_argument("requirement")
    sub.add_parser("list")
    args = p.parse_args()

    if args.cmd == "ingest":
        out = upload_docs(args.files, args.company)
    elif args.cmd == "ask":
        out = query_docs(args.question, args.company)
    elif args.cmd == "check":
        out = check_requirement(args.requirement, args.company)
    else:
        out = list_documents(args.company)
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    _cli()
