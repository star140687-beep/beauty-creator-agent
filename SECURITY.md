# Security Policy

## Reporting

Please report suspected vulnerabilities privately through GitHub Security Advisories. Do not open a public issue containing credentials, personal data, or exploit details.

## Secret handling

- Copy `.env.example` to `.env` and keep `.env` local.
- Never commit API keys, database passwords, authorization headers, private keys, model prompts containing personal data, or production URLs with embedded credentials.
- GitHub Actions uses `LLM_PROVIDER=fake`; CI requires no Ollama service or paid key.
- Store deployment secrets in GitHub Actions secrets or the target platform's secret manager.
- If a secret is committed, revoke and rotate it immediately; deleting the file in a later commit is insufficient.

## Data handling

- `data/raw`, `data/processed`, and `data/private` are ignored by Git.
- Review imports remove direct user identifiers before normalization.
- External documents are untrusted input and retain provenance.
- Public snapshots must have a documented license and attribution.

