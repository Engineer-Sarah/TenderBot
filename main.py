"""
TenderBot Pakistan - Main Entry Point
======================================
Integrates:
  - Person 1: RAG Engine (rag_engine.py)
  - Person 2: Scraper (scraper.py) + CrewAI Agents (agents.py)

Run this to execute the full TenderBot pipeline.

Usage:
    python main.py                        # default: IT category
    python main.py --category Software    # custom category
    python main.py --test-scraper         # test scraper only
    python main.py --test-rag             # test RAG only
"""

import os
import sys
import json
import argparse
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


def check_environment() -> bool:
    """Verify required API keys are configured."""
    print("\n[Setup] Checking environment configuration...")

    gemini_key = os.getenv("GEMINI_API_KEY", "")
    serper_key = os.getenv("SERPER_API_KEY", "")

    ok = True

    if not gemini_key or gemini_key == "your_gemini_api_key_here":
        print("  [WARNING] GEMINI_API_KEY not set. LLM agents will not work.")
        print("            Get your key at: https://aistudio.google.com/apikey")
        ok = False
    else:
        print(f"  [OK] GEMINI_API_KEY is configured (ends with ...{gemini_key[-4:]})")

    if not serper_key or serper_key == "your_serper_api_key_here":
        print("  [WARNING] SERPER_API_KEY not set. Search fallback will be unavailable.")
        print("            Get your key at: https://serper.dev/")
    else:
        print(f"  [OK] SERPER_API_KEY is configured (ends with ...{serper_key[-4:]})")

    return ok


def test_scraper(category: str = "IT"):
    """Test the scraper module independently."""
    from scraper import smart_fetch_tenders

    print(f"\n{'='*60}")
    print(f"  Testing Scraper Module - Category: {category}")
    print(f"{'='*60}")

    tenders = smart_fetch_tenders(category=category, max_results=5)

    if tenders:
        print(f"\nFound {len(tenders)} tenders:\n")
        for i, t in enumerate(tenders, 1):
            print(f"  [{i}] {t.get('title', 'N/A')}")
            print(f"      Dept: {t.get('department', 'N/A')}")
            print(f"      Source: {t.get('source', 'N/A')}")
            print(f"      Link: {t.get('detail_url', t.get('link', 'N/A'))}")
            print()
    else:
        print("\n  No tenders found. Check your internet connection and API keys.")


def test_rag():
    """Test the RAG engine module independently."""
    try:
        from rag_engine import query_docs
        print(f"\n{'='*60}")
        print("  Testing RAG Engine Module")
        print(f"{'='*60}")

        test_queries = [
            "What is the company PEC license category?",
            "Is the company NTN registered?",
            "What is the annual turnover?",
        ]

        for q in test_queries:
            print(f"\n  Q: {q}")
            result = query_docs(q)
            print(f"  A: {result}\n")

    except ImportError:
        print("\n  [ERROR] rag_engine.py not found!")
        print("  Person 1 needs to complete the RAG module first.")
        print("  The CrewAI agents will use placeholder data until then.")


def run_full_pipeline(category: str = "IT"):
    """Run the complete TenderBot pipeline."""
    from agents import run_tender_crew

    print(f"\n{'='*60}")
    print(f"  TenderBot Pakistan - Full Pipeline")
    print(f"  Category: {category}")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    # Check environment
    env_ok = check_environment()
    if not env_ok:
        print("\n  [ERROR] Required API keys are missing. Cannot run pipeline.")
        print("  Create a .env file from .env.example and add your keys.")
        sys.exit(1)

    # Run CrewAI pipeline
    result = run_tender_crew(category=category)

    # Save output to file
    output_dir = "outputs"
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"tender_report_{category}_{timestamp}.json")

    # Try to parse and save as formatted JSON
    try:
        # Extract JSON from the result (it might be wrapped in markdown code blocks)
        json_str = result
        if "```json" in json_str:
            json_str = json_str.split("```json")[1].split("```")[0]
        elif "```" in json_str:
            json_str = json_str.split("```")[1].split("```")[0]

        parsed = json.loads(json_str.strip())
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(parsed, f, indent=2, ensure_ascii=False)
        print(f"\n  [SAVED] Structured report -> {output_file}")
    except (json.JSONDecodeError, IndexError):
        # Save raw output if JSON parsing fails
        output_file = output_file.replace(".json", ".txt")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"\n  [SAVED] Raw report -> {output_file}")

    print(f"\n{'='*60}")
    print(f"  Pipeline complete! Check {output_file}")
    print(f"{'='*60}\n")

    return result


# ===================================================================
# CLI Entry Point
# ===================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="TenderBot Pakistan - PPRA Tender Automation Agent"
    )
    parser.add_argument(
        "--category", "-c",
        type=str,
        default="IT",
        help="Tender category to search for (default: IT)"
    )
    parser.add_argument(
        "--test-scraper",
        action="store_true",
        help="Test the scraper module only"
    )
    parser.add_argument(
        "--test-rag",
        action="store_true",
        help="Test the RAG engine module only"
    )

    args = parser.parse_args()

    if args.test_scraper:
        test_scraper(args.category)
    elif args.test_rag:
        test_rag()
    else:
        run_full_pipeline(args.category)
