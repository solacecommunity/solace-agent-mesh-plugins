"""
SMTP Gateway Services

This module contains service classes for SMTP and IMAP operations.
"""

import asyncio
import ssl
from typing import Optional, List, Dict, Any, Tuple
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.utils import parseaddr, formataddr
import logging

import aiosmtplib
import aioimaplib

log = logging.getLogger(__name__)


class SMTPService:
    """Service for sending emails via SMTP."""
    
    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        use_tls: bool = True,
        timeout: int = 30
    ):
        """
        Initialize SMTP service.
        
        Args:
            host: SMTP server hostname
            port: SMTP server port
            username: SMTP username
            password: SMTP password
            use_tls: Whether to use TLS (default: True)
            timeout: Connection timeout in seconds
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.timeout = timeout
        
    async def send_email(
        self,
        from_email: str,
        to_email: str,
        subject: str,
        body: str,
        is_html: bool = False,
        attachments: Optional[List[Tuple[str, bytes, str]]] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Send an email via SMTP.
        
        Args:
            from_email: Sender email address
            to_email: Recipient email address
            subject: Email subject
            body: Email body content
            is_html: Whether body is HTML (default: False)
            attachments: List of (filename, content, mime_type) tuples
            cc: List of CC recipients
            bcc: List of BCC recipients
            
        Returns:
            Dict with status and details
        """
        log_id = "[SMTPService:send_email]"
        log.info(f"{log_id} Preparing to send email to {to_email}")
        
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = formataddr(parseaddr(from_email))
            msg['To'] = to_email
            msg['Subject'] = subject
            
            if cc:
                msg['Cc'] = ', '.join(cc)
            if bcc:
                msg['Bcc'] = ', '.join(bcc)
            
            # Add body
            body_part = MIMEText(body, 'html' if is_html else 'plain', 'utf-8')
            msg.attach(body_part)
            
            # Add attachments
            if attachments:
                for filename, content, mime_type in attachments:
                    part = MIMEBase(*mime_type.split('/'))
                    part.set_payload(content)
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename={filename}'
                    )
                    msg.attach(part)
                    log.info(f"{log_id} Added attachment: {filename}")
            
            # Prepare recipient list
            recipients = [to_email]
            if cc:
                recipients.extend(cc)
            if bcc:
                recipients.extend(bcc)
            
            # Send email
            async with aiosmtplib.SMTP(
                hostname=self.host,
                port=self.port,
                timeout=self.timeout,
                use_tls=self.use_tls
            ) as smtp:
                await smtp.login(self.username, self.password)
                await smtp.send_message(msg, sender=from_email, recipients=recipients)
            
            log.info(f"{log_id} Email sent successfully to {to_email}")
            return {
                "status": "success",
                "message": f"Email sent successfully to {to_email}",
                "recipients": recipients,
                "subject": subject,
                "attachments_count": len(attachments) if attachments else 0
            }
            
        except aiosmtplib.SMTPException as e:
            log.error(f"{log_id} SMTP error: {e}")
            return {
                "status": "error",
                "message": f"SMTP error: {str(e)}",
                "error_type": "smtp_error"
            }
        except Exception as e:
            log.error(f"{log_id} Unexpected error: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"Unexpected error: {str(e)}",
                "error_type": "unknown_error"
            }


