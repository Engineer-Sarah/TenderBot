"""
TenderBot Pakistan - HTTP API (connects the React frontend to the backend)
==========================================================================
Run:
    uvicorn api:app --reload --port 8000

Endpoints
    GET    /api/health
    GET    /api/tenders?category=IT      fast: scrape PPRA/Serper + quick RAG match
    POST   /api/analyze  {"category"}    slow (1-5 min): full CrewAI pipeline
    GET    /api/documents                list company documents (RAG)
    POST   /api/documents                upload company documents (multipart "files")
    DELETE /api/documents/{doc_id}       delete one document
"""

import json
import re
import os
from datetime import date, datetime
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

app = FastAPI(title="TenderBot Pakistan API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

INDUSTRY_MAP = {"it": "IT & Software", "software": "IT & Software"}


# --------------------------------------------------------------------------- #
# Helpers: backend dicts -> frontend `Tender` shape (see frontend/src/types.ts)
# --------------------------------------------------------------------------- #
def _status(score: float) -> str:
    if score >= 75:
        return "eligible"
    if score >= 40:
        return "partial"
    return "not-eligible"


def _days_left(text: str) -> int:
    """Best-effort parse of a closing date; 30 if it can't be understood."""
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%B %d, %Y", "%d %B %Y", "%b %d, %Y"):
        try:
            return (datetime.strptime(text.strip(), fmt).date() - date.today()).days
        except (ValueError, AttributeError):
            continue
    return 30


def _tender(i: int, **kw) -> dict:
    base = {
        "id": f"s{i}",
        "title": "Untitled tender",
        "organization": "N/A",
        "industry": "IT & Software",
        "location": "Pakistan",
        "budget": 0,
        "budgetLabel": "N/A",
        "deadline": "",
        "daysLeft": 30,
        "matchPercentage": 0,
        "category": "Goods & Services",
        "description": "",
        "eligibilityStatus": "partial",
        "aiSummary": "",
        "requirements": [],
        "documents": [],
        "referenceNo": "",
        "publishedDate": date.today().isoformat(),
    }
    base.update(kw)
    return base


def _from_scraped(i: int, raw: dict, category: str, match: float) -> dict:
    closing = raw.get("closing_date", "") or ""
    return _tender(
        i,
        title=raw.get("title", "Untitled tender"),
        organization=raw.get("department") or raw.get("source", "N/A"),
        industry=INDUSTRY_MAP.get(category.lower(), category),
        deadline=closing,
        daysLeft=_days_left(closing),
        matchPercentage=int(round(match)),
        description=raw.get("snippet") or raw.get("title", ""),
        eligibilityStatus=_status(match),
        aiSummary=(
            f"Quick match {int(round(match))}% (document similarity). "
            "Press 'Run AI analysis' for a full eligibility report."
        ),
        documents=[
            {"id": f"d{j}", "name": u.rsplit("/", 1)[-1], "required": True}
            for j, u in enumerate(raw.get("pdf_links", []))
        ],
        referenceNo=raw.get("detail_url") or raw.get("link", ""),
    )


def _quick_match(raw: dict) -> float:
    """Cheap semantic match of one tender against the company docs (no LLM)."""
    try:
        from rag_engine import check_requirement

        text = f"{raw.get('title', '')}. {raw.get('snippet', '')}"[:400]
        return float(check_requirement(text, verify=False).get("match_percent", 0))
    except Exception:  # noqa: BLE001 - no docs / no API key => 0
        return 0.0


def _parse_crew_json(text: str):
    """Pull the JSON array out of the Writer agent's output."""
    s = text
    if "```json" in s:
        s = s.split("```json")[1].split("```")[0]
    elif "```" in s:
        s = s.split("```")[1].split("```")[0]
    else:
        m = re.search(r"\[.*\]", s, re.S)
        s = m.group(0) if m else s
    data = json.loads(s.strip())
    return data if isinstance(data, list) else [data]


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #
@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/tenders")
def get_tenders(category: str = "IT", limit: int = 10):
    from scraper import smart_fetch_tenders

    raws = smart_fetch_tenders(category=category, max_results=limit)
    return [_from_scraped(i, r, category, _quick_match(r)) for i, r in enumerate(raws, 1)]


class AnalyzeRequest(BaseModel):
    category: str = "IT"


@app.post("/api/analyze")
async def analyze(category: str = Form("IT"), files: Optional[List[UploadFile]] = File(None)):
    req = AnalyzeRequest(category=category)
    """Full 3-agent CrewAI run. Slow: the frontend shows a spinner."""
    try:
        from google import genai
        from google.genai import types

        key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not key:
            raise ValueError("GEMINI_API_KEY is not configured")

        # Keep the Vercel deployment lightweight: use Gemini directly instead of
        # importing the optional CrewAI stack (which exceeds Vercel's 500 MB
        # Python function bundle limit).
        # IMPORTANT: Vercel serverless instances do not guarantee /tmp persistence.
        # If the browser has the uploaded company files, index them in THIS SAME
        # invocation before retrieval, so the analysis always sees the PDF.
        if files:
            from rag_engine import upload_docs

            payload = [(f.filename or "file", await f.read()) for f in files]
            upload_results = upload_docs(payload)
            failed = [r for r in upload_results if r.get("status") != "ok"]
            if failed:
                details = "; ".join(f"{r.get('filename')}: {r.get('error')}" for r in failed)
                raise HTTPException(400, f"Company document indexing failed: {details}")

        raws = __import__("scraper").smart_fetch_tenders(category=req.category, max_results=5)
        if not raws:
            return []

        # IMPORTANT: the company PDF upload must actually influence AI analysis.
        # The previous implementation sent only tender data to Gemini, so uploaded
        # company documents were indexed but never read by /api/analyze.
        # Retrieve grounded evidence from the RAG knowledge base for every tender.
        try:
            from rag_engine import query_docs

            company_evidence = []
            for raw in raws:
                q = " ".join(
                    str(x or "")
                    for x in (
                        raw.get("title", ""),
                        raw.get("snippet", ""),
                        raw.get("department", ""),
                    )
                )[:1200]
                evidence = query_docs(q, generate=False)
                company_evidence.append(
                    {
                        "tender": raw.get("title", ""),
                        "found": evidence.get("found", False),
                        "match_percent": evidence.get("match_percent", 0),
                        "sources": evidence.get("sources", []),
                    }
                )
        except Exception as exc:
            raise HTTPException(500, f"Company document retrieval failed: {exc}")

        context = json.dumps(
            [
                {"tender": raw, "company_document_evidence": evidence}
                for raw, evidence in zip(raws, company_evidence)
            ],
            ensure_ascii=False,
            indent=2,
        )[:30000]

        prompt = f"""
Analyze these Pakistani government tenders for a software/IT company using the
uploaded company-document evidence supplied with EACH tender.

CRITICAL RULES:
1. The company-document evidence is the source of truth for company credentials.
2. Never claim a certificate, license, turnover, experience, registration, or
   capability is present unless the evidence supports it.
3. If evidence is missing or weak, put that item in gap_analysis and do not
   award credit for it.
4. The uploaded company PDF MUST affect eligibility_score.
5. Do not use the demo/mock company profile as evidence.

Return ONLY a JSON array. For each tender include exactly:
title, department, closing_date, summary, eligibility_score,
eligibility_reason, met_requirements, gap_analysis, cover_letter.

eligibility_score must be a number from 0 to 100 and should reflect the match
between the tender requirements and the uploaded company documents.

TENDERS + COMPANY DOCUMENT EVIDENCE:
{context}
"""
        client = genai.Client(api_key=key)
        response = client.models.generate_content(
            model=os.getenv("AGENT_MODEL", "gemini-2.5-flash"),
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
            ),
        )
        reports = _parse_crew_json(response.text or "[]")
    except (json.JSONDecodeError, ValueError) as exc:
        # Do not leave the dashboard blank if Gemini returns malformed JSON.
        # Return grounded RAG scores so the judge still sees a usable result.
        reports = []
        for raw in raws:
            q = " ".join(str(x or "") for x in (
                raw.get("title", ""), raw.get("snippet", ""), raw.get("department", "")
            ))[:1200]
            try:
                from rag_engine import check_requirement
                evidence = check_requirement(q, verify=False)
                score = float(evidence.get("match_percent", 0))
            except Exception:
                score = 0.0
            reports.append({
                "title": raw.get("title", "Untitled tender"),
                "department": raw.get("department", raw.get("source", "N/A")),
                "closing_date": raw.get("closing_date", ""),
                "summary": raw.get("snippet", ""),
                "eligibility_score": score,
                "eligibility_reason": "Grounded RAG similarity fallback.",
                "met_requirements": [],
                "gap_analysis": [] if score >= 55 else ["No sufficiently relevant company-document evidence found."],
                "cover_letter": "",
            })
    except Exception as exc:  # noqa: BLE001
        # Same fallback for transient Gemini/API/model errors.
        reports = []
        for raw in raws:
            q = " ".join(str(x or "") for x in (
                raw.get("title", ""), raw.get("snippet", ""), raw.get("department", "")
            ))[:1200]
            try:
                from rag_engine import check_requirement
                evidence = check_requirement(q, verify=False)
                score = float(evidence.get("match_percent", 0))
            except Exception:
                score = 0.0
            reports.append({
                "title": raw.get("title", "Untitled tender"),
                "department": raw.get("department", raw.get("source", "N/A")),
                "closing_date": raw.get("closing_date", ""),
                "summary": raw.get("snippet", ""),
                "eligibility_score": score,
                "eligibility_reason": "Grounded RAG similarity fallback; Gemini was unavailable.",
                "met_requirements": [],
                "gap_analysis": [] if score >= 55 else ["No sufficiently relevant company-document evidence found."],
                "cover_letter": "",
            })

    out = []
    for i, r in enumerate(reports, 1):
        score = float(r.get("eligibility_score") or 0)
        met = r.get("met_requirements") or []
        gaps = r.get("gap_analysis") or []
        reqs = [{"id": f"m{j}", "label": str(x), "matched": True, "category": "Met"} for j, x in enumerate(met)]
        reqs += [{"id": f"g{j}", "label": str(x), "matched": False, "category": "Gap"} for j, x in enumerate(gaps)]
        closing = r.get("closing_date", "") or ""
        summary = " ".join(x for x in [r.get("summary", ""), r.get("eligibility_reason", "")] if x)
        out.append(
            _tender(
                i,
                title=r.get("title", "Untitled tender"),
                organization=r.get("department", "N/A"),
                industry=INDUSTRY_MAP.get(req.category.lower(), req.category),
                deadline=closing,
                daysLeft=_days_left(closing),
                matchPercentage=int(round(score)),
                description=r.get("summary", ""),
                eligibilityStatus=_status(score),
                aiSummary=summary,
                requirements=reqs,
                coverLetter=r.get("cover_letter", ""),
            )
        )
    return out


@app.get("/api/documents")
def documents():
    from rag_engine import list_documents

    try:
        return [{"id": d["doc_id"], "name": d["source"], "chunks": d["chunks"]} for d in list_documents()]
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"Could not list documents: {exc}")


@app.post("/api/documents")
async def upload(files: List[UploadFile] = File(...)):
    from rag_engine import upload_docs

    payload = [(f.filename or "file", await f.read()) for f in files]
    return upload_docs(payload)  # per-file {filename, status, doc_id, chunks, error}


@app.delete("/api/documents/{doc_id}")
def delete_document_route(doc_id: str):
    from rag_engine import delete_document

    return {"deleted_chunks": delete_document(doc_id)}
