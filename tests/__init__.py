try:
    import yaml  # noqa: F401
except ModuleNotFoundError as exc:
    raise ModuleNotFoundError(
        "PyYAML must be installed to run the test suite. Install with 'pip install PyYAML'."
    ) from exc
