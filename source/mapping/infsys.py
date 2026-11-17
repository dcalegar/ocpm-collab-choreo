"""Access to the InfSys mapping mu (rules M1-M8), reused unchanged.

The unified mapping applies M1-M8 by calling the implementation of Calegari et
al. (InfSys, `CalegariDPR26`), repository `dcalegar/ocpm-collab-ppm`, module
`src/mapping/collab_xes_to_ocel.py` (commit 98d5e697). Nothing in that module is
modified or copied: this shim only imports it.

Resolution order:
1. an installed `ocpm-collab-ppm` (`pip install --no-deps -e <clone>`);
2. the clone named by the environment variable `OCPM_COLLAB_PPM`;
3. a sibling clone `../ocpm-collab-ppm` of this repository.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]


def _import():
    try:
        from mapping import collab_xes_to_ocel  # type: ignore
        return collab_xes_to_ocel
    except ImportError:
        pass
    candidates = []
    if os.environ.get("OCPM_COLLAB_PPM"):
        candidates.append(Path(os.environ["OCPM_COLLAB_PPM"]))
    candidates.append(_REPO.parent / "ocpm-collab-ppm")
    for clone in candidates:
        src = clone / "src"
        if (src / "mapping" / "collab_xes_to_ocel.py").is_file():
            sys.path.insert(0, str(src))
            from mapping import collab_xes_to_ocel  # type: ignore
            return collab_xes_to_ocel
    raise ImportError(
        "The InfSys mapping (ocpm-collab-ppm, src/mapping/collab_xes_to_ocel.py) "
        "was not found. Install it with `pip install --no-deps -e <clone>` or set "
        "OCPM_COLLAB_PPM to the clone.")


cx = _import()
