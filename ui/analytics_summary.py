import sys
from pathlib import Path

# Ensure project root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Ensure UTF-8 stdout encoding on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from storage.job_storage import get_application_analytics
from config import get_logger

logger = get_logger("analytics_summary")


def main():
    logger.info("=" * 70)
    logger.info("      📈 JOB APPLICATION ANALYTICS & INSIGHTS SUMMARY")
    logger.info("=" * 70)

    analytics = get_application_analytics()

    avg_applied = (
        f"{analytics['avg_applied_score']}%"
        if analytics["avg_applied_score"] is not None
        else "N/A (No applied jobs yet)"
    )
    avg_interview_offer = (
        f"{analytics['avg_interview_offer_score']}%"
        if analytics["avg_interview_offer_score"] is not None
        else "N/A (No interview/offer jobs yet)"
    )

    logger.info(f"• Average Score of Applied Jobs:                {avg_applied}")
    logger.info(f"• Average Score of Jobs (Interviews & Offers):   {avg_interview_offer}")
    logger.info(f"• Total Applications Tracked:                  {analytics['total_applied_count']}")
    logger.info(f"• Total Interviews & Offers:                   {analytics['total_interview_offer_count']}")

    logger.info("📊 Status Distribution Breakdown:")
    status_counts = analytics.get("status_counts", {})
    if status_counts:
        for st_name, count in status_counts.items():
            logger.info(f"   - {st_name.upper():<15}: {count} job(s)")
    else:
        logger.info("   No status data recorded yet.")

    logger.info("⚠️ Skills Most Frequently Missing in Rejections:")
    missing_rejections = analytics.get("frequent_rejection_missing_skills", [])
    if missing_rejections:
        for sk, count in missing_rejections:
            logger.info(f"   - {sk:<35}: missing in {count} rejection(s)")
    else:
        logger.info("   None recorded yet (No rejection data found).")

    logger.info("=" * 70)


if __name__ == "__main__":
    main()
