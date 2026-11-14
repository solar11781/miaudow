"""Entry point of the MIAUDOW API. Run from api/:  ..\\.venv\\Scripts\\uvicorn main:app"""

from miaudow_api.app import app

__all__ = ["app"]
