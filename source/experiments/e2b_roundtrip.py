#!/usr/bin/env python3
"""E2b: round trip through the unified representation, eta_H(mu+(iota_H(H))) = H.

E2 shows the export direction: from Hobeck et al.'s inputs, the unified output
exports to their OCEL. E2b shows the reverse direction: every OCEL H of Hobeck
et al. (the 7 outputs of `xescol2ocelchor` and the 13 of `trace2ocelchor`) is
read into the unified representation by the reverse adapter iota_H
(`reverse_hobeck.py`), mapped by mu+, exported by eta_H, and compared with H
using the comparison of E2 (`e2_hobeck.compare`, normalizations N1-N4).

A reference passes only if all of the following hold, so that a regression in
any of them makes the experiment fail:
- the round trip is equivalent to H;
- mu+(iota_H(H)) satisfies the structural criteria of the representation
  (U1-U3, U5, U7), so Hobeck et al.'s logs are instances of it;
- P1.7 holds on the E2O table that the export would hand to pm4py;
- iota_H reports no diagnostic (no disagreeing redundant relations, ambiguous
  request, ignored event or message, ...);
- mu+ reports no conflicting values in a logical message.
The U4/U6 counts are reported, not required: they describe the data.
"""

from __future__ import annotations

from typing import Any, Dict

from common import DATA, HOBECK_XES_LOGS, eth_pairs, md_table, write_results
import criteria
from e2_hobeck import compare
import export_hobeck
from index import index_of
from map_log import export_relations
from reverse_hobeck import read_hobeck_ocel
import unified as u


def evaluate(ref) -> Dict[str, Any]:
    """The round trip of one OCEL of Hobeck et al., with its pass condition."""
    src, diag = read_hobeck_ocel(ref)
    res = u.map_log(src)
    ix = index_of(res)
    crits = criteria.unified_criteria(ix, None)
    structural = all(c.ok for c in crits)
    p17 = criteria.infsys_criteria(res, export_relations(res))[-1]   # no local part: P1.7 only
    conflicts = res.stats["conflicting_values"]
    cmp = compare(export_hobeck.export(ix), ref)
    c = {x.name.split(" ")[0]: x.counts for x in crits}
    checks = {"equivalent": cmp["equivalent"], "structural_criteria_hold": structural,
              "p1_7_holds": p17.ok, "no_iota_H_diagnostics": not any(diag.values()),
              "no_conflicting_values": not conflicts}
    return {"passed": all(checks.values()), **checks, "iota_H_diagnostics": diag,
            "conflicting_values": conflicts, "p1_7": p17.counts.get("detail"),
            "comparison": cmp, "U4": c["U4"], "U6": c["U6"], "profile": res.stats["profile"]}


def main() -> int:
    refs = [(n, DATA / n / "hobeck" / f"{n}_uniqueInteraction_ocel.json") for n in HOBECK_XES_LOGS]
    refs += [(f"{ds} ({stem[:10]})", ref) for ds, stem, _, ref in eth_pairs()]
    results: Dict[str, Any] = {}
    rows = []
    for name, ref in refs:
        r = results[name] = {"reference": str(ref.relative_to(DATA)), **evaluate(ref)}
        cmp, diag, conflicts = r["comparison"], r["iota_H_diagnostics"], r["conflicting_values"]
        structural, p17_ok = r["structural_criteria_hold"], r["p1_7_holds"]
        yn = lambda b: "yes" if b else "**no**"  # noqa: E731
        findings = ", ".join(f"{k}={v}" for k, v in diag.items() if v) or "—"
        rows.append([name, yn(results[name]["passed"]), yn(cmp["equivalent"]),
                     "{}/{}".format(*cmp["tasks"]), cmp["tasks_differing"],
                     "yes" if cmp["message_sharing_equal"] else "no",
                     "{}/{}".format(*cmp["scopes"]),
                     "identical" if cmp["participant_types_identical"] else "renamed",
                     yn(structural), yn(p17_ok), findings, len(conflicts)])
    md = ("# E2b: round trip eta_H(mu+(iota_H(H))) vs. H\n\n"
          "Passed requires equivalence, the structural U criteria, P1.7, no iota_H "
          "diagnostic, and no conflicting values.\n\n"
          + md_table(["Hobeck et al.'s OCEL", "Passed", "Equivalent", "Tasks (round trip/H)",
                      "Tasks differing", "Message sharing", "Scopes", "Participant types",
                      "U structural ok", "P1.7", "iota_H diagnostics", "Conflicting values"],
                     rows) + "\n")
    write_results("e2b_roundtrip", results, md)
    return 0 if all(r["passed"] for r in results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
