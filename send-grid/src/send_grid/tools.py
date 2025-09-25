import asyncio
from typing import Any, Dict, Optional
import logging

from google.adk.tools import ToolContext
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

log = logging.getLogger(__name__)


async def send_email(
    to_email: str,
    subject: str,
    content: str,
    from_email: Optional[str] = None,
    is_html: bool = False,
    tool_context: Optional[ToolContext] = None,
    tool_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Send an email using SendGrid.

    Args:
        to_email: Recipient email address
        subject: Email subject
        content: Email body content (plain text or HTML)
        from_email: Sender email address (defaults to tool_config['from_email'])
        is_html: If True, sends HTML email instead of plain text
        tool_context: Optional tool context
        tool_config: Optional config dict, must include {"api_key": "...", "from_email": "..."}

    Returns:
        A dict with status and either success or error details
    """
    log_identifier = "[send_email]"
    log.info("%s Preparing to send email to %s", log_identifier, to_email)

    try:
        api_key = (tool_config or {}).get("sendgrid_api_key")
        sender = from_email or (tool_config or {}).get("default_from_email")

        if not sender or not api_key:
            return {
                "status": "error",
                "message": "Missing sender email or API key in tool_config",
            }

        message = Mail(
            from_email=sender,
            to_emails=to_email,
            subject=subject,
            html_content=content if is_html else None,
            plain_text_content=content if not is_html else None,
        )

        def _send():
            sg = SendGridAPIClient(api_key)
            return sg.send(message)

        response = await asyncio.to_thread(_send)

        return {
            "status": "success",
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "response_body": response.body.decode() if hasattr(response.body, "decode") else str(response.body),
            "content": content,
            "subject": subject,
            "to_email": to_email,
        }

    except Exception as e:
        log.error("%s Failed to send email: %s", log_identifier, str(e), exc_info=True)
        return {
            "status": "error",
            "message": str(e)
        }
