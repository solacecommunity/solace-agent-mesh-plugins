"""
SMTP Gateway Tools

This module contains all the tools for the SMTP Gateway Agent.
"""

import os
import asyncio
import mimetypes
from typing import Any, Dict, Optional, List
from datetime import datetime, timezone
from pathlib import Path
import logging

from email_validator import validate_email, EmailNotValidError
import aiofiles

from smtp_gateway.services import SMTPService, IMAPService

log = logging.getLogger(__name__)


def _validate_email_address(email: str) -> tuple[bool, str]:
    """
    Validate an email address.
    
    Args:
        email: Email address to validate
        
    Returns:
        Tuple of (is_valid, normalized_email or error_message)
    """
    try:
        validated = validate_email(email, check_deliverability=False)
        return True, validated.normalized
    except EmailNotValidError as e:
        return False, str(e)


def _validate_attachment_size(size_bytes: int, max_size_mb: int) -> tuple[bool, str]:
    """
    Validate attachment size.
    
    Args:
        size_bytes: Size in bytes
        max_size_mb: Maximum allowed size in MB
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    max_bytes = max_size_mb * 1024 * 1024
    if size_bytes > max_bytes:
        return False, f"Attachment size ({size_bytes / 1024 / 1024:.2f}MB) exceeds maximum allowed size ({max_size_mb}MB)"
    return True, ""


def _get_mime_type(filename: str) -> str:
    """
    Get MIME type for a file.
    
    Args:
        filename: File name
        
    Returns:
        MIME type string
    """
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type or "application/octet-stream"


async def send_email(
    to_email: str,
    subject: str,
    body: str,
    from_email: Optional[str] = None,
    is_html: bool = False,
    attachment_paths: Optional[List[str]] = None,
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None,
    tool_context: Optional[Any] = None,
    tool_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Send an email with optional attachments via SMTP.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        body: Email body content (plain text or HTML)
        from_email: Sender email address (defaults to SMTP username)
        is_html: If True, body is treated as HTML (default: False)
        attachment_paths: List of file paths to attach
        cc: List of CC recipient email addresses
        bcc: List of BCC recipient email addresses
        tool_context: Optional tool context
        tool_config: Configuration dict with SMTP settings
        
    Returns:
        Dict with status and details
    """
    log_id = "[send_email]"
    log.info(f"{log_id} Preparing to send email to {to_email}")
    
    try:
        # Get configuration
        config = tool_config or {}
        smtp_host = config.get("smtp_host")
        smtp_port = int(config.get("smtp_port", 587))
        smtp_username = config.get("smtp_username")
        smtp_password = config.get("smtp_password")
        smtp_use_tls = config.get("smtp_use_tls", True)
        max_attachment_size_mb = int(config.get("max_attachment_size_mb", 25))
        
        # Validate required config
        if not all([smtp_host, smtp_username, smtp_password]):
            return {
                "status": "error",
                "message": "Missing required SMTP configuration (host, username, password)",
                "error_type": "configuration_error"
            }
        
        # Use SMTP username as from_email if not provided
        if not from_email:
            from_email = smtp_username
        
        # Validate email addresses
        is_valid, result = _validate_email_address(to_email)
        if not is_valid:
            return {
                "status": "error",
                "message": f"Invalid recipient email: {result}",
                "error_type": "validation_error"
            }
        to_email = result
        
        is_valid, result = _validate_email_address(from_email)
        if not is_valid:
            return {
                "status": "error",
                "message": f"Invalid sender email: {result}",
                "error_type": "validation_error"
            }
        from_email = result
        
        # Validate CC addresses
        if cc:
            validated_cc = []
            for cc_email in cc:
                is_valid, result = _validate_email_address(cc_email)
                if not is_valid:
                    return {
                        "status": "error",
                        "message": f"Invalid CC email {cc_email}: {result}",
                        "error_type": "validation_error"
                    }
                validated_cc.append(result)
            cc = validated_cc
        
        # Validate BCC addresses
        if bcc:
            validated_bcc = []
            for bcc_email in bcc:
                is_valid, result = _validate_email_address(bcc_email)
                if not is_valid:
                    return {
                        "status": "error",
                        "message": f"Invalid BCC email {bcc_email}: {result}",
                        "error_type": "validation_error"
                    }
                validated_bcc.append(result)
            bcc = validated_bcc
        
        # Process attachments
        attachments = []
        if attachment_paths:
            for file_path in attachment_paths:
                try:
                    # Check if file exists
                    if not os.path.exists(file_path):
                        return {
                            "status": "error",
                            "message": f"Attachment file not found: {file_path}",
                            "error_type": "file_not_found"
                        }
                    
                    # Check file size
                    file_size = os.path.getsize(file_path)
                    is_valid, error_msg = _validate_attachment_size(file_size, max_attachment_size_mb)
                    if not is_valid:
                        return {
                            "status": "error",
                            "message": error_msg,
                            "error_type": "file_too_large"
                        }
                    
                    # Read file content
                    async with aiofiles.open(file_path, 'rb') as f:
                        content = await f.read()
                    
                    # Get filename and MIME type
                    filename = os.path.basename(file_path)
                    mime_type = _get_mime_type(filename)
                    
                    attachments.append((filename, content, mime_type))
                    log.info(f"{log_id} Prepared attachment: {filename} ({mime_type}, {file_size} bytes)")
                    
                except Exception as e:
                    return {
                        "status": "error",
                        "message": f"Error processing attachment {file_path}: {str(e)}",
                        "error_type": "attachment_error"
                    }
        
        # Create SMTP service and send email
        smtp_service = SMTPService(
            host=smtp_host,
            port=smtp_port,
            username=smtp_username,
            password=smtp_password,
            use_tls=smtp_use_tls
        )
        
        result = await smtp_service.send_email(
            from_email=from_email,
            to_email=to_email,
            subject=subject,
            body=body,
            is_html=is_html,
            attachments=attachments if attachments else None,
            cc=cc,
            bcc=bcc
        )
        
        # Add timestamp
        result["timestamp"] = datetime.now(timezone.utc).isoformat()
        
        return result
        
    except Exception as e:
        log.error(f"{log_id} Unexpected error: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"Unexpected error: {str(e)}",
            "error_type": "unknown_error",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


async def receive_emails(
    folder: str = "INBOX",
    limit: int = 10,
    unread_only: bool = False,
    search_from: Optional[str] = None,
    search_subject: Optional[str] = None,
    tool_context: Optional[Any] = None,
    tool_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Retrieve emails from IMAP server with optional filters.
    
    Args:
        folder: IMAP folder name (default: "INBOX")
        limit: Maximum number of emails to retrieve (default: 10)
        unread_only: Only retrieve unread emails (default: False)
        search_from: Filter by sender email address
        search_subject: Filter by subject text
        tool_context: Optional tool context
        tool_config: Configuration dict with IMAP settings
        
    Returns:
        Dict with status and email list
    """
    log_id = "[receive_emails]"
    log.info(f"{log_id} Retrieving emails from {folder}")
    
    try:
        # Get configuration
        config = tool_config or {}
        imap_host = config.get("imap_host")
        imap_port = int(config.get("imap_port", 993))
        imap_username = config.get("imap_username")
        imap_password = config.get("imap_password")
        imap_use_ssl = config.get("imap_use_ssl", True)
        
        # Validate required config
        if not all([imap_host, imap_username, imap_password]):
            return {
                "status": "error",
                "message": "Missing required IMAP configuration (host, username, password)",
                "error_type": "configuration_error"
            }
        
        # Build search criteria
        search_criteria = None
        if search_from or search_subject:
            criteria_parts = []
            if search_from:
                criteria_parts.append(f'FROM "{search_from}"')
            if search_subject:
                criteria_parts.append(f'SUBJECT "{search_subject}"')
            search_criteria = ' '.join(criteria_parts)
        
        # Create IMAP service and fetch emails
        imap_service = IMAPService(
            host=imap_host,
            port=imap_port,
            username=imap_username,
            password=imap_password,
            use_ssl=imap_use_ssl
        )
        
        result = await imap_service.fetch_emails(
            folder=folder,
            limit=limit,
            unread_only=unread_only,
            search_criteria=search_criteria
        )
        
        # Add timestamp
        result["timestamp"] = datetime.now(timezone.utc).isoformat()
        
        return result
        
    except Exception as e:
        log.error(f"{log_id} Unexpected error: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"Unexpected error: {str(e)}",
            "error_type": "unknown_error",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


async def download_attachment(
    email_id: str,
    attachment_filename: str,
    folder: str = "INBOX",
    save_path: Optional[str] = None,
    tool_context: Optional[Any] = None,
    tool_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Download a specific attachment from an email.
    
    Args:
        email_id: Email ID
        attachment_filename: Name of the attachment to download
        folder: IMAP folder name (default: "INBOX")
        save_path: Path to save the attachment (defaults to config download_path)
        tool_context: Optional tool context
        tool_config: Configuration dict with IMAP settings
        
    Returns:
        Dict with status and file path
    """
    log_id = "[download_attachment]"
    log.info(f"{log_id} Downloading attachment {attachment_filename} from email {email_id}")
    
    try:
        # Get configuration
        config = tool_config or {}
        imap_host = config.get("imap_host")
        imap_port = int(config.get("imap_port", 993))
        imap_username = config.get("imap_username")
        imap_password = config.get("imap_password")
        imap_use_ssl = config.get("imap_use_ssl", True)
        download_path = save_path or config.get("download_path", "/tmp/email_attachments")
        
        # Validate required config
        if not all([imap_host, imap_username, imap_password]):
            return {
                "status": "error",
                "message": "Missing required IMAP configuration (host, username, password)",
                "error_type": "configuration_error"
            }
        
        # Create download directory if it doesn't exist
        os.makedirs(download_path, exist_ok=True)
        
        # Create IMAP service
        imap_service = IMAPService(
            host=imap_host,
            port=imap_port,
            username=imap_username,
            password=imap_password,
            use_ssl=imap_use_ssl
        )
        
        # Connect and fetch email
        client = await imap_service._connect()
        
        try:
            await client.select(folder)
            
            # Fetch email
            fetch_response = await client.fetch(email_id, '(RFC822)')
            
            if fetch_response[0] != 'OK':
                return {
                    "status": "error",
                    "message": "Failed to fetch email",
                    "error_type": "imap_error"
                }
            
            email_data = fetch_response[1][0]
            if not isinstance(email_data, tuple) or len(email_data) < 2:
                return {
                    "status": "error",
                    "message": "Invalid email data",
                    "error_type": "data_error"
                }
            
            # Parse email
            import email
            msg = email.message_from_bytes(email_data[1])
            
            # Find and save attachment
            attachment_found = False
            for part in msg.walk():
                if part.get_content_disposition() == 'attachment':
                    filename = part.get_filename()
                    if filename == attachment_filename:
                        attachment_found = True
                        
                        # Get attachment content
                        content = part.get_payload(decode=True)
                        
                        # Save to file
                        file_path = os.path.join(download_path, filename)
                        async with aiofiles.open(file_path, 'wb') as f:
                            await f.write(content)
                        
                        log.info(f"{log_id} Attachment saved to {file_path}")
                        
                        return {
                            "status": "success",
                            "message": f"Attachment downloaded successfully",
                            "file_path": file_path,
                            "filename": filename,
                            "size_bytes": len(content),
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
            
            if not attachment_found:
                return {
                    "status": "error",
                    "message": f"Attachment '{attachment_filename}' not found in email",
                    "error_type": "attachment_not_found"
                }
                
        finally:
            await client.logout()
        
    except Exception as e:
        log.error(f"{log_id} Unexpected error: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"Unexpected error: {str(e)}",
            "error_type": "unknown_error",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


async def mark_email_read(
    email_id: str,
    folder: str = "INBOX",
    mark_as_read: bool = True,
    tool_context: Optional[Any] = None,
    tool_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Mark an email as read or unread.
    
    Args:
        email_id: Email ID
        folder: IMAP folder name (default: "INBOX")
        mark_as_read: True to mark as read, False for unread (default: True)
        tool_context: Optional tool context
        tool_config: Configuration dict with IMAP settings
        
    Returns:
        Dict with status
    """
    log_id = "[mark_email_read]"
    log.info(f"{log_id} Marking email {email_id} as {'read' if mark_as_read else 'unread'}")
    
    try:
        # Get configuration
        config = tool_config or {}
        imap_host = config.get("imap_host")
        imap_port = int(config.get("imap_port", 993))
        imap_username = config.get("imap_username")
        imap_password = config.get("imap_password")
        imap_use_ssl = config.get("imap_use_ssl", True)
        
        # Validate required config
        if not all([imap_host, imap_username, imap_password]):
            return {
                "status": "error",
                "message": "Missing required IMAP configuration (host, username, password)",
                "error_type": "configuration_error"
            }
        
        # Create IMAP service
        imap_service = IMAPService(
            host=imap_host,
            port=imap_port,
            username=imap_username,
            password=imap_password,
            use_ssl=imap_use_ssl
        )
        
        result = await imap_service.mark_as_read(
            email_id=email_id,
            folder=folder,
            mark_read=mark_as_read
        )
        
        # Add timestamp
        result["timestamp"] = datetime.now(timezone.utc).isoformat()
        
        return result
        
    except Exception as e:
        log.error(f"{log_id} Unexpected error: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"Unexpected error: {str(e)}",
            "error_type": "unknown_error",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


async def delete_email(
    email_id: str,
    folder: str = "INBOX",
    tool_context: Optional[Any] = None,
    tool_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Delete an email from the server.
    
    Args:
        email_id: Email ID
        folder: IMAP folder name (default: "INBOX")
        tool_context: Optional tool context
        tool_config: Configuration dict with IMAP settings
        
    Returns:
        Dict with status
    """
    log_id = "[delete_email]"
    log.info(f"{log_id} Deleting email {email_id}")
    
    try:
        # Get configuration
        config = tool_config or {}
        imap_host = config.get("imap_host")
        imap_port = int(config.get("imap_port", 993))
        imap_username = config.get("imap_username")
        imap_password = config.get("imap_password")
        imap_use_ssl = config.get("imap_use_ssl", True)
        
        # Validate required config
        if not all([imap_host, imap_username, imap_password]):
            return {
                "status": "error",
                "message": "Missing required IMAP configuration (host, username, password)",
                "error_type": "configuration_error"
            }
        
        # Create IMAP service
        imap_service = IMAPService(
            host=imap_host,
            port=imap_port,
            username=imap_username,
            password=imap_password,
            use_ssl=imap_use_ssl
        )
        
        result = await imap_service.delete_email(
            email_id=email_id,
            folder=folder
        )
        
        # Add timestamp
        result["timestamp"] = datetime.now(timezone.utc).isoformat()
        
        return result
        
    except Exception as e:
        log.error(f"{log_id} Unexpected error: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"Unexpected error: {str(e)}",
            "error_type": "unknown_error",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


async def move_email(
    email_id: str,
    to_folder: str,
    from_folder: str = "INBOX",
    tool_context: Optional[Any] = None,
    tool_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Move an email to a different folder.
    
    Args:
        email_id: Email ID
        to_folder: Destination folder name
        from_folder: Source folder name (default: "INBOX")
        tool_context: Optional tool context
        tool_config: Configuration dict with IMAP settings
        
    Returns:
        Dict with status
    """
    log_id = "[move_email]"
    log.info(f"{log_id} Moving email {email_id} from {from_folder} to {to_folder}")
    
    try:
        # Get configuration
        config = tool_config or {}
        imap_host = config.get("imap_host")
        imap_port = int(config.get("imap_port", 993))
        imap_username = config.get("imap_username")
        imap_password = config.get("imap_password")
        imap_use_ssl = config.get("imap_use_ssl", True)
        
        # Validate required config
        if not all([imap_host, imap_username, imap_password]):
            return {
                "status": "error",
                "message": "Missing required IMAP configuration (host, username, password)",
                "error_type": "configuration_error"
            }
        
        # Create IMAP service
        imap_service = IMAPService(
            host=imap_host,
            port=imap_port,
            username=imap_username,
            password=imap_password,
            use_ssl=imap_use_ssl
        )
        
        result = await imap_service.move_email(
            email_id=email_id,
            from_folder=from_folder,
            to_folder=to_folder
        )
        
        # Add timestamp
        result["timestamp"] = datetime.now(timezone.utc).isoformat()
        
        return result
        
    except Exception as e:
        log.error(f"{log_id} Unexpected error: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"Unexpected error: {str(e)}",
            "error_type": "unknown_error",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


async def list_folders(
    tool_context: Optional[Any] = None,
    tool_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    List all available IMAP folders.
    
    Args:
        tool_context: Optional tool context
        tool_config: Configuration dict with IMAP settings
        
    Returns:
        Dict with status and folder list
    """
    log_id = "[list_folders]"
    log.info(f"{log_id} Listing IMAP folders")
    
    try:
        # Get configuration
        config = tool_config or {}
        imap_host = config.get("imap_host")
        imap_port = int(config.get("imap_port", 993))
        imap_username = config.get("imap_username")
        imap_password = config.get("imap_password")
        imap_use_ssl = config.get("imap_use_ssl", True)
        
        # Validate required config
        if not all([imap_host, imap_username, imap_password]):
            return {
                "status": "error",
                "message": "Missing required IMAP configuration (host, username, password)",
                "error_type": "configuration_error"
            }
        
        # Create IMAP service
        imap_service = IMAPService(
            host=imap_host,
            port=imap_port,
            username=imap_username,
            password=imap_password,
            use_ssl=imap_use_ssl
        )
        
        result = await imap_service.list_folders()
        
        # Add timestamp
        result["timestamp"] = datetime.now(timezone.utc).isoformat()
        
        return result
        
    except Exception as e:
        log.error(f"{log_id} Unexpected error: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"Unexpected error: {str(e)}",
            "error_type": "unknown_error",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }