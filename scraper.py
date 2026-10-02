"""
TenderBot Pakistan - PPRA Tender Scraper Module
================================================
Fetches active government tenders from:
  1. PPRA Pakistan website (direct HTML scraping)
  2. Serper API (Google Search fallback)

Author: Backend Person 2
"""

import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PPRA_BASE_URL = "https://www.ppra.org.pk"
PPRA_TENDERS_URL = f"{PPRA_BASE_URL}/tendernotices"
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")
SERPER_ENDPOINT = "https://google.serper.dev/search"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


# ---------------------------------------------------------------------------
# 1. Direct PPRA Website Scraper
# ---------------------------------------------------------------------------
def fetch_ppra_tenders(category: str = "IT", max_results: int = 10) -> list[dict]:
    """
    Scrape the PPRA Pakistan tender notices page for active tenders.

    Args:
        category: Filter keyword (e.g. 'IT', 'Software', 'Infrastructure').
        max_results: Maximum number of tenders to return.

    Returns:
        List of dicts with keys: title, department, published_date,
        closing_date, detail_url, source.
    """
    tenders: list[dict] = []

    try:
        print(f"[Scraper] Fetching tenders from PPRA website: {PPRA_TENDERS_URL}")
        response = requests.get(PPRA_TENDERS_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # PPRA renders tenders in HTML table rows.
        # We look for table rows inside the main content area.
        table = soup.find("table")
        if not table:
            # Fallback: look for any div-based listing
            rows = soup.find_all("div", class_=lambda c: c and "tender" in c.lower()) if soup else []
        else:
            rows = table.find_all("tr")[1:]  # skip header row

        for row in rows[:50]:  # scan up to 50 rows for matches
            cells = row.find_all("td") if row.name == "tr" else [row]

            if len(cells) >= 3:
                title = cells[0].get_text(strip=True)
                department = cells[1].get_text(strip=True) if len(cells) > 1 else "N/A"
                closing_date = cells[-1].get_text(strip=True)

                # Find detail link
                link_tag = row.find("a", href=True)
                detail_url = ""
                if link_tag:
                    href = link_tag["href"]
                    detail_url = href if href.startswith("http") else f"{PPRA_BASE_URL}{href}"
            elif len(cells) == 1:
                # Div-based layout fallback
                title = cells[0].get_text(strip=True)
                department = "N/A"
                closing_date = "N/A"
                link_tag = cells[0].find("a", href=True)
                detail_url = link_tag["href"] if link_tag else ""
            else:
                continue

            # Apply category keyword filter (case-insensitive)
            if category.lower() in title.lower():
                tenders.append({
                    "title": title,
                    "department": department,
                    "closing_date": closing_date,
                    "detail_url": detail_url,
                    "source": "PPRA Website",
                    "scraped_at": datetime.now().isoformat(),
                })

            if len(tenders) >= max_results:
                break

        print(f"[Scraper] Found {len(tenders)} tenders from PPRA (category: {category})")

    except requests.RequestException as e:
        print(f"[Scraper] PPRA scraping failed: {e}")
    except Exception as e:
        print(f"[Scraper] Unexpected error during PPRA scrape: {e}")

    return tenders


# ---------------------------------------------------------------------------
# 2. Serper API Fallback (Google Search)
# ---------------------------------------------------------------------------
def search_tenders_serper(query: str = "", category: str = "IT", max_results: int = 10) -> list[dict]:
    """
    Use Serper API (Google Search) to find PPRA tenders when direct
    scraping fails or returns empty results.

    Args:
        query: Custom search query. If empty, a default is constructed.
        category: Tender category keyword.
        max_results: Maximum results to return.

    Returns:
        List of dicts with keys: title, snippet, link, source.
    """
    if not SERPER_API_KEY:
        print("[Serper] No SERPER_API_KEY found in environment. Skipping search fallback.")
        return []

    if not query:
        query = f"PPRA Pakistan {category} tender 2024 2025 site:ppra.org.pk OR site:ppra.punjab.gov.pk"

    payload = json.dumps({
        "q": query,
        "num": max_results,
        "gl": "pk",       # geo-location: Pakistan
        "hl": "en",       # language: English
    })

    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json",
    }

    tenders: list[dict] = []

    try:
        print(f"[Serper] Searching: {query}")
        response = requests.post(SERPER_ENDPOINT, headers=headers, data=payload, timeout=15)
        response.raise_for_status()
        data = response.json()

        organic_results = data.get("organic", [])
        for item in organic_results[:max_results]:
            tenders.append({
                "title": item.get("title", "Untitled"),
                "snippet": item.get("snippet", ""),
                "link": item.get("link", ""),
                "source": "Serper (Google Search)",
                "scraped_at": datetime.now().isoformat(),
            })

        print(f"[Serper] Found {len(tenders)} results via Google Search")

    except requests.RequestException as e:
        print(f"[Serper] Search failed: {e}")
    except Exception as e:
        print(f"[Serper] Unexpected error: {e}")

    return tenders


