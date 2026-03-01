"""Generate a national synthesis brief using local Ollama.

Generates against local SQLite, then pushes to production via API.

Usage:
    # Generate + push to production:
    python3 -m backend.scripts.generate_brief

    # Generate only (no push):
    python3 -m backend.scripts.generate_brief --no-push

    # Push to custom API URL:
    python3 -m backend.scripts.generate_brief --api-url http://...
"""

import asyncio
import logging
import sys

import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

PROD_API = "https://sudan-intel-api.onrender.com"


async def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--no-push", action="store_true",
        help="Generate only, don't push to production",
    )
    parser.add_argument(
        "--api-url", default=PROD_API,
        help="API base URL for push",
    )
    args = parser.parse_args()

    from backend.core.database import AsyncSessionLocal
    from backend.synthesis.briefing import BriefingGenerator

    gen = BriefingGenerator()

    if not await gen.ollama.is_available():
        logger.error(
            "Ollama not available at %s. "
            "Start it with: ollama serve",
            gen.ollama.base_url,
        )
        sys.exit(1)

    async with AsyncSessionLocal() as db:
        logger.info("Generating national brief...")
        content = await gen.generate_national_brief(db)

        if not content or content.startswith("[Ollama"):
            logger.error(
                "Brief generation failed: %s",
                content or "empty response",
            )
            sys.exit(1)

        logger.info("Brief generated: %d chars", len(content))
        print("\n--- Generated Brief ---\n")
        print(content)
        print("\n--- End ---\n")

        if not args.no_push:
            logger.info(
                "Pushing to production: %s", args.api_url
            )
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{args.api_url}/api/synthesis/push",
                    json={
                        "content": content,
                        "scope": "national",
                        "brief_type": "situation_overview",
                        "model_used": "sudan-intel-analyst",
                    },
                    timeout=30,
                )
                resp.raise_for_status()
                result = resp.json()
                logger.info(
                    "Pushed to production: %s", result
                )


if __name__ == "__main__":
    asyncio.run(main())
