# A Unified Object-Centric Representation of Collaboration and Choreography Views for Predictive Process Monitoring

Unified object-centric representation of collaborative and choreography event data,
exemplified for predictive process monitoring. It combines the collaborative mapping to
OCEL 2.0 of Calegari et al. (InfSys, `CalegariDPR26`) and the choreography
representation of Hobeck et al. (`HobeckMMW27`) in a unified core, from which two
adapters produce each of these representations.

Companion repository of a paper in preparation for the Fifth International Workshop on
Collaboration Mining for Distributed Systems (COMINDS 2027), held with ICPM 2027.
The companion document [`docs/unified-representation.pdf`](docs/unified-representation.pdf)
details the representation beyond the paper: the rules of the unified mapping, the
adapters, the evaluation, and the consistency criteria.

## Authors

- Andrea Delgado, Universidad de la República, Uruguay ([ORCID 0000-0003-4749-9366](https://orcid.org/0000-0003-4749-9366))
- Daniel Calegari, Universidad ORT Uruguay, Uruguay ([ORCID 0000-0001-9506-7619](https://orcid.org/0000-0001-9506-7619))
- Richard Hobeck, Technical University of Berlin, Germany ([ORCID 0000-0001-5242-2510](https://orcid.org/0000-0001-5242-2510))
- Alessandro Marcelletti, University of Camerino, Italy ([ORCID 0000-0003-1192-6696](https://orcid.org/0000-0003-1192-6696))

## Layout

| Path | Content |
|---|---|
| `docs/` | Companion document of the paper (`unified-representation.pdf`). |
| `data/` | Event logs used as examples: 9 collaborative XES logs, BPIC 2013, and 12 Ethereum logs, in their original formats, with the object-centric logs that InfSys and Hobeck et al. produced from them. See [`data/README.md`](data/README.md) for provenance and for the input/reference pairs. |
| `source/` | The unified mapping from the original log formats to OCEL 2.0 with its adapters and consistency criteria, the experiments E1–E4 that compare its output with the reference object-centric logs in `data/` and illustrate prediction, and their results. See [`source/README.md`](source/README.md). |

## External dependencies

These are not included and must be cloned separately:

| Repository | Version | Use |
|---|---|---|
| [23722/ocelchor](https://github.com/23722/ocelchor) | branch `v1.2-IS-2026-CPMDS`, commit `edbb6c1` (paper tag `v1.1-BPM-2026-PTF`) | `trace2ocelchor` parser and naming helpers, imported unmodified to read the Ethereum traces (`$OCELCHOR`); `ocelchorvalidator` (constraints C0–C16), run unmodified on the mapping output |
| [dcalegar/ocpm-collab-ppm](https://github.com/dcalegar/ocpm-collab-ppm) | commit `98d5e697` | InfSys mapping (M1–M8; criteria P1.1–P1.6 of its paper, plus the implementation's export check P1.7), imported unmodified by the unified mapping (`pip install --no-deps -e`); prediction pipeline (OCPA features) |

## Setup and running

The commands assume both dependencies are cloned next to this repository, as
`../ocelchor` and `../ocpm-collab-ppm`. The code finds ocelchor through `$OCELCHOR`
or, if that is unset, the sibling clone.

```bash
git clone -b v1.2-IS-2026-CPMDS https://github.com/23722/ocelchor ../ocelchor
git -C ../ocelchor checkout edbb6c1
git clone https://github.com/dcalegar/ocpm-collab-ppm ../ocpm-collab-ppm
git -C ../ocpm-collab-ppm checkout 98d5e697
```

Two Python 3.10 environments are needed, because OCPA pins pm4py 2.2.32 and the
mapping uses pm4py 2.7:

| Environment | Used by | Install |
|---|---|---|
| `.venv` | mapping, E1–E3, tests | [`source/mapping/README.md`](source/mapping/README.md#setup-and-use) |
| `.venv-predict` | E4 (prediction) | [`source/prediction/README.md`](source/prediction/README.md#environment-and-use), OCPA first |

```bash
python3.10 -m venv .venv
.venv/bin/pip install -r source/requirements.txt
.venv/bin/pip install --no-deps -e ../ocpm-collab-ppm

python3.10 -m venv .venv-predict
.venv-predict/bin/pip install "git+https://github.com/ocpm/ocpa.git@de056e0203a3fa4a9bbc19a95e001eada323074a"
.venv-predict/bin/pip install -r source/requirements-predict.txt
.venv-predict/bin/pip install --no-deps -e ../ocpm-collab-ppm
```

Run the experiments in this order. `map_all.py` writes `data/<dataset>/mapped/`, and
every experiment reads it. The folder is versioned, so its contents can be inspected
without running the mapping; the one output over 50 MB, `bpic2013_cl.jsonocel`, is
stored as `bpic2013_cl.jsonocel.gz`:

```bash
cd source/mapping && ../../.venv/bin/python map_all.py
cd ../experiments
../../.venv/bin/python e1_infsys.py
../../.venv/bin/python e2_hobeck.py
../../.venv/bin/python e2b_roundtrip.py
../../.venv/bin/python e3_consistency.py
../../.venv-predict/bin/python e4_prediction.py
```

Each experiment writes its results to `source/experiments/results/` and exits with 1
if its property fails. The tests run from the repository root:
`.venv/bin/python -m pytest source` and
`.venv-predict/bin/python -m pytest source/prediction/tests`. Details per step:
[`source/experiments/README.md`](source/experiments/README.md#running).

## References

- D. Calegari, A. Delgado, L. Peña, M. Rubio. A Framework for Object-Centric Predictive
  Monitoring of Collaborative Processes. arXiv:2608.27671 (2026).
- R. Hobeck, A. Marcelletti, A. Morichetta, I. Weber. Representing BPMN Choreographies in
  OCEL 2.0. BPM 2026 PTF, LNBIP 600, pp. 195–210 (2027).
  doi:10.1007/978-3-032-36710-5_13.

The full list, with the sources of every dataset, is in `data/README.md`.

## License

The code is licensed under the GNU GPL v3.0 (see `LICENSE`). The logs in `data/` keep the
terms of their original sources, which `data/README.md` identifies for each dataset.
