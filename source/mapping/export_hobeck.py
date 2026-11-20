"""Export adapter eta_H: the choreography view in the representation of Hobeck et
al. (`HobeckMMW27`, Def. 2), as OCEL 2.0 JSON readable by `ocelchorvalidator`.

It adds no information and recomputes nothing: it renames types and
qualifiers, and exports task roles and message endpoints as stored, so that a
disagreement between them (U8) survives the export.

| Hobeck et al. | Unified representation | Derivation |
|---|---|---|
| `choreographyInstance`, `choreo:instance` | `ChoreographyCase`, `in_choreography` | renaming; `part_of` is not exported |
| `subchoreographyInstance`, `choreo:contained-by`, `choreo:contains` | `SubChoreographyCase`, `contained_by`, `contains` | renaming |
| `choreo:message` | `request` and `response` | both logical messages |
| `choreo:source`, `choreo:target` | `source`, `target` of the logical message (UM9), including the response endpoints | prefixing |
| `choreo:initiator`, `choreo:participant` | `initiator`, `participant` of the task (UM11) | prefixing |

Only tasks, their instances, scopes, logical messages, and participants are
exported. Object types that Def. 2 leaves free are chosen as follows: a message
object takes its message name as type (`message` without one), and a
participant takes its recorded role if any (Ethereum), else its M2 type. The
bookkeeping attributes of the new objects (`caseId`, `msgInstanceId`,
`msgName`, `scopeId`, `role`) become types or identifiers and are not copied.
Event attributes are copied unchanged.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from infsys import cx
from index import Index
import unified as u

INSTANCE, SUBINSTANCE = "choreographyInstance", "subchoreographyInstance"
EPOCH = "1970-01-01T00:00:00Z"


def iso(ts: Any, micro: bool) -> str:
    t = pd.Timestamp(ts).tz_convert("UTC")
    s = t.strftime("%Y-%m-%dT%H:%M:%S.%f")
    return (s if micro else s[:-3]) + "Z"


def needs_microseconds(timestamps) -> bool:
    return any(pd.Timestamp(t).microsecond % 1000 for t in timestamps)


def _value(v: Any) -> str:
    return str(v)


def export(ix: Index) -> Dict[str, Any]:
    tasks = ix.tasks()
    micro = needs_microseconds(ix.events[t][cx.COL_TIMESTAMP] for t in tasks)
    objects: Dict[str, Dict[str, Any]] = {}

    def participant(p: str) -> str:
        if p not in objects:
            r = ix.objects[p]
            objects[p] = {"id": p, "type": r.get(u.A_ROLE) or r[cx.COL_OTYPE],
                          "attributes": [{"name": "name", "value": ix.participant_name(p),
                                          "time": EPOCH}]}
        return p

    def message(cm: str) -> str:
        if cm not in objects:
            r = ix.objects[cm]
            senders, receivers = ix.endpoints(cm)
            rels = ([{"objectId": participant(p), "qualifier": "choreo:source"} for p in senders]
                    + [{"objectId": participant(p), "qualifier": "choreo:target"} for p in receivers])
            attrs = [{"name": k, "value": _value(v), "time": EPOCH} for k, v in r.items()
                     if k not in (cx.COL_OID, cx.COL_OTYPE, *u.BOOKKEEPING)
                     and not (v is None or (isinstance(v, float) and pd.isna(v)))]
            objects[cm] = {"id": cm, "type": r.get(u.A_NAME) or "message",
                           "attributes": attrs, "relationships": rels}
        return cm

    def scope(s: str) -> str:
        if s not in objects:
            r = ix.objects[s]
            obj = {"id": s, "type": SUBINSTANCE, "attributes": [], "relationships": []}
            if isinstance(r.get(u.A_SCOPE_NAME), str):
                obj["attributes"].append({"name": "name", "value": r[u.A_SCOPE_NAME], "time": EPOCH})
            objects[s] = obj
            for child in ix.o2o_targets(s, u.Q_CONTAINS):
                obj["relationships"].append({"objectId": scope(child), "qualifier": "choreo:contains"})
        return s

    events: List[Dict[str, Any]] = []
    for t in tasks:
        ev = ix.events[t]
        rels = []
        for c in ix.targets(t, u.Q_IN_CHOREOGRAPHY):
            objects.setdefault(c, {"id": c, "type": INSTANCE})
            rels.append({"objectId": c, "qualifier": "choreo:instance"})
        req = ix.targets(t, u.Q_REQUEST)
        initiators, participants = ix.roles(t)
        rels += [{"objectId": participant(p), "qualifier": "choreo:initiator"} for p in initiators]
        rels += [{"objectId": participant(p), "qualifier": "choreo:participant"}
                 for p in participants]
        rels += [{"objectId": message(m), "qualifier": "choreo:message"}
                 for m in req + ix.targets(t, u.Q_RESPONSE)]
        rels += [{"objectId": scope(s), "qualifier": "choreo:contained-by"}
                 for s in ix.targets(t, u.Q_CONTAINED_BY)]
        attrs = [{"name": k, "value": _value(v)} for k, v in ev.items()
                 if k not in (cx.COL_EID, cx.COL_ACTIVITY, cx.COL_TIMESTAMP)
                 and not (v is None or (isinstance(v, float) and pd.isna(v)))]
        events.append({"id": t, "type": ev[cx.COL_ACTIVITY],
                       "time": iso(ev[cx.COL_TIMESTAMP], micro),
                       "attributes": attrs, "relationships": rels})

    def declared(items):
        seen: Dict[str, set] = {}
        for it in items:
            seen.setdefault(it["type"], set()).update(a["name"] for a in it.get("attributes", []))
        return [{"name": k, "attributes": [{"name": a, "type": "string"} for a in sorted(v)]}
                for k, v in sorted(seen.items())]

    objs = sorted(objects.values(), key=lambda o: (o["type"], o["id"]))
    return {"objectTypes": declared(objs), "eventTypes": declared(events),
            "objects": objs, "events": events}


def write(ocel: Dict[str, Any], path: str | Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(ocel, f, indent=1, ensure_ascii=False)
