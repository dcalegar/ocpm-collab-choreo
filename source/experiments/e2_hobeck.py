#!/usr/bin/env python3
"""E2: the unified mapping reproduces Hobeck et al.

From the same input as Hobeck et al.'s extractors, the export eta_H of the
unified output must be equivalent to their OCEL:

- the 7 collaborative logs: input `hobeck/collectivelog_<n>_uniqueInteraction.xes`,
  reference `hobeck/<n>_uniqueInteraction_ocel.json` (`xescol2ocelchor`);
- the 13 Ethereum files: input `hobeck/<stem>.json`, reference
  `hobeck/<stem>_ocel.json` (`trace2ocelchor`).

Equivalence is checked on the choreography information of Def. 2: tasks (case,
type, time), their initiator and participants, their messages (type, source,
target, content) and which tasks share a message, choreography instances, and
the scope tree. It holds up to what Def. 2 leaves free, normalized explicitly
and counted:

- N1 identifiers of events and objects: instances are identified by their
  case, participants by name (their `name` attribute, else their id), scopes
  by their name and their tasks, messages by content and by the tasks that
  share them;
- N2 participant object types: only a consistent renaming is required (a
  bijection between both sets of types);
- N3 absent content values: `trace2ocelchor` writes a missing call output as
  `output = "None"`; the unified representation leaves it absent;
- N4 event attributes: compared separately, on the attribute names both logs
  have. Attribute names present in only one log are listed (M8 keeps all
  source attributes, plus `elemType`, `participant`, and the backfilled own
  endpoint; `xescol2ocelchor` adds `concept:name`, drops `msgType`, and
  renames `msgFlow` to `msgName`). Values are compared on common names.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

from common import DATA, HOBECK_XES_LOGS, eth_pairs, md_table, require, write_results


def _attrs(item: Dict[str, Any]) -> Dict[str, str]:
    return {a["name"]: a["value"] for a in item.get("attributes", [])}


def canonical(source: "Path | Dict[str, Any]") -> Dict[str, Any]:
    """The choreography information of a log (a path to OCEL 2.0 JSON, or the
    already loaded dict), with the normalizations N1-N3."""
    d = source if isinstance(source, dict) else json.load(open(require(source), encoding="utf-8"))
    obj = {o["id"]: o for o in d["objects"]}
    rel = lambda item: [(r["objectId"], r["qualifier"]) for r in item.get("relationships", [])]

    def pname(i: str) -> str:
        return _attrs(obj[i]).get("name", i)

    def case(i: str) -> str:
        for prefix in ("chc::", "choreographyInstance:"):
            if i.startswith(prefix):
                return i[len(prefix):]
        return i

    n_none = 0

    def content(o):
        nonlocal n_none
        out = []
        for k, v in sorted(_attrs(o).items()):
            if v == "None":
                n_none += 1
                continue
            out.append((k, v))
        return tuple(out)

    def message(m: str):
        o = obj[m]
        src = tuple(sorted(pname(p) for p, q in rel(o) if q == "choreo:source"))
        tgt = tuple(sorted(pname(p) for p, q in rel(o) if q == "choreo:target"))
        return (o["type"], src, tgt, content(o))

    # task keys: (case, type, time, occurrence)
    seen = Counter()
    tasks, msg_of_task, scope_of_task = {}, defaultdict(list), {}
    for e in d["events"]:
        R = rel(e)
        inst = [o for o, q in R if q == "choreo:instance"]
        c = case(inst[0]) if inst else None
        k0 = (c, e["type"], e["time"])
        seen[k0] += 1
        key = k0 + (seen[k0],)
        msgs = [o for o, q in R if q == "choreo:message"]
        for m in msgs:
            msg_of_task[m].append(key)
        sc = [o for o, q in R if q == "choreo:contained-by"]
        scope_of_task[key] = sc
        tasks[key] = {
            "core": (tuple(sorted(pname(p) for p, q in R if q == "choreo:initiator")),
                     tuple(sorted(pname(p) for p, q in R if q == "choreo:participant")),
                     tuple(sorted(message(m) for m in msgs))),
            "attrs": _attrs(e),
        }
    # scopes: identified by (name, sorted keys of their direct tasks)
    tasks_of_scope = defaultdict(list)
    for key, sc in scope_of_task.items():
        for s in sc:
            tasks_of_scope[s].append(key)
    sid = {s: (_attrs(obj[s]).get("name"), tuple(sorted(tasks_of_scope[s])))
           for s, o in obj.items() if o["type"] == "subchoreographyInstance"}
    scope_tree = {(sid[s], sid[c]) for s in sid for c, q in rel(obj[s]) if q == "choreo:contains"}
    for key, sc in scope_of_task.items():
        tasks[key]["core"] += (tuple(sorted(sid[s] for s in sc)),)
    participants = {pname(i): o["type"] for i, o in obj.items()
                    if any(i == p for e in d["events"] for p, q in rel(e)
                           if q in ("choreo:initiator", "choreo:participant"))}
    return {
        "tasks": tasks,
        "sharing": {tuple(sorted(v)) for v in msg_of_task.values()},
        "instances": {case(i) for i, o in obj.items() if o["type"] == "choreographyInstance"},
        "scopes": set(sid.values()),
        "scope_tree": scope_tree,
        "participants": participants,
        "n_none_values": n_none,
    }


def compare(ours, ref) -> Dict[str, Any]:
    a, b = canonical(ours), canonical(ref)
    common = set(a["tasks"]) & set(b["tasks"])
    core_diff = [k for k in common if a["tasks"][k]["core"] != b["tasks"][k]["core"]]
    only_a = sorted(set(a["tasks"]) - set(b["tasks"]))
    only_b = sorted(set(b["tasks"]) - set(a["tasks"]))
    names_a = set().union(*(set(t["attrs"]) for t in a["tasks"].values())) if a["tasks"] else set()
    names_b = set().union(*(set(t["attrs"]) for t in b["tasks"].values())) if b["tasks"] else set()
    attr_diff = sum(1 for k in common for n in set(a["tasks"][k]["attrs"]) & set(b["tasks"][k]["attrs"])
                    if a["tasks"][k]["attrs"][n] != b["tasks"][k]["attrs"][n])
    pa, pb = a["participants"], b["participants"]
    renaming = {(pa[p], pb[p]) for p in set(pa) & set(pb)}
    bijective = (len({x for x, _ in renaming}) == len(renaming) == len({y for _, y in renaming}))
    r = {
        "tasks": [len(a["tasks"]), len(b["tasks"])],
        "tasks_unmatched": [len(only_a), len(only_b)],
        "tasks_differing": len(core_diff),
        "message_sharing_equal": a["sharing"] == b["sharing"],
        "instances_equal": a["instances"] == b["instances"],
        "instances": [len(a["instances"]), len(b["instances"])],
        "scopes": [len(a["scopes"]), len(b["scopes"])],
        "scopes_equal": a["scopes"] == b["scopes"] and a["scope_tree"] == b["scope_tree"],
        "participants_equal": set(pa) == set(pb),
        "participant_types_identical": all(x == y for x, y in renaming),
        "participant_types_consistently_renamed": bijective,
        "N3_none_values_dropped": b["n_none_values"] - a["n_none_values"],
        "N4_attributes_only_ours": sorted(names_a - names_b),
        "N4_attributes_only_reference": sorted(names_b - names_a),
        "N4_common_attribute_values_differing": attr_diff,
        "examples": [str(x) for x in (only_a[:2] + only_b[:2] + core_diff[:2])],
    }
    r["equivalent"] = (not only_a and not only_b and not core_diff and r["message_sharing_equal"]
                       and r["instances_equal"] and r["scopes_equal"] and r["participants_equal"]
                       and bijective)
    return r


def main() -> int:
    pairs = [(n, f"{n}_hobeck", DATA / n / "mapped" / f"{n}_hobeck_hobeck.json",
              DATA / n / "hobeck" / f"{n}_uniqueInteraction_ocel.json") for n in HOBECK_XES_LOGS]
    pairs += eth_pairs()
    results, rows = {}, []
    for dataset, name, ours, ref in pairs:
        r = compare(ours, ref)
        results[name] = {"dataset": dataset, **r}
        rows.append([dataset, "yes" if r["equivalent"] else "**no**",
                     "{}/{}".format(*r["tasks"]), r["tasks_differing"],
                     "{}/{}".format(*r["instances"]), "{}/{}".format(*r["scopes"]),
                     "yes" if r["message_sharing_equal"] else "no",
                     "identical" if r["participant_types_identical"] else
                     ("renamed" if r["participant_types_consistently_renamed"] else "**no**"),
                     r["N3_none_values_dropped"],
                     ", ".join(r["N4_attributes_only_ours"]) or "—",
                     ", ".join(r["N4_attributes_only_reference"]) or "—",
                     r["N4_common_attribute_values_differing"]])
    md = ("# E2: reproduction of Hobeck et al. (eta_H(mu_U(L)) vs. their OCEL)\n\n"
          + md_table(["Dataset", "Equivalent", "Tasks (ours/ref)", "Tasks differing",
                      "Instances", "Scopes", "Message sharing", "Participant types (N2)",
                      "None values (N3)", "Attributes only ours (N4)",
                      "Attributes only ref (N4)", "Common attr. values differing"], rows)
          + "\n\nN1 (identifiers) applies to every row. See the docstring of `e2_hobeck.py`.\n")
    write_results("e2_hobeck", results, md)
    return 0 if all(r["equivalent"] for r in results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
