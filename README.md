# ocpm-collab-choreo

Unified object-centric representation of collaborative and choreography event data,
exemplified for predictive process monitoring. It extends the collaborative mapping to
OCEL 2.0 of Calegari et al. (InfSys, `CalegariDPR26`) with the choreography
representation of Hobeck et al. (`HobeckMMW27`).

Companion repository of a paper in preparation for the Fifth International Workshop on
Collaboration Mining for Distributed Systems (COMINDS 2027), held with ICPM 2027.

## Layout

| Path | Content |
|---|---|
| `data/` | Event logs used as examples: 9 collaborative XES logs, BPIC 2013, and 12 Ethereum logs, in their original formats, with the object-centric logs that InfSys and Hobeck et al. produced from them. See [`data/README.md`](data/README.md) for provenance and for the input/reference pairs. |
| `source/` | The mapping from the original log formats to OCEL 2.0, and the experiments that compare its output with the reference object-centric logs in `data/` (in progress). |

## External dependencies

These are not included and must be cloned separately:

| Repository | Version | Use |
|---|---|---|
| [23722/ocelchor](https://github.com/23722/ocelchor) | branch `v1.2-IS-2026-CPMDS`, commit `edbb6c1` (paper tag `v1.1-BPM-2026-PTF`) | `trace2ocelchor` parser and naming helpers, imported unmodified to read the Ethereum traces (`$OCELCHOR`); `ocelchorvalidator` (constraints C0–C16), run unmodified on the mapping output |
| [dcalegar/ocpm-collab-ppm](https://github.com/dcalegar/ocpm-collab-ppm) | commit `98d5e697` | InfSys mapping (M1–M8, P1.1–P1.7), imported unmodified by the unified mapping (`pip install --no-deps -e`); prediction pipeline (OCPA features) |

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
