import os
import json
import urllib.request
import urllib.parse
from typing import Dict, Any, List, Optional

OPENALEX_API_URL = "https://api.openalex.org/works"
USER_AGENT = "GeoSentinelAI/1.0 (mailto:admin@geosentinel.ai)"

def build_literature_query(regional_context: str) -> str:
    """Constructs an effective academic search query for regional geology or coastal mariculture."""
    if not regional_context or "Terrain Sector" in regional_context:
        return "geology geomorphology remote sensing"
    clean_context = " ".join([part.strip() for part in regional_context.split(",") if part.strip()])
    if any(keyword in regional_context.lower() for keyword in ["marine", "gulf", "strait", "coast", "littoral", "archipelago", "bay", "seaweed"]):
        return f"{clean_context} seaweed aquaculture marine remote sensing"
    return f"{clean_context} geology"

def format_paper_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Extracts structured publication metadata from an OpenAlex work record."""
    title = item.get("display_name") or item.get("title") or "Untitled Geological Survey"
    year = item.get("publication_year")

    # Author formatting (up to 3 authors, + et al.)
    authors: List[str] = []
    raw_authors = item.get("authorships", [])
    for authorship in raw_authors[:3]:
        name = authorship.get("author", {}).get("display_name")
        if name:
            authors.append(name)
    if len(raw_authors) > 3:
        authors.append("et al.")

    # Venue / Journal
    venue = None
    primary_loc = item.get("primary_location") or {}
    source = primary_loc.get("source") or {}
    if source and source.get("display_name"):
        venue = source.get("display_name")
    elif item.get("host_venue") and item["host_venue"].get("display_name"):
        venue = item["host_venue"]["display_name"]

    # Links
    doi_url = item.get("doi")
    oa_info = item.get("open_access") or {}
    is_open_access = bool(oa_info.get("is_oa", False))
    oa_url = oa_info.get("oa_url")
    
    primary_link = doi_url or oa_url or primary_loc.get("landing_page_url") or f"https://openalex.org/{item.get('id', '')}"

    return {
        "title": title,
        "authors": authors,
        "year": year,
        "venue": venue or "Academic Geological Publication",
        "doi_url": primary_link,
        "is_open_access": is_open_access,
        "oa_url": oa_url
    }

def fetch_regional_literature(
    regional_context: str,
    limit: int = 4,
    timeout_seconds: float = 3.5
) -> List[Dict[str, Any]]:
    """
    Queries OpenAlex for peer-reviewed geological and remote sensing publications
    matching the regional context. Ranks by publication recency among relevant works.
    Returns empty list gracefully on network error or timeout.
    """
    query = build_literature_query(regional_context)
    encoded_query = urllib.parse.quote_plus(query)
    url = f"{OPENALEX_API_URL}?search={encoded_query}&per-page=15"

    api_key = (os.getenv("OPENALEX_KEY") or os.getenv("OPENALEX_API_KEY") or "").strip()
    headers = {"User-Agent": USER_AGENT}
    if api_key:
        url += f"&api_key={urllib.parse.quote_plus(api_key)}"
        headers["api-key"] = api_key

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
            raw_results = payload.get("results", [])
            
            # Sort candidates by publication_year descending (most recent first)
            sorted_candidates = sorted(
                raw_results,
                key=lambda x: (x.get("publication_year") or 0),
                reverse=True
            )
            
            papers = [format_paper_item(item) for item in sorted_candidates[:limit]]
            return papers
    except Exception as e:
        print(f"[Literature Ingestion Notice] Failed to fetch regional literature: {e}")
        return []
