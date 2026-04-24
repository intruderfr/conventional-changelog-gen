"""Allow running the package as ``python -m conventional_changelog``."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
