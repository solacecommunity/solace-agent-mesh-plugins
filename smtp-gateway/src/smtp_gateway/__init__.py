"""
SMTP Gateway Plugin for Solace Agent Mesh

This plugin provides comprehensive email management capabilities including:
- Sending emails with attachments via SMTP
- Receiving emails via IMAP
- Managing emails (mark read, delete, move)
- Downloading attachments
- Listing folders

Version: 0.1.0
"""

__version__ = "0.1.0"
__author__ = "Solace Community"

from smtp_gateway.tools import (
    send_email,
    receive_emails,
    download_attachment,
    mark_email_read,
    delete_email,
    move_email,
    list_folders,
)

from smtp_gateway.services import SMTPService, IMAPService

__all__ = [
    "send_email",
    "receive_emails",
    "download_attachment",
    "mark_email_read",
    "delete_email",
    "move_email",
    "list_folders",
    "SMTPService",
    "IMAPService",
]