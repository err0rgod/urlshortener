import os
import asyncio
import datetime
import httpx
from datetime import UTC, timedelta
from sqlmodel import Session, select, func
from database import engine
from models import clicklog, urldata
from short_url_gen import redis_client
from logger import logger, log_file

# Fetch configuration parameters
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
TARGET_EMAIL = os.getenv("ADMIN_EMAIL")

def get_log_counts_24h() -> dict:
    """
    Parses the local application log file to count entries by log level (INFO,
    WARNING, ERROR, CRITICAL) written within the last 24 hours.
    """
    counts = {"INFO": 0, "WARNING": 0, "ERROR": 0, "CRITICAL": 0}
    if not os.path.exists(log_file):
        return counts

    now = datetime.datetime.now()
    cutoff = now - timedelta(hours=24)

    try:
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split(" - ")
                if len(parts) >= 3:
                    ts_str = parts[0].split(",")[0]
                    try:
                        ts = datetime.datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                        if ts >= cutoff:
                            level = parts[2].upper()
                            if level in counts:
                                counts[level] += 1
                    except Exception:
                        pass
    except Exception as e:
        logger.error(f"Failed to parse daily logs: {e}")
    return counts

async def generate_and_send_report():
    """
    Queries database metrics for unique visitors, link redirects, and link creations 
    along with log occurrences in the last 24 hours, dispatches an HTML report to the admin.
    """
    logger.info("Starting production daily analytics compilation...")
    
    now = datetime.datetime.now(UTC)
    last_24h = now - timedelta(hours=24)
    
    unique_visitors = 0
    total_clicks = 0
    new_links = 0
    
    try:
        with Session(engine) as session:
            # Query unique visitors (distinct ip_address)
            stmt_visitors = select(func.count(func.distinct(clicklog.ip_address))).where(clicklog.clicked_at >= last_24h)
            unique_visitors = session.exec(stmt_visitors).first() or 0

            # Query total clicks in the last 24 hours
            stmt_clicks = select(func.count(clicklog.id)).where(clicklog.clicked_at >= last_24h)
            total_clicks = session.exec(stmt_clicks).first() or 0

            # Query new links created in the last 24 hours
            stmt_links = select(func.count(urldata.short_url)).where(urldata.created_at >= last_24h)
            new_links = session.exec(stmt_links).first() or 0
    except Exception as e:
        logger.error(f"Database query failed during daily report compilation: {e}")
        
    log_counts = get_log_counts_24h()
    
    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY is not defined in the environment. Skipping daily report dispatch.")
        return
        
    if not TARGET_EMAIL:
        logger.warning("ADMIN_EMAIL is not defined in the environment. Skipping daily report dispatch.")
        return

    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Beautiful responsive HTML email template for the executive report
    html_content = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 600px; margin: auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 12px; background-color: #ffffff;">
        <h2 style="color: #4f46e5; border-bottom: 2px solid #f1f5f9; padding-bottom: 12px; margin-top: 0; margin-bottom: 16px; font-size: 20px; font-weight: 700; tracking-tight: -0.025em;">
            FlexURL Daily System Summary
        </h2>
        <p style="color: #64748b; font-size: 13px; line-height: 1.5; margin-bottom: 24px;">
            This report summarizes database activity and runtime server logs for the 24-hour window ending at {now.strftime('%Y-%m-%d %H:%M:%S')} UTC.
        </p>
        
        <h3 style="color: #1e293b; font-size: 14px; font-weight: 600; margin-top: 0; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.05em;">Link Traffic & Analytics</h3>
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 28px;">
            <tr style="background-color: #f8fafc;">
                <td style="padding: 12px; border: 1px solid #e2e8f0; font-size: 13px; font-weight: 500; color: #475569;">New Links Created</td>
                <td style="padding: 12px; border: 1px solid #e2e8f0; font-size: 13px; color: #1e293b; text-align: right; font-weight: 600;">{new_links}</td>
            </tr>
            <tr>
                <td style="padding: 12px; border: 1px solid #e2e8f0; font-size: 13px; font-weight: 500; color: #475569;">Total Link Redirects (Clicks)</td>
                <td style="padding: 12px; border: 1px solid #e2e8f0; font-size: 13px; color: #1e293b; text-align: right; font-weight: 600;">{total_clicks}</td>
            </tr>
            <tr style="background-color: #f8fafc;">
                <td style="padding: 12px; border: 1px solid #e2e8f0; font-size: 13px; font-weight: 500; color: #475569;">Unique Visitors (IPs)</td>
                <td style="padding: 12px; border: 1px solid #e2e8f0; font-size: 13px; color: #1e293b; text-align: right; font-weight: 600;">{unique_visitors}</td>
            </tr>
        </table>
        
        <h3 style="color: #1e293b; font-size: 14px; font-weight: 600; margin-top: 0; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.05em;">System Diagnostic Logs</h3>
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 24px;">
            <thead>
                <tr style="background-color: #f1f5f9;">
                    <th style="padding: 12px; border: 1px solid #e2e8f0; text-align: left; font-size: 12px; font-weight: bold; color: #475569; text-transform: uppercase;">Severity Level</th>
                    <th style="padding: 12px; border: 1px solid #e2e8f0; text-align: right; font-size: 12px; font-weight: bold; color: #475569; text-transform: uppercase;">Count</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td style="padding: 12px; border: 1px solid #e2e8f0; font-size: 13px; color: #0d9488; font-weight: 600;">INFO</td>
                    <td style="padding: 12px; border: 1px solid #e2e8f0; font-size: 13px; color: #334155; text-align: right;">{log_counts['INFO']}</td>
                </tr>
                <tr style="background-color: #fffbeb;">
                    <td style="padding: 12px; border: 1px solid #e2e8f0; font-size: 13px; color: #d97706; font-weight: 600;">WARNING</td>
                    <td style="padding: 12px; border: 1px solid #e2e8f0; font-size: 13px; color: #334155; text-align: right;">{log_counts['WARNING']}</td>
                </tr>
                <tr style="background-color: #fef2f2;">
                    <td style="padding: 12px; border: 1px solid #e2e8f0; font-size: 13px; color: #dc2626; font-weight: 600;">ERROR</td>
                    <td style="padding: 12px; border: 1px solid #e2e8f0; font-size: 13px; color: #334155; text-align: right;">{log_counts['ERROR']}</td>
                </tr>
                <tr style="background-color: #fef2f2; border-top: 2px solid #dc2626;">
                    <td style="padding: 12px; border: 1px solid #e2e8f0; font-size: 13px; color: #991b1b; font-weight: 600;">CRITICAL</td>
                    <td style="padding: 12px; border: 1px solid #e2e8f0; font-size: 13px; color: #334155; text-align: right;">{log_counts['CRITICAL']}</td>
                </tr>
            </tbody>
        </table>
        
        <p style="color: #94a3b8; font-size: 11px; margin-top: 32px; border-top: 1px solid #f1f5f9; padding-top: 12px; text-align: center; line-height: 1.5;">
            Generated automatically by the FlexURL daily analytics dispatch agent.
        </p>
    </div>
    """
    
    payload = {
        "from": "FlexURL Reports <onboarding@resend.dev>",
        "to": [TARGET_EMAIL],
        "subject": f"FlexURL Executive Summary - {now.strftime('%Y-%m-%d')}",
        "html": html_content
    }
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=headers, json=payload, timeout=10)
            resp.raise_for_status()
        logger.info("Daily executive summary report email dispatched successfully via Resend API.")
    except Exception as e:
        logger.error(f"Failed to dispatch daily executive report email via Resend API: {e}")

async def daily_report_scheduler_loop():
    """
    Runs an infinite async loop that checks the time every 15 minutes.
    Dispatches a daily status email at midnight UTC once daily.
    """
    logger.info("Starting daily executive report background scheduler loop...")
    while True:
        # Check every 15 minutes
        await asyncio.sleep(900)
        try:
            now = datetime.datetime.now(datetime.timezone.utc)
            # Run at midnight (during the first hour: 00:00 - 00:59 UTC)
            if now.hour == 0:
                current_date = now.strftime("%Y-%m-%d")
                
                # Check Redis to prevent duplicate reports
                sent_today = False
                try:
                    last_sent = redis_client.get("daily_report_last_sent")
                    if last_sent == current_date:
                        sent_today = True
                except Exception as re:
                    logger.warning(f"Failed to check Redis for report key: {re}")
                    marker_file = os.path.join(os.path.dirname(log_file), "daily_report_last_sent.txt")
                    if os.path.exists(marker_file):
                        try:
                            with open(marker_file, "r") as f:
                                if f.read().strip() == current_date:
                                    sent_today = True
                        except Exception:
                            pass
                                
                if not sent_today:
                    await generate_and_send_report()
                    
                    # Mark as sent in Redis
                    try:
                        redis_client.set("daily_report_last_sent", current_date)
                    except Exception:
                        pass
                    # Mark as sent in fallback local file
                    try:
                        marker_file = os.path.join(os.path.dirname(log_file), "daily_report_last_sent.txt")
                        with open(marker_file, "w") as f:
                            f.write(current_date)
                    except Exception as fe:
                        logger.error(f"Failed to write fallback report marker file: {fe}")
        except Exception as ex:
            logger.critical(f"Unhandled error in daily report scheduler loop: {ex}")
