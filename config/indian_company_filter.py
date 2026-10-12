from typing import Dict, Any

INDIAN_CITIES = [
    "bengaluru", "bangalore", "hyderabad", "pune", "mumbai", "delhi", "new delhi",
    "noida", "gurugram", "gurgaon", "chennai", "kolkata", "ahmedabad", "jaipur",
    "lucknow", "chandigarh", "indore", "kochi", "coimbatore", "thiruvananthapuram",
    "bhubaneswar", "varanasi", "kanpur", "nagpur", "patna", "bhopal", "vadodara",
    "ghaziabad", "ludhiana", "agra", "nashik", "faridabad", "meerut", "rajkot",
    "trivandrum", "visakhapatnam", "vizag", "surat", "mysuru", "mysore", "dehradun",
    "madurai", "mangalore", "chunar", "kakori", "greater noida", "navi mumbai",
    "greater lucknow area"
]

INDIAN_STATES = [
    "uttar pradesh", "karnataka", "maharashtra", "tamil nadu", "telangana",
    "haryana", "west bengal", "gujarat", "kerala", "punjab", "rajasthan",
    "andhra pradesh", "madhya pradesh", "bihar", "odisha", "assam", "jharkhand",
    "uttarakhand", "goa", "himachal pradesh"
]

INDIAN_COMPANIES = [
    "tata", "tcs", "infosys", "wipro", "hcl", "tech mahindra", "swiggy", "zomato",
    "flipkart", "paytm", "ola", "meesho", "razorpay", "cred", "zepto", "zerodha",
    "jio", "reliance", "airtel", "zoho", "freshworks", "inmobi", "l&t", "larsen & toubro",
    "revun", "alightway", "billzova", "gramik", "nariro", "capital placement", "feedzai",
    "accenture india", "cognizant", "capgemini india", "persistent systems", "mphasis",
    "mindtree", "ltimindtree", "cyient", "hexaware", "birlasoft", "groww", "phonepe",
    "unacademy", "upgrad", "urban company", "nykaa", "lenskart", "dream11", "postman",
    "prep study", "aifa labs", "hitachi solutions india"
]

FOREIGN_LOCATION_KEYWORDS = [
    "usa", "united states", "u.s.", "uk", "united kingdom", "london", "canada",
    "australia", "germany", "france", "netherlands", "switzerland", "sweden",
    "denmark", "norway", "ireland", "spain", "italy", "argentina", "mexico",
    "peru", "chile", "brazil", "philippines", "pakistan", "serbia", "south korea",
    "korea", "japan", "turkey", "türkiye", "singapore", "europe", "americas",
    "latam", "san francisco", "palo alto", "sunnyvale", "mountain view", "austin",
    "new york", "seattle", "chicago", "boston", "los angeles", "san mateo",
    "münchen", "munich", "berlin", "amsterdam", "paris", "belgrade", "istanbul",
    "dublin", "olathe", "skanderborg"
]

FOREIGN_COMPANIES = [
    "spacex", "walmart", "general motors", "coinbase", "reddit", "perplexity",
    "garmin", "kamstrup", "discord", "circleci", "appliedai", "astronomer",
    "kobotoolbox", "lemon.io", "rippling", "betterhelp", "creatify", "bjak",
    "karrot", "perk", "cimri", "hey contact heroes", "telus digital", "bucket robotics",
    "lithic", "proxify", "salesloft", "bairesdev", "airspace link", "barclays",
    "ewor", "clickhouse", "rivian", "arbital health", "baton", "guidewire software",
    "smithrx", "thatch", "hp", "hopae", "codeforai"
]


def is_indian_company_or_job(job: Dict[str, Any]) -> bool:
    """Strictly identify if a job posting belongs to an Indian company or is located in India."""
    if not isinstance(job, dict):
        return False

    company_lower = str(job.get("company", "")).lower()
    location_lower = str(job.get("location", "")).lower()
    desc_lower = str(job.get("description", "")).lower()
    apply_url = str(job.get("apply_url", "")).lower()

    # 1. Immediately drop recognized foreign companies
    for fc in FOREIGN_COMPANIES:
        if fc in company_lower:
            return False

    # 2. Check if location has multiple foreign countries (e.g. global crowdsourced jobs)
    foreign_matches = [fl for fl in FOREIGN_LOCATION_KEYWORDS if fl in location_lower]
    if len(foreign_matches) >= 2 and not any(ic in company_lower for ic in INDIAN_COMPANIES):
        return False
    if foreign_matches and "india" not in location_lower:
        return False

    # 3. Explicit India in location or description or URL
    if (
        "india" in location_lower
        or ", in" in location_lower
        or "in - " in location_lower
        or ".in/" in apply_url
        or "in.linkedin.com" in apply_url
    ):
        return True

    # 4. Check known Indian cities and states
    if any(city in location_lower for city in INDIAN_CITIES):
        return True
    if any(state in location_lower for state in INDIAN_STATES):
        return True

    # 5. Check Indian company names & corporate indicators
    if any(ic in company_lower for ic in INDIAN_COMPANIES):
        return True
    if any(
        suffix in company_lower
        for suffix in [
            "pvt ltd",
            "pvt. ltd",
            "private limited",
            "technologies india",
            "solutions india",
        ]
    ):
        return True

    # 6. Check description for Indian locations or currency
    if any(k in desc_lower for k in ["india", "lpa", "lakh", "lakhs", "inr", "₹"]):
        return True

    return False
