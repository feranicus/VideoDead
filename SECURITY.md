# Security Policy

VideoDead is built secure-by-design, following [CISA Secure by Design](https://www.cisa.gov/securebydesign) principles and Singapore CSA's [Safe App Standard 2.0](https://www.csa.gov.sg/resources/publications/safe-app-standard-2-0/).

## Reporting a vulnerability

Please report security issues privately to the maintainer (open a GitHub Security Advisory on this repository, or email the address in the repo profile). Do **not** open a public issue for vulnerabilities. We aim to acknowledge within 72 hours and to coordinate disclosure responsibly.

## Default-on controls

- **No default password.** First-run wizard forces a strong admin password (Argon2id hashed).
- **MFA available at no cost** (TOTP) — CISA secure-defaults principle.
- **HTTPS only** with HSTS; secure, HttpOnly, SameSite=Strict session cookies.
- **SSRF protection** on submitted URLs: scheme allow-list and blocking of private, loopback, link-local, and cloud-metadata (169.254.169.254) addresses.
- **No shell string building** — yt-dlp is called as a library with a fixed options dict.
- **Rate limiting + lockout** on authentication and job submission.
- **Container hardening**: non-root, dropped capabilities, `no-new-privileges`, resource limits, internal-only network for api/worker/redis.
- **Data minimisation**: downloads auto-purged after a TTL; minimal logging.

## Supply chain

Pinned dependencies, Dependabot, CodeQL, Trivy image scanning, and a generated SBOM (Syft) on every release. Container images are signed with Cosign.

## Memory safety

Application logic is in Python and the edge proxy is Caddy (Go) — both memory-safe languages, consistent with CISA's memory-safety guidance.
