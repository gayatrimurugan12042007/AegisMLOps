# Development environment dependencies

The project environment is Python 3.12. Install with `python3.12 -m venv .venv` followed by `.venv/bin/python -m pip install -r requirements.txt`. `requirements.txt` is a fully pinned environment lock, including resolved transitive dependencies. It was generated after installation on 2026-10-25. Runtime code deployed to Lambda must not install this research environment; Lambda is restricted to the standard library and boto3 as documented in `AGENTS.md`.

Directly selected packages and their purposes:

- `numpy`, `pandas`, `scipy`, `scikit-learn`: data processing, statistics, and model training.
- `pyarrow`: Parquet support.
- `matplotlib`, `seaborn`: analysis plots.
- `streamlit`: local dashboard.
- `requests`: local acquisition utilities; Lambda API access uses `urllib` instead.
- `certifi`: pinned public CA roots for HTTPS verification in the local Python runtime.
- `joblib`: local model tooling.
- `pytest`: tests.
- `ruff`: formatting and linting.
- `pre-commit`: local hook runner.
- `detect-secrets`: pre-commit secret scanning.
- `pre-commit-hooks`: YAML, whitespace, and end-of-file checks.

Only packages listed in `requirements.txt` are installed. Direct versions and all transitive versions are pinned there. Add or remove packages by editing the requirements and this inventory, then re-locking and documenting the reason here.
