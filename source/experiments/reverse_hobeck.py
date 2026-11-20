"""Reverse adapter iota_H: a log in the representation of Hobeck et al.
(`HobeckMMW27`, Def. 2) as a source of the unified mapping.

iota_H reads an OCEL 2.0 JSON log of Hobeck et al. and returns a `SourceLog` of
the choreography profile, which mu_U then maps: each choreography task becomes
an exchange event, and each message object becomes one logical message (its
object id is the message identifier, so tasks that share a message object
share the logical message). No message event is created, and no send or
receive timestamp is invented.

| Hobeck et al. | Exchange event |
|---|---|
| event with `choreo:instance` (a task) | one exchange event; case = the instance; activity, time, attributes unchanged |
| `choreo:initiator`, `choreo:participant` | `initiators`, `participants` (stored roles) |
| request message: the `choreo:message` whose `choreo:source` includes the initiator | `key`, `name` (message type), `content` (message attributes), `sender` (source), `receivers` (targets) |
| the other `choreo:message`, if any | the response: `response_key`, `response_name`, `response_content`, `response_senders` (source), `response_receivers` (targets) |
| `choreo:contained-by` and the `choreo:contains` chain | `scope_path`, outermost first, with the scope `name` |
| participant object type | participant role (exported back as its type by eta_H) |

Task roles and message endpoints are both kept as recorded, also when they
disagree (C1, C9, C10 of Hobeck et al.); the unified representation stores both
and U8 reports the disagreement. iota_H counts in `diagnostics` only what it
cannot represent or must choose:
- a task with no message, with more than two, or with two messages of which
  not exactly one starts at the initiator (ambiguous request, C7/C8);
- a request with several sources (C5), of which only the first is the sender;
- a scope with several parents, or a task in several scopes;
- events without `choreo:instance` and message objects used by no task, which
  are not choreography tasks and are ignored.

This adapter belongs to the experiments: the mapping itself reads the original
formats (`../mapping/sources.py`).
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd

from common import MAPPING  # noqa: F401  (puts ../mapping on sys.path)
from sources import ExchangeEvent, Scope, SourceLog

INSTANCE_PREFIX = "choreographyInstance:"


def _attrs(item: Dict[str, Any]) -> Dict[str, str]:
    return {a["name"]: a["value"] for a in item.get("attributes", [])}


def _rels(item: Dict[str, Any], q: str) -> List[str]:
    return [r["objectId"] for r in item.get("relationships", []) if r["qualifier"] == q]


def read_hobeck_ocel(path: str | Path) -> Tuple[SourceLog, Dict[str, int]]:
    d = json.load(open(path, encoding="utf-8"))
    obj = {o["id"]: o for o in d["objects"]}
    diag: Counter = Counter()

    def pname(i: str) -> str:
        return _attrs(obj[i]).get("name", i) if i in obj else i

    parent: Dict[str, str] = {}
    for o in d["objects"]:
        for c in _rels(o, "choreo:contains"):
            if c in parent:
                diag["scopes_with_several_parents"] += 1
            parent.setdefault(c, o["id"])

    def scope_path(s: str) -> Tuple[Scope, ...]:
        chain, seen = [], set()
        while s is not None and s not in seen:
            seen.add(s)
            chain.append(Scope(s, _attrs(obj.get(s, {})).get("name")))
            s = parent.get(s)
        return tuple(reversed(chain))

    roles: Dict[str, str] = {}
    used_messages = set()
    events: List[ExchangeEvent] = []
    for order, e in enumerate(d["events"]):
        inst = _rels(e, "choreo:instance")
        if not inst:
            diag["events_without_instance_ignored"] += 1
            continue
        case = inst[0][len(INSTANCE_PREFIX):] if inst[0].startswith(INSTANCE_PREFIX) else inst[0]
        initiators = _rels(e, "choreo:initiator")
        participants = _rels(e, "choreo:participant")
        for p in initiators + participants:
            if p in obj:
                roles.setdefault(pname(p), obj[p]["type"])
        msgs = _rels(e, "choreo:message")
        used_messages.update(msgs)
        if not msgs:
            diag["tasks_without_message"] += 1
            continue
        if len(msgs) > 2:
            diag["tasks_with_more_than_two_messages"] += 1
        starts = [m for m in msgs if set(_rels(obj[m], "choreo:source")) & set(initiators)]
        if len(msgs) == 1:
            req, resp = msgs[0], None
        elif len(starts) == 1:
            req = starts[0]
            resp = next(m for m in msgs if m != req)
        else:
            diag["tasks_with_ambiguous_request"] += 1
            req, resp = msgs[0], msgs[1]
        src, tgt = _rels(obj[req], "choreo:source"), _rels(obj[req], "choreo:target")
        if len(src) > 1:
            diag["requests_with_several_sources"] += 1
        x = ExchangeEvent(
            case=case, activity=e["type"], timestamp=pd.Timestamp(e["time"]),
            order=order, sender=pname(src[0]) if src else None,
            receivers=tuple(pname(p) for p in tgt), key=req, name=obj[req]["type"],
            content=_attrs(obj[req]), attributes=_attrs(e),
            initiators=tuple(pname(p) for p in initiators),
            participants=tuple(pname(p) for p in participants))
        for p in src + tgt:
            if p in obj:
                roles.setdefault(pname(p), obj[p]["type"])
        if resp is not None:
            rs, rt = _rels(obj[resp], "choreo:source"), _rels(obj[resp], "choreo:target")
            x.response_key, x.response_name = resp, obj[resp]["type"]
            x.response_content = _attrs(obj[resp])
            x.response_senders = tuple(pname(p) for p in rs)
            x.response_receivers = tuple(pname(p) for p in rt)
            for p in rs + rt:
                if p in obj:
                    roles.setdefault(pname(p), obj[p]["type"])
        sc = _rels(e, "choreo:contained-by")
        if len(sc) > 1:
            diag["tasks_in_several_scopes"] += 1
        if sc:
            x.scope_path = scope_path(sc[0])
        events.append(x)
    instances_or_scopes = {"choreographyInstance", "subchoreographyInstance"}
    message_like = {i for i, o in obj.items() if o["type"] not in instances_or_scopes
                    and (_rels(o, "choreo:source") or _rels(o, "choreo:target"))}
    diag["message_objects_without_task_ignored"] = len(message_like - used_messages)
    src = SourceLog(name=Path(path).stem, inputs=[str(path)], exchange=events,
                    participant_roles=roles)
    return src, {k: v for k, v in sorted(diag.items())}
