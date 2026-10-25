"""Smoke checks for the initial project scaffold."""


def test_core_package_imports() -> None:
    """The core package should be importable in the project environment."""
    import aegis

    assert aegis.__doc__ == "AegisMLOps core package."
