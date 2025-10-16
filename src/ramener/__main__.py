try:
    from .main import main
except ImportError:  # pragma: no cover - frozen executable
    from ramener.main import main  # type: ignore


if __name__ == "__main__":
    raise SystemExit(main())
