import json
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load .env file from project root
BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path)

CONFIG_JSON_FILE = BASE_DIR / "config" / "pipeline_config.json"


def load_pipeline_config() -> Dict[str, Any]:
    """Load configurable pipeline parameters from editable config/pipeline_config.json."""
    default_config = {
        "match_score_cutoff": int(os.getenv("MATCH_SCORE_CUTOFF", "60")),
        "shortlist_size": int(os.getenv("FINAL_TOP_N_JOBS", "15")),
        "job_sources": [
            s.strip()
            for s in os.getenv(
                "JOB_SOURCES", "RemoteOK,WeWorkRemotely,LinkedIn,Indeed,Naukri"
            ).split(",")
            if s.strip()
        ],
    }

    if CONFIG_JSON_FILE.exists():
        try:
            with open(CONFIG_JSON_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    default_config.update(data)
        except Exception:
            pass
    else:
        save_pipeline_config(default_config)

    return default_config


def save_pipeline_config(config_data: Dict[str, Any]) -> None:
    """Save configurable pipeline parameters to config/pipeline_config.json."""
    CONFIG_JSON_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2)


@dataclass
class Config:
    GROQ_API_KEY: str = field(default_factory=lambda: os.getenv("GROQ_API_KEY", ""))
    MATCH_THRESHOLD: float = field(
        default_factory=lambda: float(os.getenv("MATCH_THRESHOLD", "0.7"))
    )

    @property
    def MATCH_SCORE_CUTOFF(self) -> int:
        return load_pipeline_config().get("match_score_cutoff", 60)

    @property
    def FINAL_TOP_N_JOBS(self) -> int:
        return load_pipeline_config().get("shortlist_size", 15)

    @property
    def JOB_SOURCES(self) -> List[str]:
        return load_pipeline_config().get(
            "job_sources", ["RemoteOK", "WeWorkRemotely", "LinkedIn", "Indeed", "Naukri"]
        )

    TARGET_PORTALS: dict = field(
        default_factory=lambda: {
            "RemoteOK": {
                "url": "https://remoteok.com/api",
                "method": "Public API (JSON)",
            },
            "WeWorkRemotely": {
                "url": "https://weworkremotely.com/remote-jobs.rss",
                "method": "Public RSS Feed",
            },
            "LinkedIn": {
                "url": "https://www.linkedin.com/jobs/search/",
                "method": "HTML Scraping / BeautifulSoup / Playwright",
            },
            "Indeed": {
                "url": "https://www.indeed.com/jobs",
                "method": "HTML Scraping / Playwright",
            },
            "Naukri": {
                "url": "https://www.naukri.com/",
                "method": "Dynamic Web Scraping / Playwright",
            },
        }
    )


settings = Config()
