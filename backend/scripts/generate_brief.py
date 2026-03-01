"""Generate a national synthesis brief using local Ollama.

Connects to whichever database is configured (local SQLite or
Render Postgres via DATABASE_URL env var), aggregates latest data,
calls local Ollama, and writes the brief to synthesis_briefs.

Usage:
    # Against local SQLite (default):
    python3 -m backend.scripts.generate_brief

    # Against Render Postgres:
    DATABASE_URL=postgresql://... python3 -m backend.scripts.generate_brief
"""

import asyncio
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    from backend.core.database import AsyncSessionLocal
    from backend.synthesis.briefing import BriefingGenerator

    gen = BriefingGenerator()

    # Check Ollama first
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

        if content and not content.startswith("[Ollama"):
            logger.info(
                "Brief generated: %d chars. "
                "Written to synthesis_briefs table.",
                len(content),
            )
            print("\n--- Generated Brief ---\n")
            print(content)
            print("\n--- End ---\n")
        else:
            logger.error("Brief generation failed: %s",
                         content or "empty response")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
