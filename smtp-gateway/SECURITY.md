# Security Documentation for SMTP Gateway Plugin

## Overview
This document outlines the security measures implemented in the SMTP Gateway plugin to ensure safe and secure email operations.

## Security Features

### 1. Connection Security
- **TLS/SSL Encryption**: All SMTP connections use TLS by default (port 587)
- **SSL Encryption**: All IMAP connections use SSL by default (port 993)
- **Secure Authentication**: Credentials transmitted over encrypted connections only

### 2. Input Validation

#### Email Address Validation
- Uses `email-validator` library for RFC-compliant validation
- Normalizes email addresses to prevent bypass attempts
- Validates all recipients (to, cc, bcc) before sending

#### Subject Line Validation
- Enforces RFC 5322 limit of 998 characters
- Prevents header injection attacks

#### File Path Validation
- Absolute path resolution to prevent relative path attacks
- Directory vs file validation
- Path traversal protection with `os.path.abspath()` checks

### 3. File Security

#### Filename Sanitization
```python
def _sanitize_filename(filename: str) -> str:
    # Removes path components
    # Strips dangerous characters
    # Limits filename length to 255 characters
```

#### File Type Validation
- Whitelist-based extension validation
- Configurable allowed file types
- Default whitelist: pdf, doc, docx, txt, jpg, jpeg, png, gif, zip, csv, xlsx, ppt, pptx

#### File Size Limits
- Default 25MB limit (configurable)
- Validates both upload and download operations
- Prevents memory exhaustion attacks

### 4. Content Security

#### HTML Sanitization
```python
def _sanitize_html_content(content: str, is_html: bool) -> str:
    # Removes <script> tags
    # Strips event handlers (onclick, onload, etc.)
    # Removes javascript: protocol
```

**Note**: For production use with untrusted HTML, consider using the `bleach` library for more comprehensive sanitization.

### 5. Path Traversal Protection

#### Download Operations
- Sanitizes download paths with `os.path.abspath()`
- Validates final path stays within allowed directory
- Double-checks with `startswith()` validation

#### Attachment Processing
- Resolves absolute paths before processing
- Validates file existence and type
- Prevents directory traversal in attachment names

## Configuration Security

### Environment Variables
All sensitive credentials stored in environment variables:
- `SMTP_USERNAME` / `SMTP_PASSWORD`
- `IMAP_USERNAME` / `IMAP_PASSWORD`

**Never** hardcode credentials in configuration files.

### Recommended Settings

```bash
# Gmail Example (with app-specific password)
export SMTP_HOST="smtp.gmail.com"
export SMTP_PORT="587"
export SMTP_USERNAME="your-email@gmail.com"
export SMTP_PASSWORD="your-16-char-app-password"
export IMAP_HOST="imap.gmail.com"
export IMAP_PORT="993"
export IMAP_USERNAME="your-email@gmail.com"
export IMAP_PASSWORD="your-16-char-app-password"
```

## Security Best Practices

### For Administrators

1. **Use App-Specific Passwords**
   - Enable 2FA on email accounts
   - Generate app-specific passwords
   - Rotate passwords regularly

2. **Limit File Types**
   - Configure `allowed_attachment_types` restrictively
   - Only allow business-necessary file types
   - Regularly review and update whitelist

3. **Monitor Usage**
   - Implement rate limiting at infrastructure level
   - Monitor for unusual patterns
   - Set up alerts for failed authentication

4. **Regular Updates**
   - Keep dependencies updated
   - Monitor security advisories
   - Apply patches promptly

5. **Audit Logging**
   - Review logs regularly
   - Monitor for suspicious activity
   - Implement log retention policies

### For Developers

1. **Input Validation**
   - Always validate user inputs
   - Use type hints consistently
   - Handle edge cases explicitly

2. **Error Handling**
   - Never expose sensitive information in errors
   - Log errors with appropriate detail
   - Return user-friendly error messages

3. **Testing**
   - Test with malicious inputs
   - Verify path traversal protection
   - Test file size limits

## Known Limitations

1. **HTML Sanitization**: Basic implementation provided. For production use with untrusted HTML, integrate `bleach` library.

2. **Rate Limiting**: Not implemented at plugin level. Must be handled at infrastructure level.

3. **Virus Scanning**: Not included. Integrate with antivirus solution if needed.

4. **Email Content Inspection**: Plugin does not inspect email content for malicious payloads.

## Threat Model

### Mitigated Threats
- ✅ Path traversal attacks
- ✅ Email header injection
- ✅ XSS via HTML emails (basic)
- ✅ Malicious filenames
- ✅ File type confusion
- ✅ Memory exhaustion (file size limits)
- ✅ Credential exposure (env vars only)

### Threats Requiring Additional Measures
- ⚠️ Rate limiting / DoS (infrastructure level)
- ⚠️ Virus/malware in attachments (antivirus integration)
- ⚠️ Advanced XSS (use bleach library)
- ⚠️ Email spoofing (SPF/DKIM/DMARC at mail server)

## Incident Response

If a security issue is discovered:

1. **Report**: Open an issue in the repository
2. **Assess**: Determine severity and impact
3. **Patch**: Develop and test fix
4. **Deploy**: Update plugin version
5. **Notify**: Inform users of security update

## Compliance Considerations

- **GDPR**: Email content may contain personal data
- **Data Retention**: Configure appropriate retention policies
- **Encryption**: All data in transit is encrypted
- **Access Control**: Implement at SAM level

## Security Checklist

Before deploying to production:

- [ ] Environment variables configured
- [ ] App-specific passwords generated
- [ ] File type whitelist reviewed
- [ ] File size limits appropriate
- [ ] Rate limiting implemented
- [ ] Monitoring configured
- [ ] Logs reviewed regularly
- [ ] Backup strategy in place
- [ ] Incident response plan documented
- [ ] Security training completed

## Contact

For security concerns, please open an issue in the repository with the `security` label.

---

Last Updated: February 2026
Version: 0.1.0