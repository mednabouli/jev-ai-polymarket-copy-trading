# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

**Do not open a public issue** for security vulnerabilities. Please report them responsibly:

### How to Report

1. **Email**: [jev-ai-security@proton.me](mailto:jev-ai-security@proton.me) (coming soon)
2. **GitHub Private Vulnerability Reporting**: Use [GitHub's security advisory feature](https://github.com/mednabouli/jev-ai-polymarket-copy-trading/security/advisories/new)

### What to Include

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)
- Your contact information

### Response Timeline

- **Acknowledgment**: Within 48 hours
- **Initial assessment**: Within 5 business days
- **Resolution target**: Depends on severity (see below)

### Severity Levels

| Severity | Description | Target Resolution |
|----------|-------------|-------------------|
| Critical | Remote code execution, private key exposure | 24-48 hours |
| High | Authentication bypass, data leakage | 5-7 days |
| Medium | CSRF, XSS in dashboards | 14 days |
| Low | Informational, best practices | 30 days |

## Security Best Practices

### For Users

1. **Never commit `.env` files** - Add to `.gitignore`
2. **Use environment variables** for all secrets
3. **Rotate credentials** every 90 days minimum
4. **Run in private network** - Don't expose ports publicly
5. **Enable TLS** for production Telegram webhooks
6. **Use paper trading** before deploying real capital

### For Contributors

1. **No secrets in code** - Scan commits before pushing
2. **Validate all inputs** - Especially wallet addresses and market IDs
3. **Use parameterized queries** - Prevent SQL injection
4. **Log responsibly** - Never log tokens, keys, or PII
5. **Keep dependencies updated** - Monitor for CVEs

## Known Limitations

- Simulated order execution (no real wallet signing)
- Public MCP servers (localhost-only in production)
- No rate limiting on MCP endpoints
- Telegram bot token stored in environment only

## Security Updates

Security patches will be announced via:
- GitHub Security Advisories
- Release notes (CHANGELOG.md)
- Telegram channel @jev_ai_updates (coming soon)

## Responsible Disclosure

We appreciate responsible disclosure and will:
- Credit researchers (with permission)
- Provide updates on fix progress
- Coordinate public disclosure after patches are available

**Thank you for helping keep Jev AI secure!**
