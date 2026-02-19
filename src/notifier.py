import requests
from src.config import Config
from src.logger import logger

class TelegramNotifier:
    @staticmethod
    def send_message(message: str):
        if not Config.TELEGRAM_ENABLED:
            logger.debug("Telegram notification disabled.")
            return

        if not Config.TELEGRAM_BOT_TOKEN or not Config.TELEGRAM_CHAT_ID:
            logger.warning("Telegram Bot Token or Chat ID not configured.")
            return

        url = f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": Config.TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }

        try:
            proxies = None
            if Config.PROXY:
                proxies = {
                    "http": Config.PROXY,
                    "https": Config.PROXY,
                }
            response = requests.post(url, json=payload, timeout=10, proxies=proxies)
            response.raise_for_status()
            logger.info("Telegram notification sent successfully.")
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")

    @staticmethod
    def notify_batch_result(total: int, success: int, failures: int, details: list = None):
        status_icon = "✅" if failures == 0 else "⚠️"
        message = (
            f"<b>{status_icon} X Downloader Batch Report</b>\n\n"
            f"<b>Total processed:</b> {total}\n"
            f"<b>Success:</b> {success}\n"
            f"<b>Failures:</b> {failures}\n"
        )
        
        if details and failures > 0:
            message += "\n<b>Failure Details:</b>\n"
            for fail in details[:5]: # Limit to first 5 failures to avoid too long message
                message += f"• {fail['url']}: {fail['error_msg'][:50]}...\n"
            if len(details) > 5:
                message += f"<i>...and {len(details) - 5} more.</i>"

        TelegramNotifier.send_message(message)
