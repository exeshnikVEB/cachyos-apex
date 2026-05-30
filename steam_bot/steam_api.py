import asyncio
import logging
from dataclasses import dataclass

import aiohttp

logger = logging.getLogger(__name__)

SEARCH_URL = (
    "https://store.steampowered.com/search/results/"
    "?specials=1&json=1&start={start}&count={count}"
)
DETAILS_URL = "https://store.steampowered.com/api/appdetails?appids={appid}&cc=us&l=english"


@dataclass
class SteamDeal:
    appid: int
    name: str
    discount: int          # percent, e.g. 75
    original_price: str    # formatted, e.g. "$59.99"
    final_price: str       # formatted, e.g. "$14.99"
    description: str
    image_url: str
    store_url: str


async def fetch_discounted_appids(
    session: aiohttp.ClientSession, max_count: int = 100
) -> list[dict]:
    """Return list of {appid, name, discount_percent, original, final} from search."""
    results = []
    start = 0
    batch = min(max_count, 100)

    while len(results) < max_count:
        url = SEARCH_URL.format(start=start, count=batch)
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as r:
                if r.status != 200:
                    break
                data = await r.json(content_type=None)
        except Exception as exc:
            logger.warning("Search request failed: %s", exc)
            break

        items = data.get("items", [])
        if not items:
            break

        for item in items:
            discount = item.get("discount_percent", 0)
            if discount <= 0:
                continue
            results.append(
                {
                    "appid": int(item["id"]),
                    "name": item.get("name", ""),
                    "discount": discount,
                    "original": _format_price(item.get("original_price", 0)),
                    "final": _format_price(item.get("final_price", 0)),
                    "tiny_image": item.get("tiny_image", ""),
                }
            )

        start += batch
        if start >= data.get("total_count", 0):
            break
        # polite delay between pages
        await asyncio.sleep(0.5)

    return results[:max_count]


async def fetch_game_details(
    session: aiohttp.ClientSession, appid: int
) -> dict | None:
    url = DETAILS_URL.format(appid=appid)
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as r:
            if r.status != 200:
                return None
            data = await r.json(content_type=None)
    except Exception as exc:
        logger.warning("Details request for %s failed: %s", appid, exc)
        return None

    app_data = data.get(str(appid), {})
    if not app_data.get("success"):
        return None
    return app_data.get("data")


async def build_deal(
    session: aiohttp.ClientSession, raw: dict
) -> SteamDeal | None:
    appid = raw["appid"]
    details = await fetch_game_details(session, appid)

    if details:
        name = details.get("name", raw["name"])
        short_desc = details.get("short_description", "")
        header_image = details.get("header_image", raw.get("tiny_image", ""))
    else:
        name = raw["name"]
        short_desc = ""
        header_image = raw.get("tiny_image", "")

    return SteamDeal(
        appid=appid,
        name=name,
        discount=raw["discount"],
        original_price=raw["original"],
        final_price=raw["final"],
        description=short_desc[:300] + ("..." if len(short_desc) > 300 else ""),
        image_url=header_image,
        store_url=f"https://store.steampowered.com/app/{appid}/",
    )


def _format_price(cents: int) -> str:
    if cents == 0:
        return "Free"
    return f"${cents / 100:.2f}"
