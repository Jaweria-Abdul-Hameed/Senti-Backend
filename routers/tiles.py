"""
routers/tiles.py — proxies Geoapify's raster map tiles for the Android
client's live/interactive map.

Same reasoning as GEMINI_API_KEY (see .env.example): the API key stays on
the server and never ships inside the APK. The client just points its map
widget at OUR /api/v1/tiles/{z}/{x}/{y}.png — this endpoint fetches the
real tile from Geoapify (using the key from the environment) and streams
the image bytes straight back. Also means we can swap tile providers later
without ever touching the installed app.

Not behind auth — map tiles aren't sensitive, and gating them would add
latency to something that needs to load fast and often (dozens of tiles
per screen).

Tiles for a given (z, x, y) never change, so every one fetched is saved to
disk once and served from there afterwards. Without this, panning back to
an area you already viewed — completely normal map usage — re-spends
Geoapify credits on tiles you already paid for once. With it, only truly
new tiles ever hit Geoapify; everything else is free and near-instant.
"""

from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException, Response

from routers.resources import GEOAPIFY_API_KEY

router = APIRouter(prefix="/api/v1/tiles", tags=["tiles"])

# "osm-bright" is Geoapify's clean, readable general-purpose style — good
# default for a small in-app map. Full style list: apidocs.geoapify.com.
GEOAPIFY_TILE_URL = "https://maps.geoapify.com/v1/tile/osm-bright/{z}/{x}/{y}.png"

# On-disk tile cache, keyed by style + z/x/y — swapping GEOAPIFY_STYLE (or
# providers later) naturally starts a fresh cache instead of ever serving a
# stale tile from a different style/provider under the same path.
CACHE_DIR = Path(__file__).resolve().parent.parent / "tile_cache" / "osm-bright"


def _cache_path(z: int, x: int, y: int) -> Path:
    return CACHE_DIR / str(z) / str(x) / f"{y}.png"


@router.get("/{z}/{x}/{y}.png")
async def get_tile(z: int, x: int, y: int):
    cache_path = _cache_path(z, x, y)
    if cache_path.exists():
        return Response(content=cache_path.read_bytes(), media_type="image/png")

    if not GEOAPIFY_API_KEY:
        raise HTTPException(status_code=500, detail="Server is missing GEOAPIFY_API_KEY.")

    url = GEOAPIFY_TILE_URL.format(z=z, x=x, y=y)
    async with httpx.AsyncClient(timeout=8.0) as client:
        resp = await client.get(url, params={"apiKey": GEOAPIFY_API_KEY})

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Couldn't fetch that map tile right now.")

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_bytes(resp.content)

    return Response(content=resp.content, media_type="image/png")