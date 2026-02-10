"""
Tests for SMTP Gateway Plugin

These tests verify the basic functionality of the SMTP Gateway tools.
Note: These are unit tests that mock external services. Integration tests
require actual SMTP/IMAP server credentials.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from smtp_gateway.tools import (
    send_email,
    receive_emails,
    download_attachment,
    mark_email_read,
    delete_email,
    move_email,
    list_folders,
)


@pytest.mark.asyncio
async def test_send_email_missing_config():
    """Test send_email with missing configuration."""
    result = await send_email(
        to_email="test@example.com",
        subject="Test",
        body="Test body",
        tool_config={}
    )
    
    assert result["status"] == "error"
    assert "configuration" in result["message"].lower()


@pytest.mark.asyncio
async def test_send_email_invalid_email():
    """Test send_email with invalid email address."""
    result = await send_email(
        to_email="invalid-email",
        subject="Test",
        body="Test body",
        tool_config={
            "smtp_host": "smtp.example.com",
            "smtp_username": "user",
            "smtp_password": "pass"
        }
    )
    
    assert result["status"] == "error"
    assert "validation" in result["error_type"]


@pytest.mark.asyncio
async def test_receive_emails_missing_config():
    """Test receive_emails with missing configuration."""
    result = await receive_emails(
        tool_config={}
    )
    
    assert result["status"] == "error"
    assert "configuration" in result["message"].lower()


@pytest.mark.asyncio
async def test_download_attachment_missing_config():
    """Test download_attachment with missing configuration."""
    result = await download_attachment(
        email_id="123",
        attachment_filename="test.pdf",
        tool_config={}
    )
    
    assert result["status"] == "error"
    assert "configuration" in result["message"].lower()


@pytest.mark.asyncio
async def test_mark_email_read_missing_config():
    """Test mark_email_read with missing configuration."""
    result = await mark_email_read(
        email_id="123",
        tool_config={}
    )
    
    assert result["status"] == "error"
    assert "configuration" in result["message"].lower()


@pytest.mark.asyncio
async def test_delete_email_missing_config():
    """Test delete_email with missing configuration."""
    result = await delete_email(
        email_id="123",
        tool_config={}
    )
    
    assert result["status"] == "error"
    assert "configuration" in result["message"].lower()


@pytest.mark.asyncio
async def test_move_email_missing_config():
    """Test move_email with missing configuration."""
    result = await move_email(
        email_id="123",
        to_folder="Archive",
        tool_config={}
    )
    
    assert result["status"] == "error"
    assert "configuration" in result["message"].lower()


@pytest.mark.asyncio
async def test_list_folders_missing_config():
    """Test list_folders with missing configuration."""
    result = await list_folders(
        tool_config={}
    )
    
    assert result["status"] == "error"
    assert "configuration" in result["message"].lower()


@pytest.mark.asyncio
@patch('smtp_gateway.tools.SMTPService')
async def test_send_email_success(mock_smtp_service):
    """Test successful email sending."""
    # Mock the SMTP service
    mock_instance = AsyncMock()
    mock_instance.send_email.return_value = {
        "status": "success",
        "message": "Email sent successfully",
        "recipients": ["test@example.com"],
        "subject": "Test",
        "attachments_count": 0
    }
    mock_smtp_service.return_value = mock_instance
    
    result = await send_email(
        to_email="test@example.com",
        subject="Test",
        body="Test body",
        tool_config={
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "smtp_username": "user@example.com",
            "smtp_password": "password",
            "smtp_use_tls": True
        }
    )
    
    assert result["status"] == "success"
    assert "timestamp" in result


@pytest.mark.asyncio
@patch('smtp_gateway.tools.IMAPService')
async def test_receive_emails_success(mock_imap_service):
    """Test successful email receiving."""
    # Mock the IMAP service
    mock_instance = AsyncMock()
    mock_instance.fetch_emails.return_value = {
        "status": "success",
        "emails": [
            {
                "id": "1",
                "from": "sender@example.com",
                "subject": "Test Email",
                "date": "Mon, 10 Feb 2026 12:00:00 +0000"
            }
        ],
        "count": 1,
        "folder": "INBOX"
    }
    mock_imap_service.return_value = mock_instance
    
    result = await receive_emails(
        tool_config={
            "imap_host": "imap.example.com",
            "imap_port": 993,
            "imap_username": "user@example.com",
            "imap_password": "password",
            "imap_use_ssl": True
        }
    )
    
    assert result["status"] == "success"
    assert "emails" in result
    assert "timestamp" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])