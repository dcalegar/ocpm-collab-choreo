#!/usr/bin/env python3
"""Map every log in `data/` to the unified representation.

Writes `data/<dataset>/mapped/<name>{.jsonocel,.sqlite,_hobeck.json,_checks.json}`
(see `map_log.py`) and `data/mapped_summary.json`. The `mapped/` folders are
regenerable and are not versioned.

| Dataset | Name | Input | Profile |
|---|---|---|---|
| 9 collaborative scenarios | `<n>_cl` | `pena/collectivelog_<n>_collab.xes` | collaboration |
| | `<n>_chl` | `pena/collectivelog_<n>_chor.xes` | choreography |
| | `<n>_complete` | both | complete |
| 7 of them (Hobeck et al.) | `<n>_hobeck` | `hobeck/collectivelog_<n>_uniqueInteraction.xes` | collaboration |
| BPIC 2013 | `bpic2013_cl` | `infsys/BPI2013_incidents_collaborative.xes` (identifier `msgId`) | collaboration |
| 12 Ethereum datasets | `<stem>` | `hobeck/<stem>.json` | hierarchical choreography |

Usage: `python map_all.py [data_dir] [--only <dataset> ...]`
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

import map_log
import sources
import unified as u

REPO = Path(__file__).resolve().parents[2]


def jobs(data: Path):
    for d in sorted(p for p in data.iterdir() if p.is_dir()):
        n = d.name
        pena, hob = d / "pena", d / "hobeck"
        cl, chl = pena / f"collectivelog_{n}_collab.xes", pena / f"collectivelog_{n}_chor.xes"
        if cl.is_file():
            yield n, f"{n}_cl", lambda cl=cl: sources.read_cl(cl)
        if chl.is_file():
            yield n, f"{n}_chl", lambda chl=chl: sources.read_chl(chl)
        if cl.is_file() and chl.is_file():
            yield n, f"{n}_complete", lambda cl=cl, chl=chl: sources.combine(
                sources.read_cl(cl), sources.read_chl(chl), name=f"{n}_complete")
        hx = hob / f"collectivelog_{n}_uniqueInteraction.xes"
        if hx.is_file():
            yield n, f"{n}_hobeck", lambda hx=hx: sources.read_hobeck_xes(hx)
        bpic = d / "infsys" / "BPI2013_incidents_collaborative.xes"
        if bpic.is_file():
            yield n, f"{n}_cl", lambda bpic=bpic: sources.read_cl(bpic, sources.BPIC_MSG_KEY)
        if n.startswith("eth-"):
            for js in sorted(hob.glob("*.json")):
                if not js.name.endswith("_ocel.json"):
                    yield n, js.stem, lambda js=js: sources.read_eth_traces(js)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Map every log in data/.")
    p.add_argument("data", nargs="?", default=str(REPO / "data"))
    p.add_argument("--only", nargs="*", help="dataset folders to map")
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
    map_log.logger.setLevel(logging.ERROR)
    logging.getLogger("trace2ocelchor").setLevel(logging.ERROR)   # undefined activities, as in trace2ocelchor
    data = Path(args.data)
    summary, ok = {}, True
    for dataset, name, read in jobs(data):
        if args.only and dataset not in args.only:
            continue
        t0 = time.time()
        res = u.map_log(read())
        report = map_log.write_outputs(res, str(data / dataset / "mapped" / name))
        failed = [c["name"] for c in report["criteria"] if not c["ok"]]
        ok = ok and not failed
        s = res.stats
        summary[name] = {"dataset": dataset, "profile": s["profile"],
                         "events": s["n_events"], "exchange_events": s["n_exchange_events"],
                         "tasks": s["n_tasks"], "two_way_tasks": s["n_two_way_tasks"],
                         "logical_messages": s["n_logical_messages"],
                         "objects": s["n_objects"], "failed_criteria": failed,
                         "logical_messages_with_conflicting_values":
                             s["n_logical_messages_with_conflicting_values"],
                         "u6": next(c["counts"] for c in report["criteria"]
                                    if c["name"].startswith("U6"))}
        print(f"{name:55s} events={s['n_events']:6d} tasks={s['n_tasks']:5d} "
              f"{'ok' if not failed else 'FAILED ' + ','.join(failed)}  ({time.time() - t0:.0f}s)",
              flush=True)
    if not args.only:
        with open(data / "mapped_summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=1)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
