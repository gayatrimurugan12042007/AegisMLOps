# AegisMLOps contributor instructions

## Project constraints

- Follow the staged plan in the project protocol and do not start AWS resource work before the user explicitly passes Gate A and authorizes Stage B.
- AWS impact must remain $0. Use only free tools and the services explicitly allowed by the project request.
- Never commit secrets, credentials, API keys, personal data, generated datasets, model binaries, or local environment files. Use `.env.example` only for documented variable names with empty/example values.
- Lambda runtime code may use only the Python standard library and `boto3`; model training, analysis, and experiments run locally or in free Google Colab.
- Keep raw data immutable. Record SHA-256 checksums and acquisition metadata for downloaded data.
- Fix random seeds and pin dependency versions. Never fabricate experiment results or tune against the frozen test stream.
- Keep notebooks thin: reusable logic belongs in `aegis/` and notebooks call package functions.
- Make changes in small, reviewable steps. Do not create AWS resources without the phase-specific approval required by the project request.

## Quality and commands

- Format: `ruff format --check .`
- Lint: `ruff check .`
- Unit tests: `python -m pytest`
- Run focused tests during development, then the full suite at phase gates. Do not make network calls from tests; use recorded fixtures.
- Before committing, run secret scanning with `pre-commit run --all-files` (includes the configured secret scanner).

## Engineering style

- Use type hints, docstrings for public functions, small functions, deterministic behavior, and explicit error handling.
- Prefer standard-library implementations in Lambda modules. Keep cloud adapters separate from domain logic.
- Document assumptions and limitations next to the relevant protocol or data documentation.
