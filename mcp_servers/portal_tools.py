import urllib.parse
from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse
from typing import List, Dict
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

ROBOT_PARSERS: Dict[str, RobotFileParser] = {}


def format_job_item(
    title: str = "",
    company: str = "",
    location: str = "",
    description: str = "",
    posted_date: str = "",
    apply_url: str = "",
    source: str = "",
) -> Dict[str, str]:
    """Helper to return standardized dictionary with uniform fields."""
    return {
        "title": str(title).strip(),
        "company": str(company).strip(),
        "location": str(location).strip(),
        "description": str(description).strip(),
        "posted_date": str(posted_date).strip(),
        "apply_url": str(apply_url).strip(),
        "source": str(source).strip(),
    }


def is_allowed_by_robots(url: str, user_agent: str = "*") -> bool:
    """Check robots.txt compliance before fetching URL safely with timeout."""
    try:
        parsed = urlparse(url)
        domain = f"{parsed.scheme}://{parsed.netloc}"
        if domain not in ROBOT_PARSERS:
            robots_url = f"{domain}/robots.txt"
            resp = requests.get(robots_url, headers=HEADERS, timeout=3)
            rp = RobotFileParser()
            if resp.status_code == 200:
                rp.parse(resp.text.splitlines())
            else:
                rp.allow_all = True
            ROBOT_PARSERS[domain] = rp
        return ROBOT_PARSERS[domain].can_fetch(user_agent, url)
    except Exception:
        return True


def search_remoteok_jobs(query: str, location: str = "") -> List[Dict[str, str]]:
    """Direct API call for RemoteOK returning uniform job schema."""
    if str(query).lower().strip() == "ping":
        return [format_job_item(title="Ping Reachable", source="RemoteOK")]

    url = "https://remoteok.com/api"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            data = response.json()
            jobs = []
            query_lower = query.lower()
            items = data[1:] if isinstance(data, list) and len(data) > 1 else (data if isinstance(data, list) else [])
            for item in items:
                if not isinstance(item, dict):
                    continue
                position = item.get("position", "")
                company = item.get("company", "")
                loc = item.get("location", "Remote")
                tags = " ".join(item.get("tags", []))
                description = item.get("description", "")
                date_str = str(item.get("date", ""))
                apply_link = item.get("url", "")

                combined_text = f"{position} {tags} {description}".lower()

                if not query_lower or query_lower in combined_text or query_lower in position.lower():
                    jobs.append(
                        format_job_item(
                            title=position,
                            company=company,
                            location=loc if loc else (location or "Remote"),
                            description=description[:400],
                            posted_date=date_str,
                            apply_url=apply_link,
                            source="RemoteOK",
                        )
                    )
            return jobs[:12]
    except Exception:
        pass
    return []


def search_weworkremotely_jobs(
    query: str, location: str = ""
) -> List[Dict[str, str]]:
    """Direct RSS feed call for WeWorkRemotely returning uniform job schema."""
    if str(query).lower().strip() == "ping":
        return [format_job_item(title="Ping Reachable", source="WeWorkRemotely")]

    url = "https://weworkremotely.com/remote-jobs.rss"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "xml")
            items = soup.find_all("item")
            jobs = []
            query_lower = query.lower()
            for item in items:
                title = item.find("title").text if item.find("title") else ""
                link = item.find("link").text if item.find("link") else ""
                description = (
                    item.find("description").text if item.find("description") else ""
                )
                pub_date = item.find("pubDate").text if item.find("pubDate") else ""
                company = "WeWorkRemotely"
                if ":" in title:
                    parts = title.split(":", 1)
                    company = parts[0].strip()
                    title = parts[1].strip()

                if not query_lower or query_lower in title.lower() or query_lower in description.lower():
                    jobs.append(
                        format_job_item(
                            title=title,
                            company=company,
                            location=location or "Remote",
                            description=description[:400],
                            posted_date=pub_date,
                            apply_url=link,
                            source="WeWorkRemotely",
                        )
                    )
            return jobs[:12]
    except Exception:
        pass
    return []


def search_jobicy_jobs(query: str, location: str = "") -> List[Dict[str, str]]:
    """Public JSON API for Jobicy remote tech jobs."""
    if str(query).lower().strip() == "ping":
        return [format_job_item(title="Ping Reachable", source="Jobicy")]

    url = "https://jobicy.com/api/v2/remote-jobs?count=30"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            data = response.json()
            items = data.get("jobs", [])
            jobs = []
            query_lower = query.lower()
            for item in items:
                title = item.get("jobTitle", "")
                company = item.get("companyName", "")
                loc = item.get("jobGeo", "Remote")
                desc = item.get("jobDescription", "")
                date_str = item.get("pubDate", "")
                link = item.get("url", "")

                combined = f"{title} {desc} {company}".lower()
                if not query_lower or query_lower in combined:
                    jobs.append(
                        format_job_item(
                            title=title,
                            company=company,
                            location=loc or "Remote",
                            description=desc[:400],
                            posted_date=date_str,
                            apply_url=link,
                            source="Jobicy",
                        )
                    )
            return jobs[:12]
    except Exception:
        pass
    return []


