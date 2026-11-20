"""Lookups over the four OCEL tables of the unified representation.

They work on any log in the representation, not only on the output of
`unified.map_log`, so the criteria (`criteria.py`) and the export to the
representation of Hobeck et al. (`export_hobeck.py`) read the log, not the
mapping. Events and objects are classified by their relations:

- local events: events with `in_collaboration` (M6);
- exchange events: all other events;
- sends / receives: events with `send` / `receive` to a logical `Message` (UM10);
- tasks: events with `request` (UM11).

The endpoints of a logical message are its stored `source` / `target`
relations (UM9), and the roles of a task its stored `initiator` /
`participant` relations (UM11). Neither is derived from the other; the
criteria U4 and U8 compare them.
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

    # ---- logical messages and task roles ---------------------------------
    def messages(self) -> List[str]:
        return self.of_type(u.OT_MESSAGE)

    def message_events(self, m: str) -> Tuple[List[str], List[str]]:
        """The send and receive events of a logical message (UM10)."""
        return sorted(self.events_of(m, cx.Q_SEND)), sorted(self.events_of(m, cx.Q_RECEIVE))

    def endpoints(self, m: str) -> Tuple[List[str], List[str]]:
        """The stored senders and receivers (participant oids) of a logical
        message (UM9)."""
        return self.o2o_targets(m, u.Q_SOURCE), self.o2o_targets(m, u.Q_TARGET)

    def roles(self, t: str) -> Tuple[List[str], List[str]]:
        """The stored initiators and participants of a task (UM11)."""
        return self.targets(t, u.Q_INITIATOR), self.targets(t, u.Q_PARTICIPANT)

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
