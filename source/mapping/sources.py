"""Readers of the original log formats.

Each reader turns one original file into a `SourceLog`, the in-memory input of
the unified mapping (`unified.py`). A `SourceLog` is not a file format: it
holds the local events of the log in the source schema of the InfSys mapping
(rules M1-M8) and the exchange events of the log as `ExchangeEvent` records.

The readers only rename and regroup. They never repair: reused identifiers,
missing receivers, and sends without receives reach the mapping as recorded.

| Reader | Original file | Local events | Exchange events |
|---|---|---|---|
| `read_cl` | Pena et al.'s CL (`pena/*_collab.xes`), InfSys's BPIC 2013 CL | yes | no |
| `read_chl` | Pena et al.'s ChL (`pena/*_chor.xes`) | no | yes |
| `read_hobeck_xes` | Hobeck et al.'s XES input (`hobeck/*_uniqueInteraction.xes`) | yes | no |
| `combine` | a CL and its ChL | from the CL | from the ChL |
| `read_eth_traces` | Ethereum traces (`hobeck/<stem>.json`), read with `trace2ocelchor` | no | yes, with return messages and scopes |
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from infsys import cx

# Source keys read besides the InfSys ones (cx.CASE_KEY, cx.ELEMTYPE_KEY, ...).
MSG_KEY = "msgInstanceId"          # message identifier (correlation key)
BPIC_MSG_KEY = "msgId"             # message identifier in InfSys's BPIC 2013 CL
MSG_NAME_KEYS = ("msgName", "msgFlow")
MSG_TYPE_KEY = "msgType"           # send / receive, in the raw logs
ORG_GROUP_KEY = "org:group"        # executing participant, in the raw logs

# Fixed names under which UM7 (M8) keeps the consumed collab:* keys; UM8 uses the same.
RENAMED_COLLAB_KEYS = {
    cx.ELEMTYPE_KEY: "elemType",
    cx.PARTICIPANT_KEY: "participant",
    cx.FROM_KEY: "fromParticipant",
    cx.TO_KEY: "toParticipant",
}


def clean(v: Any) -> Optional[str]:
    """Absent values (None, NaN, empty or blank strings) as None, like
    `_clean` in the InfSys mapping; any other value as a stripped string."""
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    s = str(v).strip()
    return s or None


@dataclass
class Scope:
    """One recorded scope execution (sub-choreography) enclosing a task."""
    scope_id: str                       # source identifier, unique in its case
    name: Optional[str] = None


@dataclass
class ExchangeEvent:
    """An event that records a whole message (a choreography task), with the
    request message and, for a two-way task, the response message.

    ``sender``/``receivers`` are the request endpoints.  The optional role
    and response-endpoint tuples preserve independent source assertions.  A
    value of ``None`` means that the source does not state that assertion, so
    the unified mapping uses the BPMN fallback (request endpoints as task
    roles, and reversed request endpoints as response endpoints).  An empty
    tuple is an explicit empty assertion and is therefore not replaced."""
    case: str
    activity: str
    timestamp: pd.Timestamp
    order: int                          # position in the source file
    sender: Optional[str]               # sender of the request
    receivers: Tuple[str, ...]          # receivers of the request
    key: Optional[str]                  # identifier of the request message
    name: Optional[str] = None          # name of the request message
    content: Dict[str, Any] = field(default_factory=dict)
    response_key: Optional[str] = None
    response_name: Optional[str] = None
    response_content: Dict[str, Any] = field(default_factory=dict)
    initiators: Optional[Tuple[str, ...]] = None
    participants: Optional[Tuple[str, ...]] = None
    response_senders: Optional[Tuple[str, ...]] = None
    response_receivers: Optional[Tuple[str, ...]] = None
    scope_path: Tuple[Scope, ...] = ()  # enclosing scopes, outermost first
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SourceLog:
    """Input of the unified mapping."""
    name: str
    inputs: List[str]
    local: Optional[pd.DataFrame] = None    # InfSys source schema
    exchange: List[ExchangeEvent] = field(default_factory=list)
    key_attr: str = MSG_KEY                 # identifier attribute of local events
    name_attrs: Tuple[str, ...] = MSG_NAME_KEYS
    participant_roles: Dict[str, str] = field(default_factory=dict)


def read_xes(path: str | Path) -> pd.DataFrame:
    """Read an XES file with the InfSys reader (`read_collaborative_xes`).

    The InfSys reader re-parses the raw timestamps with
    `pd.to_datetime(..., errors="coerce")`, which infers one format from the
    first value and sets to NaT any value written with another precision (for
    instance, `...T18:53:51+00:00` among `...T18:53:51.123000+00:00`, as
    pm4py writes Hobeck et al.'s XES). The timestamps are therefore parsed
    again from the raw strings with `format="ISO8601"`. Where the InfSys
    reader parsed a value, both must agree; otherwise the reader raises."""
    df = cx.read_collaborative_xes(str(path))
    raw = pd.Series(cx._raw_timestamps_in_file_order(str(path)))
    iso = pd.to_datetime(raw, utc=True, format="ISO8601")
    ts = df[cx.TIMESTAMP_KEY].reset_index(drop=True)
    parsed = ts.notna()
    if not (ts[parsed] == iso[parsed]).all():
        raise ValueError(f"{path}: timestamps disagree with the InfSys reader")
    df[cx.TIMESTAMP_KEY] = iso.values
    return df


def _message_name(row: Dict[str, Any], name_attrs) -> Optional[str]:
    for k in name_attrs:
        v = clean(row.get(k))
        if v is not None:
            return v
    return None


def read_cl(path: str | Path, key_attr: str = MSG_KEY) -> SourceLog:
    """A collaboration log with the `collab` extension: Pena et al.'s CL, or
    InfSys's BPIC 2013 CL (`key_attr="msgId"`). It is read exactly as the
    InfSys mapping reads it."""
    df = read_xes(path)
    return SourceLog(name=Path(path).stem, inputs=[str(path)], local=df,
                     key_attr=key_attr)


def read_hobeck_xes(path: str | Path) -> SourceLog:
    """Hobeck et al.'s XES input: the raw log of Pena et al., without the
    `collab:*` attributes. The executing participant is `org:group` and the
    kind of event is `msgType` (`send`, `receive`, or absent for an internal
    task), as `xescol2ocelchor` reads them. The reader derives
    `collab:participant` and `collab:elemType` from them; the counterparty of
    a send or receive is not recorded, so `collab:fromParticipant` and
    `collab:toParticipant` stay absent. `org:group` and `msgType` remain
    source attributes (M8)."""
    df = read_xes(path)
    for k in (cx.ELEMTYPE_KEY, cx.PARTICIPANT_KEY, cx.FROM_KEY, cx.TO_KEY):
        if k in df.columns:
            raise ValueError(f"{path}: unexpected attribute {k!r} in Hobeck et al.'s XES")
    kinds = {"send": cx.ELEM_SEND, "receive": cx.ELEM_RECEIVE}
    df[cx.PARTICIPANT_KEY] = df[ORG_GROUP_KEY] if ORG_GROUP_KEY in df.columns else None
    mtype = df[MSG_TYPE_KEY] if MSG_TYPE_KEY in df.columns else pd.Series([None] * len(df))
    unknown = sorted({clean(v) for v in mtype if clean(v) not in (None, *kinds)})
    if unknown:
        raise ValueError(f"{path}: unknown {MSG_TYPE_KEY} values {unknown}")
    df[cx.ELEMTYPE_KEY] = [kinds.get(clean(v), cx.ELEM_TASK) for v in mtype]
    return SourceLog(name=Path(path).stem, inputs=[str(path)], local=df)


def read_chl(path: str | Path, key_attr: str = MSG_KEY) -> SourceLog:
    """Pena et al.'s choreography log: one exchange event per message
    (`collab:elemType = Message`), with its sender and single receiver in
    `collab:fromParticipant` and `collab:toParticipant`."""
    df = read_xes(path)
    bad = sorted({clean(v) for v in df.get(cx.ELEMTYPE_KEY, [])} - {"Message"})
    if bad:
        raise ValueError(f"{path}: events with collab:elemType {bad} in a ChL")
    consumed = (cx.CASE_KEY, cx.ACTIVITY_KEY, cx.TIMESTAMP_KEY)
    events: List[ExchangeEvent] = []
    for order, row in enumerate(df.to_dict("records")):
        attrs = {}
        for k, v in row.items():
            if k in consumed or clean(v) is None:
                continue
            attrs[RENAMED_COLLAB_KEYS.get(k, k)] = v
        receiver = clean(row.get(cx.TO_KEY))
        events.append(ExchangeEvent(
            case=str(row[cx.CASE_KEY]),
            activity=row[cx.ACTIVITY_KEY],
            timestamp=row[cx.TIMESTAMP_KEY],
            order=order,
            sender=clean(row.get(cx.FROM_KEY)),
            receivers=(receiver,) if receiver else (),
            key=clean(row.get(key_attr)),
            name=_message_name(row, MSG_NAME_KEYS),
            attributes=attrs,
        ))
    return SourceLog(name=Path(path).stem, inputs=[str(path)], exchange=events,
                     key_attr=key_attr)


def combine(cl: SourceLog, chl: SourceLog, name: Optional[str] = None) -> SourceLog:
    """The complete profile: the local events of a CL and the exchange events
    of its ChL in one log. Events are not aligned or matched here: the mapping
    links each exchange event to the message events with its identifier."""
    if cl.key_attr != chl.key_attr:
        raise ValueError("The CL and the ChL use different identifier attributes")
    return SourceLog(name=name or f"{cl.name}+{chl.name}",
                     inputs=cl.inputs + chl.inputs, local=cl.local,
                     exchange=chl.exchange, key_attr=cl.key_attr)


# ---------------------------------------------------------------------------
# Ethereum transaction traces (Hobeck et al.)
# ---------------------------------------------------------------------------

def _trace2ocelchor():
    """Import `trace2ocelchor` (ocelchor repository, unmodified) from the clone
    named by the environment variable `OCELCHOR`, or from a sibling clone
    `../ocelchor`. No byte code is written into the clone."""
    import os
    import sys
    try:
        import trace2ocelchor  # noqa: F401
    except ImportError:
        repo = Path(__file__).resolve().parents[2]
        clones = ([Path(os.environ["OCELCHOR"])] if os.environ.get("OCELCHOR") else [])
        clones.append(repo.parent / "ocelchor")
        for clone in clones:
            src = clone / "trace2ocelchor" / "src"
            if (src / "trace2ocelchor" / "parser.py").is_file():
                sys.path.insert(0, str(src))
                break
        else:
            raise ImportError("trace2ocelchor not found; set OCELCHOR to the ocelchor clone")
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        from trace2ocelchor import parser, transformer
    finally:
        sys.dont_write_bytecode = previous
    return parser, transformer


def read_eth_traces(path: str | Path) -> SourceLog:
    """Ethereum transaction traces, read and interpreted with the code of
    `trace2ocelchor` (Hobeck et al.): its parser (DELEGATECALL rewrite,
    address normalization) and its naming helpers (event types, participant
    roles, message names and content, timestamps). Only the walk that turns
    the call tree into exchange events is redone here, keeping the structure
    of `trace2ocelchor`: each transaction is a case; the root call is a
    one-way task (a request with no response), which opens the root scope
    when it has internal calls; a call without nested calls is a two-way
    task; a call with nested calls becomes a request task and a response
    task that open and close its scope. Each task records its scope path."""
    parser, tr = _trace2ocelchor()

    def scalar(d):
        """Content values as trace2ocelchor serializes them, with str(); this
        also keeps integers from becoming floats in the object table. None
        stays absent."""
        return {k: (None if v is None else str(v)) for k, v in d.items()}

    traces = parser.load_trace_file(Path(path))
    names = tr._collect_contract_names(traces)
    senders = tr._collect_senders(traces)
    roles: Dict[str, str] = {}
    events: List[ExchangeEvent] = []

    def role(addr: str) -> None:
        if addr and addr not in roles:
            roles[addr] = tr._participant_type(addr, senders, names)

    def emit(trace, order, activity, sender, receiver, key, name, content,
             scopes, response=None):
        role(sender)
        role(receiver)
        ev = ExchangeEvent(
            case=trace.transaction_hash, activity=activity,
            timestamp=pd.Timestamp(tr._make_time(trace, order)), order=len(events),
            sender=sender or None, receivers=(receiver,) if receiver else (),
            key=key, name=name, content=scalar(content), scope_path=tuple(scopes),
            attributes={"trace_order": order})
        if response is not None:
            ev.response_key, ev.response_name, ev.response_content = (
                response[0], response[1], scalar(response[2]))
        events.append(ev)

    def walk(trace, frame, scopes, order):
        disc = tr._participant_discriminator(names.get(frame.to_addr), frame.to_addr)
        req = (f"req:{frame.call_id}", tr._request_message_type(frame.activity),
               tr._input_attrs(frame.inputs, frame.inputs_call))
        res = (f"res:{frame.call_id}", tr._response_message_type(frame.activity),
               tr._output_attrs(frame.output))
        if not frame.calls:
            emit(trace, order, tr._event_type(frame.activity, disc),
                 frame.from_addr, frame.to_addr, *req, scopes, response=res)
            return order + 1
        inner = scopes + [Scope(frame.call_id, tr._call_key(frame.activity, disc))]
        emit(trace, order, tr._event_type(frame.activity, disc, kind="request"),
             frame.from_addr, frame.to_addr, *req, inner)
        order += 1
        for child in frame.calls:
            order = walk(trace, child, inner, order)
        emit(trace, order, tr._event_type(frame.activity, disc, kind="response"),
             frame.to_addr, frame.from_addr, *res, inner)
        return order + 1

    for trace in traces:
        disc = tr._participant_discriminator(names.get(trace.contract_address),
                                             trace.contract_address)
        req = ("req:root", tr._request_message_type(trace.function_name),
               tr._input_attrs(trace.inputs))
        if not trace.internal_txs:
            emit(trace, 0, tr._event_type(trace.function_name, disc),
                 trace.sender, trace.contract_address, *req, [])
            continue
        root = [Scope("root", tr._call_key(trace.function_name, disc))]
        emit(trace, 0, tr._event_type(trace.function_name, disc, kind="request"),
             trace.sender, trace.contract_address, *req, root)
        order = 1
        for frame in trace.internal_txs:
            order = walk(trace, frame, root, order)

    return SourceLog(name=Path(path).stem, inputs=[str(path)], exchange=events,
                     participant_roles=roles)
