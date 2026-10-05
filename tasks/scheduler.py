import time
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from skills.linkedin_hunter import LinkedInHunter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Scheduler")

def weekly_saturday_job_alert():
    logger.info("Executing scheduled job: Weekly Saturday LinkedIn Job Alert...")
    hunter = LinkedInHunter()
    res = hunter.send_weekly_jobs()
    logger.info(f"Saturday Job Alert Result:\n{res}")

def start_scheduler():
    scheduler = BackgroundScheduler()
    # Runs every Saturday at 09:00 AM
    scheduler.add_job(weekly_saturday_job_alert, 'cron', day_of_week='sat', hour=9, minute=0)
    scheduler.start()
    logger.info("✅ Background Scheduler started.")
    return scheduler

if __name__ == "__main__":
    s = start_scheduler()
    logger.info("Scheduler worker running...")
    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        s.shutdown()
