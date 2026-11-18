"""The InfSys tasks restated over the choreography view (paper, Table `tab:tasks-collab`).

Each restated task is an InfSys task (`tasks.catalog.TASKS`) whose label function
(`tasks.labels`) runs unchanged on one of the two neutral views of `choreo_view`:

- direct: the definition applies unchanged (sender view);
- redefined: the view supplies the choreography counterpart of what the definition
  refers to: the sender for "acting" in NE-NPaA, involvement for the participant tasks,
  tasks for messages, and the last task for the end of the case.

Collapsed and lost tasks are listed for completeness and are never computed: a
collapsed task has, at every prefix, the target of the task it collapses into, and a
lost task needs the receive event, which the choreography view does not record.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from tasks.catalog import TASKS  # InfSys
from tasks.labels import build_context, compute_label_rows  # InfSys

import choreo_view as cv

DIRECT = "direct"
REDEFINED = "redefined"
COLLAPSED = "collapsed"
LOST = "lost"

SENDER = "sender"
INVOLVEMENT = "involvement"


@dataclass(frozen=True)
class RestatedTask:
    key: str        # InfSys task key
    kind: str       # DIRECT or REDEFINED
    view: str       # SENDER or INVOLVEMENT


RESTATED: Dict[str, RestatedTask] = {t.key: t for t in [
    RestatedTask("NE-NEPr", DIRECT, SENDER),
    RestatedTask("NV-TNE", DIRECT, SENDER),
    RestatedTask("OB-M", DIRECT, SENDER),
    RestatedTask("NE-NPaA", REDEFINED, SENDER),
    RestatedTask("NE-NMPa", REDEFINED, INVOLVEMENT),
    RestatedTask("NV-NMPr", REDEFINED, SENDER),
    RestatedTask("NV-NMPa", REDEFINED, INVOLVEMENT),
    RestatedTask("NV-PrT", REDEFINED, SENDER),
    RestatedTask("NV-PaT", REDEFINED, INVOLVEMENT),
    RestatedTask("OB-P", REDEFINED, INVOLVEMENT),
]}

# (InfSys key, direction or None) -> task it collapses into.
COLLAPSED_INTO: Dict[Tuple[str, Optional[str]], str] = {
    ("NE-NEPa", None): "NE-NEPr",     # if every activity has a single sender
    ("NE-NMPr", None): "NE-NEPr",     # if messages are identified by the send activity
    ("NE-NPaM", "send"): "NE-NPaA",
    ("NV-TNM", "send"): "NV-TNE",
}
LOST_TASKS: List[Tuple[str, str]] = [("NE-NPaM", "receive"), ("NV-TNM", "receive")]


def neutral_log(view: cv.ChoreographyView, key: str, participant: Optional[str] = None):
    """The neutral InfSys model on which the restated task `key` is computed."""
    task = RESTATED[key]
    if task.view == INVOLVEMENT:
        if participant is None:
            raise ValueError(f"{key} needs a participant")
        return cv.involvement_view(view, participant)
    return cv.sender_view(view)


def label_rows(view: cv.ChoreographyView, key: str, param=None,
               drop_bottom: bool = True) -> List[Tuple[str, str, int, object]]:
    """Rows (case_id, event_id, k, y) of the restated task `key`, computed by the InfSys
    label function. `param` is the participant (involvement tasks) or the activity (OB-M)."""
    task = RESTATED[key]
    log = neutral_log(view, key, param if task.view == INVOLVEMENT else None)
    return compute_label_rows(log, TASKS[key], param=param, ctx=build_context(log),
                              drop_bottom=drop_bottom)
