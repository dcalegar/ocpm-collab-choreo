"""E4. Example of choreography-level prediction over the unified representation.

The ten distinct InfSys tasks restated over the choreography view (paper, Table
`tab:tasks-collab`) are computed on the ChL profile of Healthcare, the running example
of the paper and the scenario shared by InfSys and Hobeck et al., with the InfSys
pipeline: OCPA features with `ChoreographyCase` as leading type, a random forest, and
5-fold cross-validation grouped by case, against a trivial baseline. The example
compares nothing (views, profiles, logs, or predictors).

The parameters are part of the tasks and follow the domain, not the labels: the
participant of NE-NMPa, NV-NMPa, NV-PaT, and OB-P is the Hospital, and the activity of
OB-M is "Communicate the need to hospitalise".

The adapter, the restated tasks, and the runner live in `../prediction/` (see its
README). This script needs the prediction environment (`../requirements-predict.txt`):

    cd source/experiments && ../../.venv-predict/bin/python e4_prediction.py

Output: `results/e4_prediction_healthcare.{md,json}`; folds in `../prediction/folds/`.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "prediction"))

import run_prediction as rp  # noqa: E402

DATASET = "healthcare"
PARTICIPANT = "Hospital"
ACTIVITY = "Communicate the need to hospitalise"


def main() -> int:
    return rp.main([DATASET, "--participant", PARTICIPANT, "--activity", ACTIVITY])


if __name__ == "__main__":
    sys.exit(main())
