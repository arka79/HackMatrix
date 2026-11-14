"""Allow running CI Doctor as a module: python -m cidoctor"""

from .cli import app

if __name__ == "__main__":
    app()
