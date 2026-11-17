#!/usr/bin/env python3
"""Map one log, in its original format, to the unified representation.

Outputs, for an output base `<out>`:

- `<out>.jsonocel` and `<out>.sqlite`: mu+(L) in OCEL 2.0, written with the
  InfSys exporters (pm4py);
- `<out>_hobeck.json`: the choreography view exported to the representation
  of Hobeck et al. (eta_H), for `ocelchorvalidator`;
- `<out>_checks.json`: statistics, profile, and criteria P1.1-P1.7, U1-U7.

Examples:

    python map_log.py --cl ../../data/healthcare/pena/collectivelog_healthcare_collab.xes out/hc_cl
    python map_log.py --cl CL.xes --chl ChL.xes out/hc_complete
    python map_log.py --hobeck-xes ../../data/healthcare/hobeck/collectivelog_healthcare_uniqueInteraction.xes out/hc_hobeck
    python map_log.py --eth ../../data/eth-ensgovernor/hobeck/<stem>.json out/ens
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from infsys import cx
import criteria
import export_hobeck
from index import index_of
import sources
import unified as u

logger = logging.getLogger("map_log")


# ---------------------------------------------------------------------------
# Export (serialization artifacts only)
# ---------------------------------------------------------------------------

def export_relations(res: u.UnifiedResult) -> pd.DataFrame:
    """The E2O table handed to the pm4py exporters. pm4py drops every object
    without an E2O relation, so objects reachable only through O2O get one
    witness E2O edge that reuses the O2O qualifier (as the InfSys mapping does
    for participants): first the InfSys witnesses, computed on the InfSys
    tables exactly as InfSys does, then, until no orphan remains, an edge from
    an event of a reachable O2O neighbour. Witnesses are not part of the
    representation; the criteria are evaluated without them."""
    rel = res.relations_df
    if res.infsys is not None:
        w = cx._add_export_reachability_witnesses(
            res.infsys.objects_df, res.infsys.relations_df, res.infsys.o2o_df)
        rel = pd.concat([rel, w.iloc[len(res.infsys.relations_df):]], ignore_index=True)
    otype = dict(zip(res.objects_df[cx.COL_OID], res.objects_df[cx.COL_OTYPE]))
    some_event = {}
    for r in rel.to_dict("records"):
        some_event.setdefault(r[cx.COL_OID], r[cx.COL_EID])
    orphans = set(otype) - set(some_event)
    links = res.o2o_df.to_dict("records")
    added: List[Dict[str, Any]] = []
    while orphans:
        progress = False
        for r in links:
            a, b, q = r[cx.COL_OID], r[cx.COL_OID2], r[cx.COL_QUALIFIER]
            for orphan, anchor in ((b, a), (a, b)):
                if orphan in orphans and anchor in some_event:
                    eid = some_event[anchor]
                    added.append({cx.COL_EID: eid, cx.COL_OID: orphan,
                                  cx.COL_OTYPE: otype[orphan], cx.COL_QUALIFIER: q})
                    some_event[orphan] = eid
                    orphans.discard(orphan)
                    progress = True
        if not progress:
            break
    if added:
        rel = pd.concat([rel, pd.DataFrame(added)], ignore_index=True)
    return rel


def _restore_subsecond_times(json_path: str, events_df: pd.DataFrame) -> None:
    """pm4py's OCEL 2.0 JSON exporter truncates event times to seconds. Restore
    them from the event table, with one precision for the whole log, so that
    the time strings also sort in temporal order. The SQLite export keeps
    them natively."""
    micro = export_hobeck.needs_microseconds(events_df[cx.COL_TIMESTAMP])
    times = {e: export_hobeck.iso(t, micro)
             for e, t in zip(events_df[cx.COL_EID], events_df[cx.COL_TIMESTAMP])}
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    for ev in data.get("events", []):
        ev["time"] = times[ev["id"]]
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def _name_unnamed(df: pd.DataFrame) -> pd.DataFrame:
    """The pm4py SQLite exporter rejects empty column names, which unnamed ABI
    parameters of the Ethereum logs produce (as in Hobeck et al.'s logs). For
    the pm4py exports only, an empty attribute name becomes `unnamed`; the
    export to Hobeck et al.'s representation keeps it."""
    if "" not in df.columns:
        return df
    if "unnamed" in df.columns:
        raise ValueError("attributes named '' and 'unnamed' in the same table")
    return df.rename(columns={"": "unnamed"})


def write_outputs(res: u.UnifiedResult, out: str) -> Dict[str, Any]:
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    rel = export_relations(res)
    ix = index_of(res)
    crits = criteria.infsys_criteria(res, rel) + criteria.unified_criteria(
        ix, res.source.key_attr)
    events_df, objects_df = _name_unnamed(res.events_df), _name_unnamed(res.objects_df)
    ocel = cx.build_ocel_object(events_df, objects_df, rel, res.o2o_df)
    cx.write_ocel2_json(ocel, out + ".jsonocel")
    _restore_subsecond_times(out + ".jsonocel", res.events_df)
    cx.write_ocel2_sqlite(ocel, out + ".sqlite")
    schema = cx.validate_jsonocel(out + ".jsonocel")
    export_hobeck.write(export_hobeck.export(ix), out + "_hobeck.json")
    report = {
        "inputs": res.source.inputs,
        "stats": res.stats,
        "export": {"witness_e2o_edges": len(rel) - len(res.relations_df),
                   "ocel2_json_schema_problems": schema[:25]},
        "mapping_diagnostics": {
            # values that a logical message cannot hold at once (first kept, M10)
            "conflicting_values": res.stats["conflicting_values"],
        },
        "criteria": criteria.as_json(crits),
        "structural_criteria_hold": all(c.ok for c in crits),
    }
    with open(out + "_checks.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1, default=str, ensure_ascii=False)
    if res.stats["conflicting_values"]:
        logger.warning("  %d logical message(s) with conflicting values (first kept; see "
                       "mapping_diagnostics)", res.stats["n_logical_messages_with_conflicting_values"])
    for c in crits:
        logger.info("  [%s] %-28s %s", "ok" if c.ok else "FAIL", c.name,
                    {k: v for k, v in c.counts.items() if k != "detail"} or c.counts.get("detail", ""))
    return report


def read_source(args) -> sources.SourceLog:
    if args.eth:
        return sources.read_eth_traces(args.eth)
    if args.hobeck_xes:
        return sources.read_hobeck_xes(args.hobeck_xes)
    if args.cl and args.chl:
        return sources.combine(sources.read_cl(args.cl, args.key),
                               sources.read_chl(args.chl, args.key))
    if args.cl:
        return sources.read_cl(args.cl, args.key)
    if args.chl:
        return sources.read_chl(args.chl, args.key)
    raise SystemExit("give --cl, --chl, --hobeck-xes, or --eth")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--cl", help="collaboration log (Pena et al.'s CL, or InfSys's BPIC 2013 CL)")
    p.add_argument("--chl", help="choreography log (Pena et al.'s ChL)")
    p.add_argument("--hobeck-xes", help="Hobeck et al.'s XES input")
    p.add_argument("--eth", help="Ethereum transaction traces (JSON)")
    p.add_argument("--key", default=sources.MSG_KEY,
                   help="message identifier attribute (msgId for BPIC 2013)")
    p.add_argument("out", help="output base path")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING,
                        format="%(levelname)s %(message)s")
    logger.setLevel(logging.INFO)
    if not args.verbose:
        logging.getLogger("map_log").addHandler(logging.StreamHandler())
        logging.getLogger("map_log").propagate = False
    res = u.map_log(read_source(args))
    report = write_outputs(res, args.out)
    return 0 if report["structural_criteria_hold"] else 1


if __name__ == "__main__":
    sys.exit(main())
