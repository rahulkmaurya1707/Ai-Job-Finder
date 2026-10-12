from graph.filters import is_indian_company_or_job, filter_job_postings
from profile.user_profile import UserProfile


def test_is_indian_company_or_job_positive():
    """Verify Indian companies and locations are positively recognized."""
    indian_samples = [
        {"title": "Software Engineer", "company": "Tata Consultancy Services", "location": "Chennai, Tamil Nadu, India"},
        {"title": "Python Developer", "company": "Hitachi Solutions India Pvt Ltd", "location": "Pune, Maharashtra, India"},
        {"title": "SDE 1", "company": "Swiggy", "location": "Bengaluru, Karnataka, India"},
        {"title": "Full Stack Engineer", "company": "Zomato", "location": "Gurugram, Haryana, India"},
        {"title": "Backend Engineer", "company": "Razorpay", "location": "Bengaluru, Karnataka, India"},
        {"title": "Web Developer", "company": "Revun", "location": "Chunar, Uttar Pradesh, India"},
        {"title": "Software Developer", "company": "Alightway Solutions Pvt. Ltd.", "location": "Lucknow, Uttar Pradesh, India"},
        {"title": "Software Engineer", "company": "Billzova", "location": "Kakori, Uttar Pradesh, India"},
        {"title": "Full Stack Dev", "company": "Jio Platforms", "location": "Navi Mumbai, Maharashtra, India"},
    ]

    for job in indian_samples:
        assert is_indian_company_or_job(job) is True, f"Failed to identify Indian job: {job}"


def test_is_indian_company_or_job_negative():
    """Verify foreign companies and overseas locations are strictly rejected."""
    foreign_samples = [
        {"title": "Software Engineer", "company": "SpaceX", "location": "Palo Alto, CA"},
        {"title": "Senior Developer", "company": "Walmart Global Tech", "location": "Sunnyvale, CA"},
        {"title": "Backend Engineer", "company": "Appliedai", "location": "München (81671)"},
        {"title": "Cloud Architect", "company": "Astronomer", "location": "London"},
        {"title": "Web Developer", "company": "KoboToolbox", "location": "USA, Canada, Argentina, Mexico, Peru"},
        {"title": "Python Engineer", "company": "Lemon.io", "location": "Europe, USA, UK, Australia"},
        {"title": "Full Stack Engineer", "company": "Bucket Robotics", "location": "San Francisco, CA"},
        {"title": "Software Engineer", "company": "CircleCI", "location": "Remote"},
        {"title": "Site Reliability Engineer", "company": "Coinbase", "location": "Austin, TX"},
    ]

    for job in foreign_samples:
        assert is_indian_company_or_job(job) is False, f"Erroneously accepted foreign job: {job}"


def test_filter_job_postings_indian_only():
    """Verify filter_job_postings with indian_only=True excludes all foreign postings."""
    profile = UserProfile(name="Candidate", locations=["India"], remote_ok=True)
    mixed_jobs = [
        {"title": "Python Engineer", "company": "Tata Consultancy Services", "location": "Chennai, Tamil Nadu, India"},
        {"title": "Software Engineer", "company": "SpaceX", "location": "Palo Alto, CA"},
        {"title": "Backend Dev", "company": "Swiggy", "location": "Bengaluru, Karnataka, India"},
        {"title": "Lead Engineer", "company": "Astronomer", "location": "London"},
    ]

    filtered, dropped = filter_job_postings(mixed_jobs, profile, indian_only=True)
    assert len(filtered) == 2
    assert dropped == 2
    companies = [j["company"] for j in filtered]
    assert "Tata Consultancy Services" in companies
    assert "Swiggy" in companies
    assert "SpaceX" not in companies
    assert "Astronomer" not in companies