# ---------------------------------------------------------------------------
# 3. Scrape Tender Detail Page
# ---------------------------------------------------------------------------
def scrape_tender_detail(url: str) -> dict:
    """
    Scrape an individual tender detail page to extract the full
    description, requirements, and any downloadable PDF links.

    Args:
        url: Full URL of the tender detail page.

    Returns:
        Dict with keys: url, full_text, pdf_links, requirements_raw.
    """
    result = {
        "url": url,
        "full_text": "",
        "pdf_links": [],
        "requirements_raw": "",
    }

    if not url:
        return result

    try:
        print(f"[Scraper] Fetching tender detail: {url}")
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove script and style tags for cleaner text
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        # Extract full visible text
        full_text = soup.get_text(separator="\n", strip=True)
        result["full_text"] = full_text[:10000]  # cap at 10k chars

        # Find PDF download links
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if href.lower().endswith(".pdf"):
                pdf_url = href if href.startswith("http") else f"{PPRA_BASE_URL}{href}"
                result["pdf_links"].append(pdf_url)

        # Attempt to find a requirements / eligibility section
        for heading in soup.find_all(["h2", "h3", "h4", "strong", "b"]):
            heading_text = heading.get_text(strip=True).lower()
            if any(kw in heading_text for kw in ["eligib", "requir", "qualif", "criteria"]):
                # Grab the next sibling content
                sibling = heading.find_next_sibling()
                if sibling:
                    result["requirements_raw"] += sibling.get_text(strip=True) + "\n"

        print(f"[Scraper] Detail extracted: {len(full_text)} chars, {len(result['pdf_links'])} PDFs found")

    except Exception as e:
        print(f"[Scraper] Detail scrape failed for {url}: {e}")

    return result


# ---------------------------------------------------------------------------
# 4. Combined Smart Fetch (Primary + Fallback)
# ---------------------------------------------------------------------------
def smart_fetch_tenders(category: str = "IT", max_results: int = 10) -> list[dict]:
    """
    Smart fetcher that tries PPRA direct scraping first, falls back to
    Serper API if no results are found.

    Args:
        category: Tender category keyword.
        max_results: Maximum results to return.

    Returns:
        Combined list of tender dicts.
    """
    print(f"\n{'='*60}")
    print(f"  TenderBot - Smart Fetch: category='{category}'")
    print(f"{'='*60}\n")

    # Step 1: Try direct PPRA scraping
    tenders = fetch_ppra_tenders(category=category, max_results=max_results)

    # Step 2: If no results, fall back to Serper Google Search
    if not tenders:
        print("[SmartFetch] PPRA scraping returned 0 results. Trying Serper fallback...")
        tenders = search_tenders_serper(category=category, max_results=max_results)

    # Step 3: If still empty, try a broader search
    if not tenders:
        print("[SmartFetch] Serper also returned 0 results. Trying broader search...")
        broader_query = f"Pakistan government {category} tender notice 2024 2025"
        tenders = search_tenders_serper(query=broader_query, max_results=max_results)

    if not tenders:
        print("[SmartFetch] WARNING: No tenders found from any source.")
    else:
        print(f"\n[SmartFetch] Total tenders fetched: {len(tenders)}")

    return tenders


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    results = smart_fetch_tenders(category="IT", max_results=5)
    print("\n--- Results ---")
    for i, t in enumerate(results, 1):
        print(f"\n[{i}] {t.get('title', 'N/A')}")
        print(f"    Source: {t.get('source', 'N/A')}")
        print(f"    Link:   {t.get('detail_url', t.get('link', 'N/A'))}")
