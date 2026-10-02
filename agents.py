"""
TenderBot Pakistan - CrewAI Agents Module
==========================================
Defines 3 specialized AI agents orchestrated by CrewAI:
  Agent 1 - Researcher : Discovers active tenders
  Agent 2 - Matcher    : Checks company eligibility via RAG
  Agent 3 - Writer     : Produces structured JSON output + cover letter

Author: Backend Person 2
"""

import os
import json
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Ensure Gemini API key is available to litellm (CrewAI's LLM backend)
# litellm reads GEMINI_API_KEY from os.environ directly.
# ---------------------------------------------------------------------------
_gemini_key = os.getenv("GEMINI_API_KEY", "")
if _gemini_key:
    os.environ["GEMINI_API_KEY"] = _gemini_key
else:
    print(
        "[WARNING] GEMINI_API_KEY not found in .env file.\n"
        "  CrewAI agents will not be able to call the LLM.\n"
        "  Get your key at: https://aistudio.google.com/apikey\n"
        "  Then add it to your .env file."
    )

from crewai import Agent, Task, Crew, Process
from crewai.tools import tool

# Import the scraper module (Person 2)
from scraper import smart_fetch_tenders, scrape_tender_detail

# Import the RAG engine (Person 1 — or the development stub)
from rag_engine import query_docs


# ===================================================================
# LLM CONFIGURATION
# ===================================================================

# CrewAI uses litellm under the hood. For Gemini models, the format is:
#   "gemini/<model-name>"
# litellm automatically picks up GEMINI_API_KEY from os.environ.
# Override in .env with AGENT_MODEL=<model name> if Google retires this one
LLM_MODEL = "gemini/" + os.getenv("AGENT_MODEL", "gemini-3.8-flash")


# ===================================================================
# CUSTOM TOOLS (exposed to CrewAI agents)
# ===================================================================

@tool("Tender Search Tool")
def tender_search_tool(category: str) -> str:
    """
    Search for active Pakistani government tenders by category.
    Uses PPRA website scraping with Serper API fallback.

    Args:
        category: The tender category to search for (e.g. 'IT', 'Software',
                  'Construction', 'Infrastructure', 'Medical').

    Returns:
        JSON string of found tenders with title, department, dates, and links.
    """
    try:
        tenders = smart_fetch_tenders(category=category, max_results=10)
        if not tenders:
            return json.dumps({
                "status": "no_results",
                "message": f"No tenders found for category: {category}",
                "tenders": []
            })
        return json.dumps({
            "status": "success",
            "count": len(tenders),
            "tenders": tenders
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Tender search failed: {str(e)}",
            "tenders": []
        })


@tool("Tender Detail Tool")
def tender_detail_tool(url: str) -> str:
    """
    Fetch full details of a specific tender from its URL. Extracts the
    complete description text, eligibility requirements, and PDF download links.

    Args:
        url: The full URL of the tender detail page.

    Returns:
        JSON string with full_text, requirements_raw, and pdf_links.
    """
    try:
        detail = scrape_tender_detail(url)
        return json.dumps(detail, indent=2)
    except Exception as e:
        return json.dumps({
            "url": url,
            "error": f"Failed to fetch tender details: {str(e)}",
            "full_text": "",
            "pdf_links": [],
            "requirements_raw": ""
        })


@tool("Company RAG Query Tool")
def company_rag_tool(question: str) -> str:
    """
    Query the company's internal document knowledge base using RAG
    (Retrieval-Augmented Generation). Use this to verify if the company
    has specific qualifications, certificates, experience, or documents.

    Example questions:
      - 'Does the company have a PEC license? What category?'
      - 'What is the company annual turnover?'
      - 'List past IT project experience'
      - 'Does the company have NTN registration?'

    Args:
        question: Natural language question about the company's qualifications.

    Returns:
        Retrieved context from the company's document knowledge base.
    """
    try:
        result = query_docs(question)
        if isinstance(result, dict):
            # Real RAG engine returns {"answer", "found", "sources", ...}
            if not result.get("found"):
                return "No relevant information found in company documents for this query."
            sources = ", ".join(
                str(x.get("source", "")) for x in (result.get("sources") or [])
            )
            return f"{result.get('answer', '')}\n(Sources: {sources})"
        if result:
            return str(result)
        return "No relevant information found in company documents for this query."
    except Exception as e:
        return f"RAG query failed: {str(e)}"


# ===================================================================
# AGENT DEFINITIONS
# ===================================================================

def create_researcher_agent() -> Agent:
    """
    Agent 1 - Tender Researcher
    Role: Discover and collect active government tenders matching
          the user's specified category from PPRA and Google Search.
    """
    return Agent(
        role="Senior Tender Research Analyst",
        goal=(
            "Find the latest active Pakistani government tenders "
            "matching the user's required category. Extract titles, "
            "departments, deadlines, and detail URLs."
        ),
        backstory=(
            "You are an expert government procurement researcher "
            "specializing in Pakistani PPRA tenders. You have 10 years "
            "of experience tracking tender notices across federal and "
            "provincial procurement portals. You know how to find "
            "relevant tenders quickly and extract key details."
        ),
        tools=[tender_search_tool, tender_detail_tool],
        llm=LLM_MODEL,
        verbose=True,
        allow_delegation=False,
    )


def create_matcher_agent() -> Agent:
    """
    Agent 2 - Eligibility Matcher
    Role: Compare tender requirements against the company's credentials
          using RAG and calculate eligibility match percentage.
    """
    return Agent(
        role="Tender Eligibility Matching Specialist",
        goal=(
            "Analyze each tender's eligibility requirements and compare "
            "them against the company's qualifications retrieved from the "
            "RAG knowledge base. Calculate a match percentage and identify "
            "any gaps or missing documents."
        ),
        backstory=(
            "You are a procurement compliance expert who has helped "
            "hundreds of Pakistani SMEs determine their eligibility "
            "for government tenders. You understand PEC categories, "
            "NTN requirements, financial turnover thresholds, and "
            "experience criteria. You methodically check each "
            "requirement against company documents."
        ),
        tools=[company_rag_tool],
        llm=LLM_MODEL,
        verbose=True,
        allow_delegation=False,
    )


def create_writer_agent() -> Agent:
    """
    Agent 3 - Proposal Writer
    Role: Compile final structured JSON output and generate a
          professional cover letter for eligible tenders.
    """
    return Agent(
        role="Tender Proposal Writer & Report Generator",
        goal=(
            "Create a final structured JSON report for each tender that "
            "includes: title, department, deadline, summary, eligibility "
            "score, eligibility reason, gap analysis, and a professional "
            "cover letter draft. Output must be valid JSON."
        ),
        backstory=(
            "You are a professional tender proposal writer who has "
            "written over 500 successful government tender applications "
            "in Pakistan. You know how to present company qualifications "
            "persuasively and format reports that procurement officers "
            "expect to see."
        ),
        tools=[],
        llm=LLM_MODEL,
        verbose=True,
        allow_delegation=False,
    )


# ===================================================================
# TASK DEFINITIONS
# ===================================================================

def create_research_task(agent: Agent, category: str) -> Task:
    """Task 1: Find tenders matching the given category."""
    return Task(
        description=(
            f"Search for the latest active Pakistani government tenders "
            f"in the '{category}' category.\n\n"
            f"Steps:\n"
            f"1. Use the 'Tender Search Tool' with category='{category}'\n"
            f"2. For each tender found, note the title, department, "
            f"   closing date, and detail URL\n"
            f"3. If a detail URL is available, use the 'Tender Detail Tool' "
            f"   to extract full requirements for the top 3 tenders\n"
            f"4. Compile a summary of each tender with its key requirements\n\n"
            f"Return a comprehensive list of tenders with their details."
        ),
        expected_output=(
            "A detailed list of found tenders, each containing:\n"
            "- Tender title\n"
            "- Issuing department\n"
            "- Closing/deadline date\n"
            "- Key requirements (if detail page was scraped)\n"
            "- Source URL"
        ),
        agent=agent,
    )


def create_matching_task(agent: Agent) -> Task:
    """Task 2: Match company credentials against tender requirements."""
    return Task(
        description=(
            "For each tender found by the Researcher, check if our company "
            "is eligible by querying our internal document knowledge base.\n\n"
            "Steps:\n"
            "1. For each tender requirement, use the 'Company RAG Query Tool' "
            "   to verify if the company meets that requirement\n"
            "2. Check these critical areas:\n"
            "   - PEC license category (use query: 'What is company PEC category?')\n"
            "   - NTN registration (use query: 'Is company NTN registered?')\n"
            "   - Financial turnover (use query: 'What is company annual turnover?')\n"
            "   - Past experience (use query: 'List company past project experience')\n"
            "   - Required certifications (use query: 'What certifications does company have?')\n"
            "3. For each tender, calculate an eligibility match percentage:\n"
            "   - 100% = meets all requirements\n"
            "   - 75%  = meets most, minor gaps\n"
            "   - 50%  = meets some, significant gaps\n"
            "   - 25%  = meets few requirements\n"
            "   - 0%   = does not qualify\n"
            "4. Clearly list what requirements are MET and what are GAPS\n\n"
            "Return a detailed eligibility analysis for each tender."
        ),
        expected_output=(
            "For each tender:\n"
            "- Tender title\n"
            "- Eligibility match percentage (0-100%)\n"
            "- List of MET requirements with evidence from company docs\n"
            "- List of GAP requirements (what is missing)\n"
            "- Overall recommendation: ELIGIBLE / CONDITIONALLY_ELIGIBLE / NOT_ELIGIBLE"
        ),
        agent=agent,
    )


def create_writing_task(agent: Agent) -> Task:
    """Task 3: Generate final JSON report and cover letter."""
    return Task(
        description=(
            "Using the tender details from the Researcher and the eligibility "
            "analysis from the Matcher, create a final structured report.\n\n"
            "For EACH tender, produce a JSON object with these exact keys:\n"
            "{\n"
            '  "title": "Full tender title",\n'
            '  "department": "Issuing department name",\n'
            '  "closing_date": "Deadline date",\n'
            '  "summary": "2-3 sentence summary of what the tender is about",\n'
            '  "eligibility_score": 75,\n'
            '  "eligibility_status": "ELIGIBLE | CONDITIONALLY_ELIGIBLE | NOT_ELIGIBLE",\n'
            '  "eligibility_reason": "Brief explanation of why this score",\n'
            '  "met_requirements": ["list of met items"],\n'
            '  "gap_analysis": ["list of missing items"],\n'
            '  "cover_letter": "A professional 3-paragraph cover letter draft"\n'
            "}\n\n"
            "IMPORTANT:\n"
            "- Your final output MUST be a valid JSON array containing one object per tender\n"
            "- Wrap the entire output in ```json code blocks\n"
            "- Generate a cover letter ONLY for tenders with eligibility >= 50%\n"
            "- For tenders below 50%, set cover_letter to 'Not recommended to apply'"
        ),
        expected_output=(
            "A valid JSON array where each element is a tender report object "
            "containing: title, department, closing_date, summary, "
            "eligibility_score, eligibility_status, eligibility_reason, "
            "met_requirements, gap_analysis, and cover_letter."
        ),
        agent=agent,
    )


# ===================================================================
# CREW ORCHESTRATION
# ===================================================================

def run_tender_crew(category: str = "IT") -> str:
    """
    Assemble and run the full 3-agent CrewAI pipeline.

    Args:
        category: Tender category to search for.

    Returns:
        Final output string from the Writer agent (JSON report).
    """
    print(f"\n{'='*60}")
    print(f"  TenderBot CrewAI Pipeline - Category: {category}")
    print(f"{'='*60}\n")

    # Create agents
    researcher = create_researcher_agent()
    matcher = create_matcher_agent()
    writer = create_writer_agent()

    # Create tasks (sequential: research -> match -> write)
    research_task = create_research_task(researcher, category)
    matching_task = create_matching_task(matcher)
    writing_task = create_writing_task(writer)

    # Assemble crew with sequential process
    crew = Crew(
        agents=[researcher, matcher, writer],
        tasks=[research_task, matching_task, writing_task],
        process=Process.sequential,
        verbose=True,
    )

    # Execute the pipeline
    print("\n[CrewAI] Starting pipeline execution...\n")
    result = crew.kickoff()

    print(f"\n{'='*60}")
    print("  Pipeline Complete!")
    print(f"{'='*60}\n")

    return str(result)


# ===================================================================
# Standalone test
# ===================================================================
if __name__ == "__main__":
    output = run_tender_crew(category="IT")
    print("\n--- Final CrewAI Output ---")
    print(output)
