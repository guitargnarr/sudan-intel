"""Generate synthesis briefs using local Ollama.

Generates against local SQLite, then pushes to production via API.

Usage:
    # National brief + push:
    python3 -m backend.scripts.generate_brief

    # All regions + national:
    python3 -m backend.scripts.generate_brief --regions

    # Generate only (no push):
    python3 -m backend.scripts.generate_brief --no-push
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


async def push_brief(
    client, api_url, content, scope="national",
    region_code=None,
):
    resp = await client.post(
        f"{api_url}/api/synthesis/push",
        json={
            "content": content,
            "scope": scope,
            "region_code": region_code,
            "brief_type": "situation_overview",
            "model_used": "sudan-intel-analyst",
        },
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()


async def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--no-push", action="store_true",
        help="Generate only, don't push to production",
    )
    parser.add_argument(
        "--regions", action="store_true",
        help="Also generate briefs for all regions",
    )
    parser.add_argument(
        "--api-url", default=PROD_API,
        help="API base URL for push",
    )
    args = parser.parse_args()

    from sqlalchemy import select

    from backend.core.database import AsyncSessionLocal
    from backend.models.models import ConflictEvent
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
        # National brief
        logger.info("Generating national brief...")
        content = await gen.generate_national_brief(db)

        if not content or content.startswith("[Ollama"):
            logger.error(
                "Brief generation failed: %s",
                content or "empty response",
            )
            sys.exit(1)

        logger.info(
            "National brief: %d chars", len(content)
        )
        print("\n--- National Brief ---\n")
        print(content)

        if not args.no_push:
            async with httpx.AsyncClient() as client:
                r = await push_brief(
                    client, args.api_url, content,
                )
                logger.info("Pushed national: %s", r)

                # Regional briefs
                if args.regions:
                    result = await db.execute(
                        select(
                            ConflictEvent.admin1_code,
                            ConflictEvent.admin1_name,
                        ).where(
                            ConflictEvent.admin1_code
                            .isnot(None),
                            ConflictEvent.admin1_code
                            .like("SD%"),
                        ).distinct()
                    )
                    regions = result.all()
                    logger.info(
                        "Generating %d region briefs...",
                        len(regions),
                    )

                    for reg in regions:
                        logger.info(
                            "Region: %s (%s)",
                            reg.admin1_name,
                            reg.admin1_code,
                        )
                        rc = (
                            await gen.generate_region_brief(
                                db,
                                reg.admin1_code,
                                reg.admin1_name,
                            )
                        )
                        if rc and not rc.startswith(
                            "[Ollama"
                        ):
                            r = await push_brief(
                                client,
                                args.api_url,
                                rc,
                                scope="admin1",
                                region_code=reg.admin1_code,
                            )
                            logger.info(
                                "Pushed %s: %s",
                                reg.admin1_code, r,
                            )
                        else:
                            logger.warning(
                                "Skipped %s",
                                reg.admin1_code,
                            )

    print("\n--- Done ---\n")


if __name__ == "__main__":
    asyncio.run(main())