class IMAPService:
    """Service for receiving and managing emails via IMAP."""
    
    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        use_ssl: bool = True,
        timeout: int = 30
    ):
        """
        Initialize IMAP service.
        
        Args:
            host: IMAP server hostname
            port: IMAP server port
            username: IMAP username
            password: IMAP password
            use_ssl: Whether to use SSL (default: True)
            timeout: Connection timeout in seconds
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_ssl = use_ssl
        self.timeout = timeout
        
    async def _connect(self) -> aioimaplib.IMAP4_SSL:
        """
        Create and authenticate IMAP connection.
        
        Returns:
            Authenticated IMAP client
        """
        log_id = "[IMAPService:_connect]"
        
        try:
            if self.use_ssl:
                client = aioimaplib.IMAP4_SSL(host=self.host, port=self.port, timeout=self.timeout)
            else:
                client = aioimaplib.IMAP4(host=self.host, port=self.port, timeout=self.timeout)
            
            await client.wait_hello_from_server()
            await client.login(self.username, self.password)
            
            log.info(f"{log_id} Connected and authenticated to IMAP server")
            return client
            
        except Exception as e:
            log.error(f"{log_id} Connection failed: {e}")
            raise
    
    async def list_folders(self) -> Dict[str, Any]:
        """
        List all available IMAP folders.
        
        Returns:
            Dict with status and folder list
        """
        log_id = "[IMAPService:list_folders]"
        log.info(f"{log_id} Listing IMAP folders")
        
        try:
            client = await self._connect()
            
            try:
                response = await client.list()
                
                if response[0] == 'OK':
                    folders = []
                    for folder_data in response[1]:
                        # Parse folder name from response
                        folder_str = folder_data.decode() if isinstance(folder_data, bytes) else folder_data
                        # Extract folder name (last part after quotes)
                        parts = folder_str.split('"')
                        if len(parts) >= 3:
                            folders.append(parts[-2])
                    
                    log.info(f"{log_id} Found {len(folders)} folders")
                    return {
                        "status": "success",
                        "folders": folders,
                        "count": len(folders)
                    }
                else:
                    return {
                        "status": "error",
                        "message": "Failed to list folders",
                        "error_type": "imap_error"
                    }
                    
            finally:
                await client.logout()
                
        except Exception as e:
            log.error(f"{log_id} Error: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"Error listing folders: {str(e)}",
                "error_type": "unknown_error"
            }
    
    async def fetch_emails(
        self,
        folder: str = "INBOX",
        limit: int = 10,
        unread_only: bool = False,
        search_criteria: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetch emails from specified folder.
        
        Args:
            folder: IMAP folder name (default: "INBOX")
            limit: Maximum number of emails to fetch
            unread_only: Only fetch unread emails
            search_criteria: IMAP search criteria (e.g., "FROM user@example.com")
            
        Returns:
            Dict with status and email list
        """
        log_id = "[IMAPService:fetch_emails]"
        log.info(f"{log_id} Fetching emails from {folder}")
        
        try:
            client = await self._connect()
            
            try:
                # Select folder
                await client.select(folder)
                
                # Build search criteria
                if search_criteria:
                    criteria = search_criteria
                elif unread_only:
                    criteria = "UNSEEN"
                else:
                    criteria = "ALL"
                
                # Search for emails
                response = await client.search(criteria)
                
                if response[0] != 'OK':
                    return {
                        "status": "error",
                        "message": "Failed to search emails",
                        "error_type": "imap_error"
                    }
                
                # Get email IDs
                email_ids = response[1][0].split()
                
                # Limit results
                email_ids = email_ids[-limit:] if len(email_ids) > limit else email_ids
                
                emails = []
                for email_id in email_ids:
                    # Fetch email data
                    fetch_response = await client.fetch(email_id, '(RFC822)')
                    
                    if fetch_response[0] == 'OK':
                        email_data = fetch_response[1][0]
                        if isinstance(email_data, tuple) and len(email_data) > 1:
                            # Parse email
                            import email
                            msg = email.message_from_bytes(email_data[1])
                            
                            emails.append({
                                "id": email_id.decode() if isinstance(email_id, bytes) else email_id,
                                "from": msg.get('From', ''),
                                "to": msg.get('To', ''),
                                "subject": msg.get('Subject', ''),
                                "date": msg.get('Date', ''),
                                "has_attachments": any(part.get_content_disposition() == 'attachment' for part in msg.walk())
                            })
                
                log.info(f"{log_id} Fetched {len(emails)} emails")
                return {
                    "status": "success",
                    "emails": emails,
                    "count": len(emails),
                    "folder": folder
                }
                
            finally:
                await client.logout()
                
        except Exception as e:
            log.error(f"{log_id} Error: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"Error fetching emails: {str(e)}",
                "error_type": "unknown_error"
            }
    
    async def mark_as_read(self, email_id: str, folder: str = "INBOX", mark_read: bool = True) -> Dict[str, Any]:
        """
        Mark an email as read or unread.
        
        Args:
            email_id: Email ID
            folder: IMAP folder name
            mark_read: True to mark as read, False for unread
            
        Returns:
            Dict with status
        """
        log_id = "[IMAPService:mark_as_read]"
        log.info(f"{log_id} Marking email {email_id} as {'read' if mark_read else 'unread'}")
        
        try:
            client = await self._connect()
            
            try:
                await client.select(folder)
                
                flag = r'\Seen'
                if mark_read:
                    response = await client.store(email_id, '+FLAGS', flag)
                else:
                    response = await client.store(email_id, '-FLAGS', flag)
                
                if response[0] == 'OK':
                    log.info(f"{log_id} Email marked successfully")
                    return {
                        "status": "success",
                        "message": f"Email marked as {'read' if mark_read else 'unread'}",
                        "email_id": email_id
                    }
                else:
                    return {
                        "status": "error",
                        "message": "Failed to mark email",
                        "error_type": "imap_error"
                    }
                    
            finally:
                await client.logout()
                
        except Exception as e:
            log.error(f"{log_id} Error: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"Error marking email: {str(e)}",
                "error_type": "unknown_error"
            }
    
    async def delete_email(self, email_id: str, folder: str = "INBOX") -> Dict[str, Any]:
        """
        Delete an email.
        
        Args:
            email_id: Email ID
            folder: IMAP folder name
            
        Returns:
            Dict with status
        """
        log_id = "[IMAPService:delete_email]"
        log.info(f"{log_id} Deleting email {email_id}")
        
        try:
            client = await self._connect()
            
            try:
                await client.select(folder)
                
                # Mark for deletion
                response = await client.store(email_id, '+FLAGS', r'\Deleted')
                
                if response[0] == 'OK':
                    # Expunge to permanently delete
                    await client.expunge()
                    
                    log.info(f"{log_id} Email deleted successfully")
                    return {
                        "status": "success",
                        "message": "Email deleted successfully",
                        "email_id": email_id
                    }
                else:
                    return {
                        "status": "error",
                        "message": "Failed to delete email",
                        "error_type": "imap_error"
                    }
                    
            finally:
                await client.logout()
                
        except Exception as e:
            log.error(f"{log_id} Error: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"Error deleting email: {str(e)}",
                "error_type": "unknown_error"
            }
    
    async def move_email(self, email_id: str, from_folder: str, to_folder: str) -> Dict[str, Any]:
        """
        Move an email to a different folder.
        
        Args:
            email_id: Email ID
            from_folder: Source folder
            to_folder: Destination folder
            
        Returns:
            Dict with status
        """
        log_id = "[IMAPService:move_email]"
        log.info(f"{log_id} Moving email {email_id} from {from_folder} to {to_folder}")
        
        try:
            client = await self._connect()
            
            try:
                await client.select(from_folder)
                
                # Copy to destination
                response = await client.copy(email_id, to_folder)
                
                if response[0] == 'OK':
                    # Delete from source
                    await client.store(email_id, '+FLAGS', r'\Deleted')
                    await client.expunge()
                    
                    log.info(f"{log_id} Email moved successfully")
                    return {
                        "status": "success",
                        "message": f"Email moved from {from_folder} to {to_folder}",
                        "email_id": email_id
                    }
                else:
                    return {
                        "status": "error",
                        "message": "Failed to move email",
                        "error_type": "imap_error"
                    }
                    
            finally:
                await client.logout()
                
        except Exception as e:
            log.error(f"{log_id} Error: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"Error moving email: {str(e)}",
                "error_type": "unknown_error"
            }