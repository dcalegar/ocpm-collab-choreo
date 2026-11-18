"""Prediction of the restated InfSys tasks on the choreography view, with the InfSys pipeline.

Each log goes through `evaluation.rq3_pipeline.run_one_log` of InfSys, unchanged: OCPA
import and features (`features`), persisted case folds, grouped 5-fold cross-validation,
the random forest (`predictors`), the degeneracy flag, and the trivial baseline. Three
things adapt it to the choreography view:

1. The schema sets `ChoreographyCase` as the case type, so OCPA's leading-type
   extraction builds one process execution per choreography case, and
   `ChoreographyMessage` as the message type of the "previous message count" feature.
   In a ChL there are no `OrchestrationCase` objects, so the InfSys feature that counts
   them is constant 0.
2. `run_one_log` builds its label log with `read_ocel2_labels`, the InfSys adapter of
   the collaboration view. `_label_reader` replaces that one module attribute, for the
   duration of a call, with the neutral view of `choreo_view`. OCPA still reads the
   SQLite file itself, and the alignment oracle of `extract_feature_table` (OCPA's
   remaining time equals NV-PrT on the adapted log, event by event) checks that both
   sides see the same executions and events.
3. Each log runs up to twice, once per view (`tasks_chor.RESTATED`): the sender view for
   NE-NEPr, NV-TNE, OB-M, NE-NPaA, NV-NMPr, and NV-PrT, and the involvement view of the
   participant for NE-NMPa, NV-NMPa, NV-PaT, and OB-P. Both runs share the persisted
   folds of the log.

The parameters are part of the task, so they are given, never chosen from the data: the
participant of NE-NMPa, NV-NMPa, NV-PaT, and OB-P (`--participant`) and the activity of
OB-M (`--activity`). A task whose parameter is not given is not run and is reported as
skipped; a parameter that does not occur in the log is an error.

Input: the ChL profile of the mapping output, `data/<dataset>/mapped/<dataset>_chl.sqlite`.
Output: `../experiments/results/e4_prediction_<dataset>.{md,json}`; folds in `folds/`.

Run with the prediction environment (`../requirements-predict.txt`), from the repository root:

    .venv-predict/bin/python source/prediction/run_prediction.py <dataset> \
        [--participant P] [--activity A]
"""

from __future__ import annotations

import argparse
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import choreo_view as cv  # noqa: E402
import tasks_chor as tc  # noqa: E402
from common import DATA, md_table, require, write_results  # noqa: E402

from evaluation import rq3_pipeline  # noqa: E402  (InfSys)
from evaluation.config import ExperimentConfig, LogSpec  # noqa: E402
from tasks.catalog import TASKS  # noqa: E402
from tasks.schema import Schema  # noqa: E402

# The nine collaboration scenarios of Pena et al. with a ChL.
CHL_LOGS = ["artificial1", "artificial5", "healthcare", "real1", "real2", "real3",
            "real4", "real5", "smartagriculture"]

CHOREOGRAPHY_SCHEMA = Schema(ot_cc=cv.OT_CHC, ot_message=cv.OT_CM)
FOLDS = HERE / "folds"
RESULT_NAME = "e4_prediction"


def chl_path(dataset: str) -> Path:
    return DATA / dataset / "mapped" / f"{dataset}_chl.sqlite"


@dataclass
class Run:
    view: str                     # tc.SENDER or tc.INVOLVEMENT
    log: object                   # neutral ObjectCentricLog of InfSys
    tasks: List[str]


def check_params(view: cv.ChoreographyView, participant: Optional[str],
                 activity: Optional[str]) -> None:
    if participant is not None and participant not in view.participants():
        raise ValueError(f"participant {participant!r} does not occur in the log; "
                         f"participants: {', '.join(view.participants())}")
    activities = sorted({t.activity for t in view.tasks})
    if activity is not None and activity not in activities:
        raise ValueError(f"activity {activity!r} does not occur in the log; "
                         f"activities: {', '.join(activities)}")


