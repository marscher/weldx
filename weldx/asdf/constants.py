import os
from pathlib import Path

from asdf.util import filepath_to_url

__all__ = [
    "SCHEMA_PATH",
    "WELDX_SCHEMA_URI_BASE",
    "WELDX_TAG_BASE",
    "WELDX_URL_MAPPING",
]

SCHEMA_PATH = str(Path(__file__).resolve().parents[0] / "schemas")
WELDX_SCHEMA_URI_BASE = "http://weldx.bam.de/schemas/"
WELDX_TAG_BASE = "tag:weldx.bam.de:weldx"
WELDX_URL_MAPPING = [
    (
        WELDX_SCHEMA_URI_BASE,
        filepath_to_url(os.path.join(SCHEMA_PATH, "weldx.bam.de"))
        + "/{url_suffix}.yaml",
    )
]