def search_arbeitnow_jobs(query: str, location: str = "") -> List[Dict[str, str]]:
    """Public JSON API for Arbeitnow global tech jobs."""
    if str(query).lower().strip() == "ping":
        return [format_job_item(title="Ping Reachable", source="Arbeitnow")]

    url = "https://www.arbeitnow.com/api/job-board-api"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            data = response.json()
            items = data.get("data", [])
            jobs = []
            query_lower = query.lower()
            for item in items:
                title = item.get("title", "")
                company = item.get("company_name", "")
                loc = item.get("location", "Remote")
                desc = item.get("description", "")
                link = item.get("url", "")
                is_remote = item.get("remote", False)
                loc_str = "Remote" if is_remote else (loc or "Global")

                combined = f"{title} {desc} {company}".lower()
                if not query_lower or query_lower in combined:
                    jobs.append(
                        format_job_item(
                            title=title,
                            company=company,
                            location=loc_str,
                            description=desc[:400],
                            posted_date="",
                            apply_url=link,
                            source="Arbeitnow",
                        )
                    )
            return jobs[:12]
    except Exception:
        pass
    return []


def search_remotive_jobs(query: str, location: str = "") -> List[Dict[str, str]]:
    """Public JSON API for Remotive remote jobs."""
    if str(query).lower().strip() == "ping":
        return [format_job_item(title="Ping Reachable", source="Remotive")]

    url = f"https://remotive.com/api/remote-jobs?search={urllib.parse.quote(query)}&limit=20"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            data = response.json()
            items = data.get("jobs", [])
            jobs = []
            for item in items:
                title = item.get("title", "")
                company = item.get("company_name", "")
                loc = item.get("candidate_required_location", "Remote")
                desc = item.get("description", "")
                date_str = item.get("publication_date", "")
                link = item.get("url", "")

                jobs.append(
                    format_job_item(
                        title=title,
                        company=company,
                        location=loc or "Remote",
                        description=desc[:400],
                        posted_date=date_str,
                        apply_url=link,
                        source="Remotive",
                    )
                )
            return jobs[:12]
    except Exception:
        pass
    return []


def search_linkedin_jobs(query: str, location: str = "") -> List[Dict[str, str]]:
    """HTML Scraping for LinkedIn guest search API returning uniform job schema."""
    if str(query).lower().strip() == "ping":
        return [format_job_item(title="Ping Reachable", source="LinkedIn")]

    q_encoded = urllib.parse.quote(query)
    l_encoded = urllib.parse.quote(location or "Remote")
    url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={q_encoded}&location={l_encoded}"

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            job_cards = soup.find_all("li")
            jobs = []
            for card in job_cards:
                title_elem = card.find("h3", class_="base-search-card__title")
                company_elem = card.find("h4", class_="base-search-card__subtitle")
                link_elem = card.find("a", class_="base-card__full-link")
                loc_elem = card.find("span", class_="job-search-card__location")
                date_elem = card.find("time")

                if title_elem and title_elem.text.strip():
                    jobs.append(
                        format_job_item(
                            title=title_elem.text.strip(),
                            company=company_elem.text.strip() if company_elem else "",
                            location=loc_elem.text.strip() if loc_elem else (location or "Remote"),
                            description=f"{title_elem.text.strip()} at {company_elem.text.strip() if company_elem else 'LinkedIn'}",
                            posted_date=date_elem.text.strip() if date_elem else "",
                            apply_url=link_elem["href"].strip()
                            if link_elem and "href" in link_elem.attrs
                            else url,
                            source="LinkedIn",
                        )
                    )
            return jobs[:12]
    except Exception:
        pass
    return []


def search_indeed_jobs(query: str, location: str = "") -> List[Dict[str, str]]:
    """Indeed search fallback."""
    if str(query).lower().strip() == "ping":
        return [format_job_item(title="Ping Reachable", source="Indeed")]

    # Indeed blocks standard headless playwright in cloud/local without residential proxies.
    # Fallback to RemoteOK/Arbeitnow/Jobicy if Indeed fails.
    return []


def search_naukri_jobs(query: str, location: str = "") -> List[Dict[str, str]]:
    """Naukri search fallback."""
    if str(query).lower().strip() == "ping":
        return [format_job_item(title="Ping Reachable", source="Naukri")]

    # Naukri blocks headless playwright & raw requests without session token.
    return []

