"""Cherion — query-to-visualization agent for clinical trials."""

# Load environment variables from a local .env file (if present) as early as
# possible, so ANTHROPIC_API_KEY / CHERION_MODEL are available to every entry
# point (uvicorn, tests, scripts). Real env vars always take precedence.
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover - dotenv is a declared dependency
    pass
