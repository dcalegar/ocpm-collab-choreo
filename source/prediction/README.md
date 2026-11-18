# prediction/: the InfSys tasks on the choreography view

The paper restates the prediction tasks of InfSys over the choreography view (Section 4,
Table `tab:tasks-collab`). This directory computes them by reusing the task library of
`ocpm-collab-ppm` (`src/tasks`, commit 98d5e697) unchanged: an adapter builds the
InfSys neutral model from a log in the unified representation, and the InfSys label
functions run on it.

| File | Content |
|---|---|
| `choreo_view.py` | Reads the choreography tasks of an OCEL 2.0 SQLite log (one per event with `request`, grouped by `ChoreographyCase`, with the sender and receivers of its request message), and builds two neutral views: the sender view (`actor` = sender) and the involvement view of a participant p (`actor` = p exactly on the tasks that involve p). |
| `tasks_chor.py` | The restated tasks: kind (direct or redefined), InfSys key, and view; the collapsed and lost tasks, which are not computed; `label_rows`, which calls the InfSys `compute_label_rows` on the right view. |
| `run_prediction.py` | Runs one ChL log through `evaluation.rq3_pipeline.run_one_log` of InfSys (OCPA features, persisted folds, grouped 5-fold CV, random forest, baseline), once per view, with `ChoreographyCase` as leading type. Only the InfSys label reader is replaced, for the duration of the call; OCPA reads the SQLite file itself, and the InfSys alignment oracle checks that both sides see the same events. Takes the participant and the activity of the parameterized tasks as arguments, and writes `../experiments/results/e4_prediction_<dataset>.{md,json}` and the folds in `folds/`. |
| `tests/` | Synthetic log with hand-computed targets for the ten tasks, endpoint derivation, the involvement view, the unconditional collapses, and a cross-check with `mapping/index.py` on the mapped ChL of Artificial5; runner checks that run no log (reader replacement and restoration, runs and skipped tasks per given parameter, rejection of parameters absent from the log, schema, output format). |

| Task | Kind | View |
|---|---|---|
| NE-NEPr, NV-TNE, OB-M | direct | sender |
| NE-NPaA, NV-NMPr, NV-PrT | redefined | sender |
| NE-NMPa, NV-NMPa, NV-PaT, OB-P | redefined | involvement |

Notes:

- Every task is a send in the neutral model (`is_send=True`), so the InfSys message
  counts and message activities become task counts and task activities.
- A task without a recorded receiver (44 in the ChL of Artificial5, 26 in Healthcare)
  involves only its sender.
- The parameters are part of the task, so they are given, never chosen from the data:
  the participant of NE-NMPa, NV-NMPa, NV-PaT, and OB-P (`--participant`) and the
  activity of OB-M (`--activity`). Without a parameter, its tasks are skipped and
  reported as such; a parameter absent from the log is an error. The InfSys defaults
  (most frequent actor and activity) are not used.
- The adapter reads the SQLite file with the standard library
  (`experiments/common.read_sqlite`) and does not import the mapping, so it also runs
  in an environment with the pm4py version that OCPA requires.

- In a ChL there are no `OrchestrationCase` objects, so the InfSys feature that counts
  them is constant 0; `build_feature_set` is reused unchanged.

## Environment and use

OCPA pins pm4py 2.2.32 and the mapping uses pm4py 2.7, so prediction has its own
environment (`../requirements-predict.txt`). It reads the mapping outputs, so
`map_all.py` must run first, in `.venv`.

```bash
python3.10 -m venv .venv-predict
.venv-predict/bin/pip install "git+https://github.com/ocpm/ocpa.git@de056e0203a3fa4a9bbc19a95e001eada323074a"
.venv-predict/bin/pip install -r source/requirements-predict.txt
.venv-predict/bin/pip install --no-deps -e ../ocpm-collab-ppm   # InfSys, commit 98d5e697

.venv-predict/bin/python -m pytest source/prediction/tests      # runner and adapter
.venv/bin/python -m pytest source/prediction/tests              # adapter, cross-check with the mapping
.venv-predict/bin/python source/prediction/run_prediction.py <dataset> [--participant P] [--activity A]
```

Experiment E4 of the paper is `../experiments/e4_prediction.py`, which fixes the dataset
(Healthcare) and the parameters (Hospital, "Communicate the need to hospitalise") and calls
this runner.
