"""
routers/resources.py — powers the "interactive map" on CrisisSafetyMapScreen.

The old screen was 100% fake: a hand-drawn Canvas grid, one hardcoded
"Cedar Haven Wellness Center" card, and a hardcoded phone number that isn't
a real, verified crisis line — so it's been removed rather than kept and
relabeled. This endpoint replaces all of that with real data:

  1. The Android client gets the device's actual GPS coordinates (see
     CrisisSafetyMapScreen's location permission + LocationManager code)
     and sends them here.
  2. This queries a places API for real hospitals/clinics near that point
     and returns them as plain JSON.
  3. Results are sorted by actual straight-line distance; the client
     renders them as radar-style pins and as real "Call" / "Get
     Directions" cards.

Deliberately NOT behind auth (Depends(get_current_user)) — someone in
crisis shouldn't be blocked from finding help by a login problem, and no
user data is read or stored here, just a lat/lon the client already has.

Originally this called OpenStreetMap's free Overpass API — no key needed,
but it's a shared community server with no real uptime guarantee, and it
started timing out (502/504) under totally normal use, which is a
dealbreaker for something a real user in crisis might rely on. Swapped to
Geoapify's Places API: still free (no credit card required for the free
tier — see .env.example), but backed by real infrastructure instead of a
best-effort public mirror, so it responds reliably.

To swap providers again in future (e.g. to Google Places once there's
billing set up), you only need to change _fetch_places() and _classify()
below — the route, the schema, the distance math, and the Android client
all stay exactly the same no matter which provider is behind them.
"""

import logging
import math
import os
from typing import List, Optional

import httpx
from fastapi import APIRouter, HTTPException, Query

from schemas import NearbyResourceOut

router = APIRouter(prefix="/api/v1/resources", tags=["resources"])
logger = logging.getLogger("senti.resources")

GEOAPIFY_API_KEY = os.getenv("GEOAPIFY_API_KEY", "")
GEOAPIFY_URL = "https://api.geoapify.com/v2/places"

# Geoapify's category tree turns out to have a real psychiatry subcategory
# (healthcare.clinic_or_praxis.psychiatry) — much closer to the original
# OSM healthcare=psychotherapist/psychiatrist tags than the generic
# "healthcare.clinic_or_praxis" parent, which would otherwise pull in every
# dermatology/orthopaedics/cardiology practice too. Kept deliberately
# narrow: hospitals (real emergencies + ERs), psychiatry specifically, and
# general practice (walk-in triage when nothing more specific is nearby).
# Pharmacies were tried too but didn't belong here — someone in a mental
# health crisis needs a person/place to go to, not a place that sells
# medication, so that category was dropped.
GEOAPIFY_CATEGORIES = (
    "healthcare.hospital,"
    "healthcare.clinic_or_praxis.psychiatry,"
    "healthcare.clinic_or_praxis.general,"
    "emergency.control_centre"
)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _classify(categories: List[str]) -> str:
    joined = ",".join(categories)
    if "psychiatry" in joined:
        return "psychiatric care"
    if "hospital" in joined:
        return "hospital"
    if "clinic" in joined or "praxis" in joined:
        return "clinic"
    return "clinic"


def _phone(props: dict) -> Optional[str]:
    contact = props.get("contact") or {}
    if contact.get("phone"):
        return contact["phone"]
    raw = (props.get("datasource") or {}).get("raw") or {}
    return raw.get("phone") or raw.get("contact:phone")


async def _fetch_places(lat: float, lon: float, radius_km: float) -> List[dict]:
    """The one function to touch if you ever swap providers again — every-
    thing downstream just expects a list of Geoapify-style feature dicts."""
    if not GEOAPIFY_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="Server is missing GEOAPIFY_API_KEY — get a free key at "
                   "myprojects.geoapify.com and add it to .env (see .env.example).",
        )

    params = {
        "categories": GEOAPIFY_CATEGORIES,
        "filter": f"circle:{lon},{lat},{int(radius_km * 1000)}",
        "bias": f"proximity:{lon},{lat}",
        "limit": 20,
        "apiKey": GEOAPIFY_API_KEY,
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(GEOAPIFY_URL, params=params)
        resp.raise_for_status()
        return resp.json().get("features", [])


@router.get("/nearby", response_model=List[NearbyResourceOut])
async def nearby_resources(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(8.0, gt=0, le=25),
):
    try:
        features = await _fetch_places(lat, lon, radius_km)
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        logger.warning("Geoapify lookup failed: %s", e)
        raise HTTPException(
            status_code=502,
            detail="Couldn't reach the map data service right now. Please try again in a moment.",
        ) from e

    results: List[NearbyResourceOut] = []
    for feature in features:
        props = feature.get("properties", {})
        name = props.get("name")
        if not name:
            continue  # unnamed entries aren't useful to show someone in crisis

        elat, elon = props.get("lat"), props.get("lon")
        if elat is None or elon is None:
            continue

        results.append(
            NearbyResourceOut(
                name=name,
                lat=elat,
                lon=elon,
                distance_km=round(_haversine_km(lat, lon, elat, elon), 2),
                address=props.get("formatted"),
                phone=_phone(props),
                kind=_classify(props.get("categories", [])),
            )
        )

    results.sort(key=lambda r: r.distance_km)
    return results[:15]