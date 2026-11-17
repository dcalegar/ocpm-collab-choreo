"""Lookups over the four OCEL tables of the unified representation.

They work on any log in the representation, not only on the output of
`unified.map_log`, so the criteria (`criteria.py`) and the export to the
representation of Hobeck et al. (`export_hobeck.py`) read the log, not the
mapping. Events and objects are classified by their relations:

- local events: events with `in_collaboration` (M6);
- exchange events: all other events;
- sends / receives: events with `send` / `receive` (M6);
- tasks: events with `request` (M12).

The sender and receiver of a logical message are derived (M11): from the
`from` / `to` endpoints of its `Message` objects when it has message events,
and from its own `from` / `to` relations otherwise.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple

import pandas as pd

from infsys import cx
import unified as u


@dataclass
class Index:
    events: Dict[str, dict]
    objects: Dict[str, dict]
    e2o: Dict[str, List[Tuple[str, str]]]          # eid -> [(oid, qualifier)]
    o2o: Dict[str, List[Tuple[str, str]]]          # oid -> [(oid2, qualifier)]
    o2o_in: Dict[str, List[Tuple[str, str]]]       # oid2 -> [(oid, qualifier)]
    e2o_in: Dict[str, List[Tuple[str, str]]]       # oid -> [(eid, qualifier)]

    def targets(self, eid: str, q: str) -> List[str]:
        return [o for o, qq in self.e2o.get(eid, []) if qq == q]

    def o2o_targets(self, oid: str, q: str) -> List[str]:
        return [o for o, qq in self.o2o.get(oid, []) if qq == q]

    def o2o_sources(self, oid: str, q: str) -> List[str]:
        return [o for o, qq in self.o2o_in.get(oid, []) if qq == q]

    def events_of(self, oid: str, q: str) -> List[str]:
        return [e for e, qq in self.e2o_in.get(oid, []) if qq == q]

    def of_type(self, otype: str) -> List[str]:
        return [o for o, r in self.objects.items() if r[cx.COL_OTYPE] == otype]

    # ---- classification ------------------------------------------------
    def is_local(self, eid: str) -> bool:
        return bool(self.targets(eid, cx.Q_IN_COLLABORATION))

    def tasks(self) -> List[str]:
        return sorted(e for e in self.events if self.targets(e, u.Q_REQUEST))

    def exchange_events(self) -> List[str]:
        return sorted(e for e in self.events if not self.is_local(e))

    # ---- logical messages -----------------------------------------------
    def message_events(self, cm: str) -> Tuple[List[str], List[str]]:
        """The Message objects of the sends and receives of a logical message."""
        return self.o2o_targets(cm, u.Q_SENT_AS), self.o2o_targets(cm, u.Q_RECEIVED_AS)

    def endpoints(self, cm: str) -> Tuple[List[str], List[str]]:
        """Derived senders and receivers (participant oids) of a logical message."""
        sends, receives = self.message_events(cm)
        local = sends + receives
        if local:
            senders = [p for m in local for p in self.o2o_targets(m, cx.Q_FROM)]
            receivers = [p for m in local for p in self.o2o_targets(m, cx.Q_TO)]
        else:
            senders = self.o2o_targets(cm, u.Q_FROM)
            receivers = self.o2o_targets(cm, u.Q_TO)
        return list(dict.fromkeys(senders)), list(dict.fromkeys(receivers))

    def participant_name(self, oid: str) -> str:
        return str(self.objects[oid].get("name", oid))


def build_index(events_df: pd.DataFrame, objects_df: pd.DataFrame,
                relations_df: pd.DataFrame, o2o_df: pd.DataFrame) -> Index:
    def records(df):
        return [] if df is None or df.empty else df.to_dict("records")

    events = {r[cx.COL_EID]: r for r in records(events_df)}
    objects = {r[cx.COL_OID]: r for r in records(objects_df)}
    e2o: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
    e2o_in: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
    for r in records(relations_df):
        e2o[r[cx.COL_EID]].append((r[cx.COL_OID], r[cx.COL_QUALIFIER]))
        e2o_in[r[cx.COL_OID]].append((r[cx.COL_EID], r[cx.COL_QUALIFIER]))
    o2o: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
    o2o_in: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
    for r in records(o2o_df):
        o2o[r[cx.COL_OID]].append((r[cx.COL_OID2], r[cx.COL_QUALIFIER]))
        o2o_in[r[cx.COL_OID2]].append((r[cx.COL_OID], r[cx.COL_QUALIFIER]))
    return Index(events, objects, dict(e2o), dict(o2o), dict(o2o_in), dict(e2o_in))


def index_of(res: "u.UnifiedResult") -> Index:
    return build_index(res.events_df, res.objects_df, res.relations_df, res.o2o_df)
