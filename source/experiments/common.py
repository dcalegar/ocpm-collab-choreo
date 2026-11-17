"""Shared paths and helpers of the experiments.

The experiments read the outputs of `../mapping/map_all.py` in
`data/<dataset>/mapped/` and the reference logs in `data/<dataset>/infsys/` and
`data/<dataset>/hobeck/`. They never change the mapping or its outputs.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "data"
RESULTS = Path(__file__).resolve().parent / "results"
MAPPING = REPO / "source" / "mapping"
sys.path.insert(0, str(MAPPING))

# The 7 collaborative logs of Hobeck et al. and the 4 of InfSys.
HOBECK_XES_LOGS = ["healthcare", "real1", "real2", "real3", "real4", "real5", "smartagriculture"]
INFSYS_LOGS = ["artificial1", "artificial5", "healthcare", "real4"]


def eth_pairs() -> List[Tuple[str, str, Path, Path]]:
    """(dataset, stem, mapped eta_H export, Hobeck et al.'s OCEL) per Ethereum file."""
    out = []
    for d in sorted(DATA.glob("eth-*")):
        for js in sorted((d / "hobeck").glob("*.json")):
            if js.name.endswith("_ocel.json"):
                continue
            out.append((d.name, js.stem, d / "mapped" / f"{js.stem}_hobeck.json",
                        d / "hobeck" / f"{js.stem}_ocel.json"))
    return out


def require(path: Path) -> Path:
    if not path.is_file():
        raise SystemExit(f"missing {path}; run source/mapping/map_all.py first")
    return path


def write_results(name: str, data: Any, markdown: str) -> None:
    RESULTS.mkdir(exist_ok=True)
    with open(RESULTS / f"{name}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False, default=str)
    (RESULTS / f"{name}.md").write_text(markdown, encoding="utf-8")
    print(markdown)


def md_table(header: List[str], rows: List[List[Any]]) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def ocelchor_module(name: str, *submodules: str):
    """Import a package of the ocelchor clone (`$OCELCHOR`, or a sibling
    `../ocelchor`) and the given submodules, unmodified and without writing
    byte code into the clone."""
    clones = ([Path(os.environ["OCELCHOR"])] if os.environ.get("OCELCHOR") else [])
    clones.append(REPO.parent / "ocelchor")
    for clone in clones:
        src = clone / name / "src"
        if (src / name).is_dir():
            if str(src) not in sys.path:
                sys.path.insert(0, str(src))
            break
    else:
        raise SystemExit(f"{name} not found; set OCELCHOR to the ocelchor clone")
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        import importlib
        pkg = importlib.import_module(name)
        for sub in submodules:
            importlib.import_module(f"{name}.{sub}")
        return pkg
    finally:
        sys.dont_write_bytecode = previous


# ---------------------------------------------------------------------------
# OCEL 2.0 SQLite (pm4py layout) as plain sets
# ---------------------------------------------------------------------------

def read_sqlite(path: Path) -> Dict[str, Any]:
    """Events, objects, E2O, and O2O of an OCEL 2.0 SQLite file, with the
    non-null attributes of each event and object."""
    con = sqlite3.connect(str(path))
    q = lambda sql: con.execute(sql).fetchall()
    events = {i: {"type": t, "attrs": {}} for i, t in q("select ocel_id, ocel_type from event")}
    objects = {i: {"type": t, "attrs": {}} for i, t in q("select ocel_id, ocel_type from object")}
    for kind, store in (("event", events), ("object", objects)):
        for (ot, table) in q(f"select ocel_type, ocel_type_map from {kind}_map_type"):
            cur = con.execute(f'select * from "{kind}_{table}"')
            cols = [c[0] for c in cur.description]
            for row in cur:
                rec = dict(zip(cols, row))
                item = store[rec.pop("ocel_id")]
                if "ocel_time" in rec:
                    t = rec.pop("ocel_time")
                    if kind == "event":
                        item["time"] = t
                rec.pop("ocel_changed_field", None)
                rec.pop("ocel:timestamp", None)      # epoch of static object attributes
                item["attrs"].update({k: v for k, v in rec.items() if v is not None})
    e2o = set(q("select ocel_event_id, ocel_object_id, ocel_qualifier from event_object"))
    o2o = set(q("select ocel_source_id, ocel_target_id, ocel_qualifier from object_object"))
    con.close()
    return {"events": events, "objects": objects, "e2o": e2o, "o2o": o2o}
