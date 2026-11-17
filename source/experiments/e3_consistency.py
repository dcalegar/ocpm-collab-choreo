#!/usr/bin/env python3
"""E3: consistency of the unified output, per profile.

Part A, the criteria of the representation, on every output of `map_all.py`:
the structural criteria (P1.1-P1.7, U1-U3, U5, U7) must hold, and the
diagnostic ones (U4, U6) describe the source data. They are read from the
`_checks.json` files that the mapping writes.

Part B, C0-C16 of Hobeck et al., with their validator (`ocelchorvalidator`,
unmodified), on:
- the export eta_H of every output (`_hobeck.json`), including the complete,
  non-deduplicated logs, on which Hobeck et al. report no results;
- the reference OCEL of Hobeck et al. for each pair of E2, as a cross-check:
  equivalent logs must give the same violation counts.

C15 and C16 are diagnostics of parallel behavior and timestamp ties, as in
Hobeck et al.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from common import (DATA, HOBECK_XES_LOGS, eth_pairs, md_table, ocelchor_module, require,
                    write_results)

C_IDS = [f"C{i}" for i in range(17)]


def profile_name(p: Dict[str, bool]) -> str:
    local = p["internal_tasks"] or p["message_events"]
    if local and p["exchange_events"]:
        return "complete"
    if local:
        return "collaboration"
    return "hierarchical choreography" if p["hierarchy"] else "choreography"


def validator():
    ocelchor_module("ocelchorvalidator", "constraints", "index", "reader")
    from ocelchorvalidator.constraints import validate_all
    from ocelchorvalidator.index import build_index
    from ocelchorvalidator.reader import read_ocel

    def run(path: Path) -> Dict[str, List[int]]:
        res = validate_all(build_index(read_ocel(require(path))))
        return {c: [res[c].num_violations, res[c].elements_checked] for c in C_IDS if c in res}
    return run


def main() -> int:
    summary = json.load(open(require(DATA / "mapped_summary.json")))
    run = validator()
    part_a, part_b, rows_a, rows_b = {}, {}, [], []
    for name, s in summary.items():
        checks = json.load(open(DATA / s["dataset"] / "mapped" / f"{name}_checks.json"))
        crit = {c["name"].split(" ")[0]: c for c in checks["criteria"]}
        prof = profile_name(s["profile"])
        structural_ok = all(c["ok"] for c in checks["criteria"])
        u4, u6 = crit["U4"]["counts"], crit["U6"]["counts"]
        part_a[name] = {"dataset": s["dataset"], "profile": prof, "structural_ok": structural_ok,
                        "U4": u4, "U6": u6, "tasks": s["tasks"],
                        "logical_messages": s["logical_messages"]}
        rows_a.append([name, prof, "yes" if structural_ok else "**no**", s["tasks"],
                       s["logical_messages"], u6["correct"], u6["correct_multicast"],
                       u6["absent"], u6["incoherent"], u6["no_message_events"],
                       u4["several_senders"] + u4["recorded_receiver_not_among_receives"]
                       + u4["exchange_event_endpoints_disagree"]])
        c = run(DATA / s["dataset"] / "mapped" / f"{name}_hobeck.json")
        part_b[name] = {"profile": prof, "constraints": c}
        rows_b.append([name, prof] + [f"{c[k][0]}/{c[k][1]}" if k in c else "—" for k in C_IDS])

    # cross-check on the references of E2
    refs = [(f"{n}_hobeck", DATA / n / "hobeck" / f"{n}_uniqueInteraction_ocel.json")
            for n in HOBECK_XES_LOGS]
    refs += [(stem, ref) for _, stem, _, ref in eth_pairs()]
    cross, rows_c = {}, []
    for name, ref in refs:
        c_ref = run(ref)
        c_ours = part_b[name]["constraints"]
        same = all(c_ref.get(k, [0, 0])[0] == c_ours.get(k, [0, 0])[0] for k in C_IDS)
        cross[name] = {"reference": c_ref, "same_violation_counts": same}
        rows_c.append([name, "yes" if same else "**no**"] +
                      [f"{c_ref[k][0]}/{c_ref[k][1]}" if k in c_ref else "—" for k in C_IDS])

    md = ("# E3: consistency per profile\n\n## A. Criteria of the representation\n\n"
          "U6 columns count logical messages; U4 counts logical messages with any endpoint "
          "disagreement.\n\n"
          + md_table(["Output", "Profile", "Structural ok", "Tasks", "Logical msgs",
                      "U6 correct", "of which multicast", "U6 absent", "U6 incoherent",
                      "U6 no message events", "U4 findings"], rows_a)
          + "\n\n## B. C0–C16 (ocelchorvalidator) on the export eta_H (violations/checked)\n\n"
          + md_table(["Output", "Profile"] + C_IDS, rows_b)
          + "\n\n## C. Cross-check: C0–C16 on Hobeck et al.'s reference OCEL\n\n"
          "Same: the reference has the same violation counts as the export of the "
          "equivalent unified output (part B).\n\n"
          + md_table(["Reference of", "Same"] + C_IDS, rows_c) + "\n")
    write_results("e3_consistency", {"criteria": part_a, "constraints": part_b,
                                     "cross_check": cross}, md)
    ok = all(v["structural_ok"] for v in part_a.values()) and \
        all(v["same_violation_counts"] for v in cross.values())
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
