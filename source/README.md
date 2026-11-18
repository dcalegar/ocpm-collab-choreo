# source/

- `mapping/`: the unified mapping from the original log formats in `../data/` to OCEL 2.0,
  its consistency criteria, and the export to the representation of Hobeck et al. See
  [`mapping/README.md`](mapping/README.md).
- `experiments/`: the comparison of its output with the reference object-centric logs
  (`data/*/infsys/` and `data/*/hobeck/`); the input/reference pairs are listed in
  `../data/README.md`. See [`experiments/README.md`](experiments/README.md).
- `prediction/`: the InfSys prediction tasks restated over the choreography view,
  computed with the InfSys task library through an adapter. See
  [`prediction/README.md`](prediction/README.md).
- `requirements.txt`: the Python environment of the mapping and the experiments, and of
  the adapter of `prediction/`.
- `requirements-predict.txt`: the environment of `prediction/run_prediction.py` (OCPA,
  with its pm4py 2.2.32, and the InfSys pipeline).