def plan(view: cv.ChoreographyView, participant: Optional[str],
         activity: Optional[str]) -> "tuple[List[Run], List[str]]":
    """The runs of a log and the tasks skipped for lack of a parameter."""
    check_params(view, participant, activity)
    runs, skipped = [], []
    for view_name in (tc.SENDER, tc.INVOLVEMENT):
        keys = [k for k, t in tc.RESTATED.items() if t.view == view_name]
        given = {"participant": participant, "activity": activity}
        run_keys = [k for k in keys if TASKS[k].param is None or given[TASKS[k].param]]
        skipped += [k for k in keys if k not in run_keys]
        if not run_keys:
            continue
        log = (cv.involvement_view(view, participant) if view_name == tc.INVOLVEMENT
               else cv.sender_view(view))
        runs.append(Run(view_name, log, run_keys))
    return runs, skipped


@contextmanager
def _label_reader(log):
    """Make `run_one_log` take its labels from `log` instead of the InfSys adapter."""
    def read(path, schema, ocpa_ocel=None):
        return log
    with mock.patch.object(rq3_pipeline, "read_ocel2_labels", read):
        yield


def config(tasks: List[str], participant: Optional[str] = None,
           activity: Optional[str] = None) -> ExperimentConfig:
    return ExperimentConfig(logs=[], schema=CHOREOGRAPHY_SCHEMA, rq3_tasks=tasks,
                            predictor="random_forest", folds_dir=str(FOLDS),
                            obp_target_participant=participant,
                            obm_target_activity=activity)


def run_dataset(dataset: str, participant: Optional[str] = None,
                activity: Optional[str] = None) -> List[dict]:
    path = require(chl_path(dataset))
    view = cv.read_choreography(path)
    runs, skipped = plan(view, participant, activity)
    spec = LogSpec(name=f"{dataset}_chl", ocel_path=str(path), xes_path="")
    rows: List[dict] = []
    for run in runs:
        with _label_reader(run.log):
            out = rq3_pipeline.run_one_log(spec, config(run.tasks, participant, activity))
        for rec in out:
            rec.update(dataset=dataset, kind=tc.RESTATED[rec["task"]].kind, view=run.view)
            rec.pop("anchor", None)   # InfSys anchor of the collaboration view
        rows.extend(out)
    rows += [{"dataset": dataset, "task": k, "kind": tc.RESTATED[k].kind,
              "view": tc.RESTATED[k].view, "samples": 0,
              "note": f"skipped: no {TASKS[k].param} given"} for k in skipped]
    order = list(tc.RESTATED)
    return sorted(rows, key=lambda r: order.index(r["task"]))


def _fmt(x, digits=3):
    return "–" if x is None else (f"{x:.{digits}f}" if isinstance(x, float) else str(x))


def markdown(rows: List[dict]) -> str:
    header = ["Log", "Task", "Kind", "Param.", "Samples", "Labels", "Degenerate",
              "Metric", "Mean", "SD", "Baseline", "Folds", "Note"]
    body = [[r["dataset"], r["task"], r["kind"],
             r.get("participant") or r.get("obm_activity") or "",
             r["samples"], r.get("n_labels", "–"), r.get("degenerate", "–"),
             r.get("metric_name", "–"), _fmt(r.get("metric_mean")), _fmt(r.get("metric_sd")),
             _fmt(r.get("baseline_mean")), r.get("folds", "–"), r.get("note", "")]
            for r in rows]
    return ("# E4: restated InfSys tasks on the choreography view\n\n"
            "InfSys pipeline (OCPA features, random forest, 5-fold CV grouped by "
            "ChoreographyCase) on the ChL profile. Metric: macro F1 for classification, "
            "MAE in seconds or tasks for regression; baseline: majority class or median.\n\n"
            + md_table(header, body) + "\n")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("dataset", choices=CHL_LOGS)
    p.add_argument("--participant",
                   help="participant of NE-NMPa, NV-NMPa, NV-PaT, and OB-P (skipped if absent)")
    p.add_argument("--activity", help="activity of OB-M (skipped if absent)")
    args = p.parse_args(argv)
    rows = run_dataset(args.dataset, args.participant, args.activity)
    write_results(f"{RESULT_NAME}_{args.dataset}", rows, markdown(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
