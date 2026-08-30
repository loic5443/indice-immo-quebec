"""Transient official aerial-image retrieval for a consented property lookup.

The image is visual context only.  It is never used by ImmoValue, ImmoScore,
financial calculations, telemetry, diagnostics, drafts, exports or PDFs.
Coordinates are accepted only after the person has explicitly consented to a
public-address lookup, are used for one official MRNF request, and are not
included in the returned result.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Callable
from urllib.parse import urlencode, urlparse

import requests
from PIL import Image, ImageStat


WMS_URL = "https://servicesmatriciels.mern.gouv.qc.ca/erdas-iws/ogc/wms/Imagerie_Aeroportee_Forestiere_Historique"
WMS_HOST = "servicesmatriciels.mern.gouv.qc.ca"
SOURCE_ID = "mrnf_imagerie_orthorectifiee"
SOURCE_LABEL = "MRNF — Imagerie orthorectifiée du Québec"
# The official service publishes two complementary acquisition programs.  The
# ecoforest inventory layer has broader useful coverage in several populated
# sectors than the planning/follow-up layer that was initially queried alone.
# Both remain official MRNF imagery, are fetched only after consent, and are
# visual context only.  The publication is still a collection of acquisitions,
# not a promise of a province-wide current photo.  Try only a short list of
# newest verified layers so a selection never starts a long series of requests.
AERIAL_LAYERS: tuple[tuple[int, str], ...] = (
    (2025, "Inventaire_Ecoforestier_2025_2025_Inv_Ecofor_20cm_RVB"),
    (2025, "Planification_Suivi_Controle_2025_2025_Planif_Suiv_Cont_20cm_RVB"),
    (2024, "Inventaire_Ecoforestier_2024_2024_Inv_Ecofor_20cm_RVB"),
    (2024, "Planification_Suivi_Controle_2024_2024_Planif_Suiv_Cont_20cm_RVB"),
    (2023, "Inventaire_Ecoforestier_2023_2023_Inv_Ecofor_20cm_RVB"),
)
# Kept as a compatibility alias for callers and documentation that refer to
# the newest layer.  The response itself always records the actual year used.
LAYER = AERIAL_LAYERS[0][1]
ACQUISITION_YEAR = AERIAL_LAYERS[0][0]
REQUEST_TIMEOUT_SECONDS = 4.0
MAX_IMAGE_BYTES = 1_500_000
IMAGE_WIDTH = 512
IMAGE_HEIGHT = 360


@dataclass(frozen=True)
class AerialImageResponse:
    """A safe render payload containing no address or coordinate."""

    status: str
    image_bytes: bytes | None = None
    mime_type: str = "image/png"
    acquisition_year: int | None = None
    message: str = ""


def _valid_coordinate(longitude: object, latitude: object) -> bool:
    """Accept only a plausible Québec longitude/latitude pair."""

    if isinstance(longitude, bool) or isinstance(latitude, bool):
        return False
    if not isinstance(longitude, (int, float)) or not isinstance(latitude, (int, float)):
        return False
    return -80.0 <= float(longitude) <= -57.0 and 44.0 <= float(latitude) <= 63.0


def _get_map_url(longitude: float, latitude: float, layer: str = LAYER) -> str:
    """Build a bounded WMS request. Coordinates do not leave this function."""

    # About 230 m × 230 m around the selected civic point: enough property
    # context without requesting an unnecessary broad neighbourhood image.
    half_span = 0.0015
    params = {
        "service": "WMS",
        "request": "GetMap",
        "version": "1.1.1",
        "layers": layer,
        "styles": "",
        "srs": "EPSG:4326",
        "bbox": f"{longitude - half_span:.6f},{latitude - half_span:.6f},{longitude + half_span:.6f},{latitude + half_span:.6f}",
        "width": str(IMAGE_WIDTH),
        "height": str(IMAGE_HEIGHT),
        "format": "image/png",
        "transparent": "false",
    }
    return f"{WMS_URL}?{urlencode(params)}"


def _fetch_image(url: str) -> tuple[bytes, str]:
    """Fetch only from the declared MRNF HTTPS WMS endpoint."""

    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != WMS_HOST:
        raise ValueError("official_host_required")
    response = requests.get(
        url,
        headers={"Accept": "image/png", "User-Agent": "ImmoRadar/1.0"},
        timeout=REQUEST_TIMEOUT_SECONDS,
        allow_redirects=False,
    )
    response.raise_for_status()
    if response.is_redirect:
        raise ValueError("redirect_refused")
    image_bytes = response.content
    mime_type = (response.headers.get("Content-Type") or "").split(";", 1)[0].lower()
    if mime_type != "image/png" or not image_bytes or len(image_bytes) > MAX_IMAGE_BYTES:
        raise ValueError("invalid_image")
    return image_bytes, mime_type


def _is_useful_image(image_bytes: bytes) -> bool:
    """Reject malformed, over-sized and blank WMS renderings."""

    try:
        with Image.open(BytesIO(image_bytes)) as image:
            if image.format != "PNG" or image.width > IMAGE_WIDTH or image.height > IMAGE_HEIGHT:
                return False
            # A uniform WMS canvas means that this acquisition has no useful
            # image at the selected point. Do not pretend that it is a photo.
            stats = ImageStat.Stat(image.convert("RGB"))
            return any(variance > 0.5 for variance in stats.var)
    except Exception:
        return False


def fetch_aerial_image(
    longitude: object,
    latitude: object,
    consent: bool,
    *,
    fetch_image: Callable[[str], tuple[bytes, str]] | None = None,
) -> AerialImageResponse:
    """Return a compact, consented aerial view or a safe unavailable state."""

    if not consent:
        return AerialImageResponse("consent_required", message="Activez la recherche publique pour afficher une vue aérienne officielle.")
    if not _valid_coordinate(longitude, latitude):
        return AerialImageResponse("unavailable", message="Vue aérienne indisponible : la source publique ne fournit pas de position utilisable.")
    for acquisition_year, layer in AERIAL_LAYERS:
        try:
            image_bytes, mime_type = (fetch_image or _fetch_image)(
                _get_map_url(float(longitude), float(latitude), layer)
            )
        except Exception:
            # A service failure is not a coverage signal.  Stop immediately
            # instead of multiplying failing external calls on a rerun.
            break
        if mime_type == "image/png" and len(image_bytes) <= MAX_IMAGE_BYTES and _is_useful_image(image_bytes):
            return AerialImageResponse(
                "available",
                image_bytes=image_bytes,
                mime_type=mime_type,
                acquisition_year=acquisition_year,
            )
    # Do not retain endpoint, coordinate or provider details in any UI
    # error: all remain an internal, consented request failure or a sector
    # without a useful public acquisition.
    return AerialImageResponse("unavailable", message="Vue aérienne officielle indisponible pour cette adresse. Vous pouvez continuer votre analyse.")
