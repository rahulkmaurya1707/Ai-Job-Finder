import time
from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse
from typing import List, Dict, Any
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

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
    if not is_allowed_by_robots(url):
        return [
            format_job_item(
                description="Access disallowed by robots.txt", source="RemoteOK"
            )
        ]

    time.sleep(1.0)
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            data = response.json()
            jobs = []
            query_lower = query.lower()
            items = data[1:] if isinstance(data, list) and len(data) > 1 else data
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

                if query_lower in combined_text:
                    jobs.append(
                        format_job_item(
                            title=position,
                            company=company,
                            location=loc if loc else (location or "Remote"),
                            description=description[:300],
                            posted_date=date_str,
                            apply_url=apply_link,
                            source="RemoteOK",
                        )
                    )
            return jobs[:10]
    except Exception as e:
        return [
            format_job_item(
                description=f"RemoteOK search failed: {str(e)}", source="RemoteOK"
            )
        ]
    return []


def search_weworkremotely_jobs(
    query: str, location: str = ""
) -> List[Dict[str, str]]:
    """Direct RSS feed call for WeWorkRemotely returning uniform job schema."""
    if str(query).lower().strip() == "ping":
        return [format_job_item(title="Ping Reachable", source="WeWorkRemotely")]

    url = "https://weworkremotely.com/remote-jobs.rss"
    if not is_allowed_by_robots(url):
        return [
            format_job_item(
                description="Access disallowed by robots.txt", source="WeWorkRemotely"
            )
        ]

    time.sleep(1.0)
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
                    company = title.split(":")[0].strip()

                if (
                    query_lower in title.lower()
                    or query_lower in description.lower()
                ):
                    jobs.append(
                        format_job_item(
                            title=title,
                            company=company,
                            location=location or "Remote",
                            description=description[:300],
                            posted_date=pub_date,
                            apply_url=link,
                            source="WeWorkRemotely",
                        )
                    )
            return jobs[:10]
    except Exception as e:
        return [
            format_job_item(
                description=f"WeWorkRemotely search failed: {str(e)}",
                source="WeWorkRemotely",
            )
        ]
    return []


def search_linkedin_jobs(query: str, location: str = "") -> List[Dict[str, str]]:
    """HTML Scraping for LinkedIn returning uniform job schema."""
    if str(query).lower().strip() == "ping":
        return [format_job_item(title="Ping Reachable", source="LinkedIn")]

    url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={query}&location={location}"
    if not is_allowed_by_robots(url):
        return [
            format_job_item(
                description="Access disallowed by robots.txt", source="LinkedIn"
            )
        ]

    time.sleep(1.2)
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

                if title_elem:
                    jobs.append(
                        format_job_item(
                            title=title_elem.text,
                            company=company_elem.text if company_elem else "",
                            location=loc_elem.text if loc_elem else location,
                            description=title_elem.text,
                            posted_date=date_elem.text if date_elem else "",
                            apply_url=link_elem["href"]
                            if link_elem and "href" in link_elem.attrs
                            else url,
                            source="LinkedIn",
                        )
                    )
            return jobs[:10]
    except Exception as e:
        return [
            format_job_item(
                description=f"LinkedIn search failed: {str(e)}", source="LinkedIn"
            )
        ]
    return []


def search_indeed_jobs(query: str, location: str = "") -> List[Dict[str, str]]:
    """Playwright Dynamic Scraping for Indeed returning uniform job schema."""
    if str(query).lower().strip() == "ping":
        return [format_job_item(title="Ping Reachable", source="Indeed")]

    url = f"https://www.indeed.com/jobs?q={query}&l={location}"
    if not is_allowed_by_robots(url):
        return [
            format_job_item(
                description="Access disallowed by robots.txt", source="Indeed"
            )
        ]

    time.sleep(1.5)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=HEADERS["User-Agent"])
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
            html = page.content()
            browser.close()

            soup = BeautifulSoup(html, "html.parser")
            job_cards = soup.find_all("div", class_="job_seen_beacon")
            jobs = []
            for card in job_cards:
                title_elem = card.find("h2", class_="jobTitle")
                company_elem = card.find("span", class_="companyName")
                loc_elem = card.find("div", class_="companyLocation")
                snippet_elem = card.find("div", class_="job-snippet")

                if title_elem:
                    jobs.append(
                        format_job_item(
                            title=title_elem.text,
                            company=company_elem.text if company_elem else "",
                            location=loc_elem.text if loc_elem else location,
                            description=snippet_elem.text if snippet_elem else "",
                            posted_date="",
                            apply_url=url,
                            source="Indeed",
                        )
                    )
            return jobs[:10]
    except Exception as e:
        return [
            format_job_item(
                description=f"Indeed Playwright search failed: {str(e)}",
                source="Indeed",
            )
        ]


def search_naukri_jobs(query: str, location: str = "") -> List[Dict[str, str]]:
    """Playwright Dynamic Scraping for Naukri returning uniform job schema."""
    if str(query).lower().strip() == "ping":
        return [format_job_item(title="Ping Reachable", source="Naukri")]

    clean_query = query.replace(" ", "-").lower()
    clean_loc = location.replace(" ", "-").lower() if location else "india"
    url = f"https://www.naukri.com/{clean_query}-jobs-in-{clean_loc}"
    if not is_allowed_by_robots(url):
        return [
            format_job_item(
                description="Access disallowed by robots.txt", source="Naukri"
            )
        ]

    time.sleep(1.5)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=HEADERS["User-Agent"])
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
            html = page.content()
            browser.close()

            soup = BeautifulSoup(html, "html.parser")
            job_cards = soup.find_all("article", class_="jobTuple")
            jobs = []
            for card in job_cards:
                title_elem = card.find("a", class_="title")
                company_elem = card.find("a", class_="subTitle")
                loc_elem = card.find("li", class_="location")
                desc_elem = card.find("div", class_="job-description")
                date_elem = card.find("span", class_="type")

                if title_elem:
                    jobs.append(
                        format_job_item(
                            title=title_elem.text,
                            company=company_elem.text if company_elem else "",
                            location=loc_elem.text if loc_elem else (location or "India"),
                            description=desc_elem.text if desc_elem else "",
                            posted_date=date_elem.text if date_elem else "",
                            apply_url=title_elem["href"]
                            if "href" in title_elem.attrs
                            else url,
                            source="Naukri",
                        )
                    )
            return jobs[:10]
    except Exception as e:
        return [
            format_job_item(
                description=f"Naukri Playwright search failed: {str(e)}",
                source="Naukri",
            )
        ]
