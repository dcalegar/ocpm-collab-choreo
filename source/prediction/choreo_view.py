"""Choreography view of a log in the unified representation, as the neutral model of InfSys.

The prediction tasks of InfSys (`tasks` of `ocpm-collab-ppm`, imported unchanged) read a
neutral model: one `Execution` per case, one `Event` per position of the prefix. This
module builds that model from the choreography view of a log in the unified
representation, so that the InfSys label functions compute the restated tasks of the
paper (Section 4, Table `tab:tasks-collab`) without modification:

- one `Execution` per `ChoreographyCase`, with the case object id as `case_id`;
- one `Event` per choreography task (an event with a `request` relation), with the
  event id of the OCEL log, so that labels join the OCPA feature table by event id;
- every event is a send (`is_send=True`): in a one-way choreography each task is one
  message, so InfSys's message counts and message activities become task counts and
  task activities;
- the sender and receivers of a task are those of its request message, derived as in
  the representation (`mapping/index.py`, `Index.endpoints`): from the `Message`
  objects of its message events when it has any, and from its own `from` / `to`
  otherwise.

The redefinition of each task lives in the `actor` of the events, which is the only
field the participant-related label functions read:

- `sender_view`: `actor` = sender, so NE-NPaA predicts the next sender;
- `involvement_view(p)`: `actor` = p when p is the sender or a receiver of the task,
  and the sender otherwise. Then `actor == p` holds exactly when the task involves p,
  so the InfSys functions of NE-NMPa, NV-NMPa, NV-PaT, and OB-P compute "involving
  the participant". This view is only valid for the parameter p it was built with.

The log is read with the standard library only (`experiments/common.read_sqlite`), so
this module does not depend on the pm4py version of the mapping or of OCPA. Only the
request message is read: the response message of a two-way task does not change who
takes part in it.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments"))
from common import read_sqlite  # noqa: E402

from tasks.model import Event, Execution, ObjectCentricLog  # noqa: E402  (InfSys)

# Vocabulary of the unified representation (mapping/unified.py, M6-M12). Repeated
# here instead of imported, because importing the mapping pulls in its pm4py version.
OT_CHC = "ChoreographyCase"
OT_CM = "ChoreographyMessage"
Q_IN_CHOREOGRAPHY = "in_choreography"
Q_REQUEST = "request"
Q_SENT_AS = "sent_as"
Q_RECEIVED_AS = "received_as"
Q_FROM = "from"
Q_TO = "to"


@dataclass(frozen=True)
class ChoreographyTask:
    event_id: str
    case_id: str                 # ChoreographyCase object id
    activity: str
    timestamp: datetime
    message: str                 # request ChoreographyMessage object id
    sender: Optional[str]        # participant name; None if the log records none
    receivers: Tuple[str, ...]   # participant names; empty if the log records none

    def involves(self, participant: str) -> bool:
        return participant == self.sender or participant in self.receivers


@dataclass
class ChoreographyView:
    """The choreography tasks of a log, grouped by ChoreographyCase."""
    cases: Dict[str, List[ChoreographyTask]]

    @property
    def tasks(self) -> List[ChoreographyTask]:
        return [t for ts in self.cases.values() for t in ts]

    def participants(self) -> List[str]:
        names = {t.sender for t in self.tasks if t.sender}
        names.update(r for t in self.tasks for r in t.receivers)
        return sorted(names)


def _parse_time(value: str) -> datetime:
    return pd.Timestamp(value).to_pydatetime()


def _order_key(event_id: str) -> Tuple[int, str]:
    """Source order within a case: the mapping writes ids as `<prefix>::<case>::<i>`."""
    _, _, idx = event_id.rpartition("::")
    return (int(idx), event_id) if idx.isdigit() else (sys.maxsize, event_id)


def read_choreography(path: Path | str) -> ChoreographyView:
    """Read the choreography tasks of an OCEL 2.0 SQLite log in the unified representation."""
    log = read_sqlite(Path(path))
    events, objects = log["events"], log["objects"]
    e2o: Dict[str, Dict[str, List[str]]] = defaultdict(lambda: defaultdict(list))
    for eid, oid, q in log["e2o"]:
        e2o[eid][q].append(oid)
    o2o: Dict[str, Dict[str, List[str]]] = defaultdict(lambda: defaultdict(list))
    for src, tgt, q in log["o2o"]:
        o2o[src][q].append(tgt)

    def name(oid: str) -> str:
        return str(objects.get(oid, {}).get("attrs", {}).get("name", oid))

    def endpoints(cm: str) -> Tuple[List[str], List[str]]:
        carriers = sorted(o2o[cm][Q_SENT_AS] + o2o[cm][Q_RECEIVED_AS])
        sources = carriers if carriers else [cm]
        senders = sorted({p for m in sources for p in o2o[m][Q_FROM]})
        receivers = sorted({p for m in sources for p in o2o[m][Q_TO]})
        return [name(p) for p in senders], [name(p) for p in receivers]

    cases: Dict[str, List[ChoreographyTask]] = defaultdict(list)
    for eid in sorted(events, key=_order_key):
        requests = sorted(e2o[eid][Q_REQUEST])
        if not requests:
            continue
        chcs = e2o[eid][Q_IN_CHOREOGRAPHY]
        if len(chcs) != 1 or len(requests) != 1:
            raise ValueError(f"task {eid}: expected one {Q_IN_CHOREOGRAPHY} and one "
                             f"{Q_REQUEST} relation, found {len(chcs)} and {len(requests)}")
        senders, receivers = endpoints(requests[0])
        if len(senders) > 1:
            raise ValueError(f"task {eid}: request message with {len(senders)} senders")
        ev = events[eid]
        cases[chcs[0]].append(ChoreographyTask(
            event_id=eid, case_id=chcs[0], activity=ev["type"],
            timestamp=_parse_time(ev["time"]), message=requests[0],
            sender=senders[0] if senders else None, receivers=tuple(receivers)))
    return ChoreographyView(dict(cases))


def _neutral(view: ChoreographyView, actor_of) -> ObjectCentricLog:
    executions = []
    for case_id, tasks in view.cases.items():
        evs = [Event(event_id=t.event_id, activity=t.activity, timestamp=t.timestamp,
                     actor=actor_of(t) or "", is_send=True, msg_id=t.message,
                     msg_type=t.activity, msg_from=t.sender,
                     msg_to=t.receivers[0] if len(t.receivers) == 1 else None)
               for t in tasks]
        executions.append(Execution(case_id=case_id, events=evs))  # stable sort on time
    return ObjectCentricLog(executions)


def sender_view(view: ChoreographyView) -> ObjectCentricLog:
    """Neutral model with the sender of each task as its actor."""
    return _neutral(view, lambda t: t.sender)


def involvement_view(view: ChoreographyView, participant: str) -> ObjectCentricLog:
    """Neutral model in which the actor is `participant` exactly on the tasks that involve it."""
    return _neutral(view, lambda t: participant if t.involves(participant) else t.sender)
