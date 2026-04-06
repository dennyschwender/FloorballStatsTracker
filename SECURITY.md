# Security Policy

## Reporting Security Vulnerabilities

If you discover a security vulnerability in this project, please email the maintainers privately rather than using the public issue tracker.

## Supported Versions

The latest version on the `main` branch is actively maintained and receives security updates.

## Security Updates

This project follows the security release schedules of its dependencies:
- Flask (Pallets)
- Werkzeug (Pallets)
- Jinja2 (Pallets)
- SQLAlchemy

### Current Security Posture

**Minimum Dependency Versions** (addressing known CVEs):
- Jinja2 >= 3.1.5 (fixes CVE-2024-56201, CVE-2024-56326)
- Werkzeug >= 3.0.3 (fixes CVE-2024-34069)
- Flask >= 3.1.0
- markupsafe >= 2.1.5

**Python Version**:
- Python 3.12+ (includes security patches)

## Automated Security Scanning

This project uses GitHub Dependabot to automatically detect and report security vulnerabilities. A Dependabot configuration file (`.github/dependabot.yml`) is in place to:
- Check dependencies weekly for known vulnerabilities
- Auto-create pull requests for security updates
- Monitor both pip and Docker dependencies

## Third-Party Audits

Developers are encouraged to run their own security audits using tools like:
- `pip-audit`
- `safety`
- OWASP dependency checks

```bash
# Example: run pip-audit
pip-audit
```

## Contact

For security concerns, please refer to the GitHub Security Advisory process.
