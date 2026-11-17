# data/

Event logs used as examples in the paper. The set is the union of the logs evaluated by
InfSys (Calegari et al., `CalegariDPR26`) and by Hobeck et al. (`HobeckMMW27`). Each
dataset has its own folder. Inside it, one subfolder per provenance holds the files
exactly as that source publishes them (copied on 2026-11-12, unmodified; the XES inputs of
Hobeck et al. were added on 2026-11-17). The logs are used in these original formats.

Each log is kept once. When two sources publish the same log, or one log is contained in
another, only the copy the papers use is kept; the provenance notes list what was dropped
and why.

An earlier unified XES format (`collab.xesext`), the logs migrated to it, and their
mapped OCEL logs were discarded on 2026-11-17. They are archived outside this repository.

## Datasets

| Folder | Scenario | Family | Cases | Events (CL) | Part. | Used by |
|---|---|---|--:|--:|--:|---|
| `artificial1/` | Synthetic (PartyA, PartyC) | Collaborative XES | 100 | 800 | 2 | InfSys |
| `artificial5/` | Synthetic (PartyA–PartyD) | Collaborative XES | 100 | 2,360 | 4 | InfSys |
| `healthcare/` | Hospitalization | Collaborative XES | 100 | 1,450 | 4 | InfSys, Hobeck |
| `real1/` | Two-robot search | Collaborative XES | 22 | 154 | 2 | Hobeck |
| `real2/` | Travel booking | Collaborative XES | 100 | 1,476 | 2 | Hobeck |
| `real3/` | Smart thermostat | Collaborative XES | 100 | 1,818 | 3 | Hobeck |
| `real4/` | ZooClub registration | Collaborative XES | 100 | 1,800 | 3 | InfSys, Hobeck |
| `real5/` | Academic paper review | Collaborative XES | 100 | 1,289 | 3 | Hobeck |
| `smartagriculture/` | Tractor coordination | Collaborative XES | 10 | 435 | 3 | Hobeck |
| `bpic2013/` | Volvo IT incident management | Real-life, reinterpreted | 7,554 | 69,584 | 25 | InfSys |
| `eth-depositcontract/` | Consensus Layer: DepositContract | Ethereum traces | — | — | 3 | Hobeck |
| `eth-ensgovernor/` | ENS: ENSGovernor | Ethereum traces | — | — | 8 | Hobeck |
| `eth-tornadocash-governance/` | Tornado.Cash: GovernanceProposalStateUpgrade | Ethereum traces | — | — | 16 | Hobeck |
| `eth-tornadocash-router/` | Tornado.Cash: TornadoRouter | Ethereum traces | — | — | 22 | Hobeck |
| `eth-pancakeswap-masterchefv3/` | PancakeSwap: MasterChefV3 | Ethereum traces | — | — | 45 | Hobeck |
| `eth-uniswap-v2pair-usdc-weth/` | Uniswap: UniswapV2Pair (USDC–WETH) | Ethereum traces | — | — | 16 | Hobeck |
| `eth-sushiswap-router/` | SushiSwap: Router | Ethereum traces | — | — | 55 | Hobeck |
| `eth-cryptokitties-core/` | CryptoKitties: Core (KittyCore) | Ethereum traces | — | — | 78 | Hobeck |
| `eth-cryptokitties-saleauction/` | CryptoKitties: SaleClockAuction | Ethereum traces | — | — | 4 | Hobeck |
| `eth-boredapeyachtclub/` | Yuga Labs: BoredApeYachtClub | Ethereum traces | — | — | 13 | Hobeck |
| `eth-nounstoken/` | Nouns DAO: NounsToken | Ethereum traces | — | — | 11 | Hobeck |
| `eth-beanstalk-attack/` | Beanstalk Farms: attack transaction | Ethereum traces | — | — | 59 | Hobeck |

Cases, events, and participants of the collaborative logs are counted on `pena/*_collab.xes`;
for BPIC 2013, on `infsys/BPI2013_incidents_collaborative.xes`. The Ethereum logs have no
case notion: their participant counts, and their variant, task, and message counts, are in
Table 2 of `HobeckMMW27` and in the ocelchor README.

## Use of the collaborative logs and object-centric results

Of Peña et al.'s nine collaborative logs, InfSys uses four and Hobeck et al. use seven.
Only Healthcare and Real4 are shared. Each dataset folder holds the object-centric log
that each work produced from it. These logs are the references for the new mapping: from
the same input, its output should be semantically similar to them.

| Log | InfSys | Hobeck et al. | InfSys OCEL (`infsys/`) | Hobeck et al.'s input (`hobeck/`) | Hobeck et al.'s OCEL (`hobeck/`) |
|---|:-:|:-:|---|---|---|
| Artificial1 | ✓ | | `collectivelog_artificial1_collab.sqlite` | — | — |
| Artificial5 | ✓ | | `collectivelog_artificial5_collab.sqlite` | — | — |
| Healthcare | ✓ | ✓ | `collectivelog_healthcare_collab.sqlite` | `collectivelog_healthcare.xes`, `_uniqueInteraction.xes` | `healthcare_uniqueInteraction_ocel.json` |
| Real1 | | ✓ | — | `collectivelog_real1.xes`, `_uniqueInteraction.xes` | `real1_uniqueInteraction_ocel.json` |
| Real2 | | ✓ | — | `collectivelog_real2.xes`, `_uniqueInteraction.xes` | `real2_uniqueInteraction_ocel.json` |
| Real3 | | ✓ | — | `collectivelog_real3.xes`, `_uniqueInteraction.xes` | `real3_uniqueInteraction_ocel.json` |
| Real4 | ✓ | ✓ | `collectivelog_real4_collab.sqlite` | `collectivelog_real4.xes`, `_uniqueInteraction.xes` | `real4_uniqueInteraction_ocel.json` |
| Real5 | | ✓ | — | `collectivelog_real5.xes`, `_uniqueInteraction.xes` | `real5_uniqueInteraction_ocel.json` |
| Smart agriculture | | ✓ | — | `collectivelog_smartagriculture.xes`, `_uniqueInteraction.xes` | `smartagriculture_uniqueInteraction_ocel.json` |

InfSys also uses BPIC 2013 (`bpic2013/infsys/`), and Hobeck et al. also use the 12
Ethereum logs (`eth-*/hobeck/`). The usage was checked against the log statistics table of
InfSys and the evaluation tables of `HobeckMMW27`.

The pairs to compare are:

- **InfSys.** Input: `pena/collectivelog_<n>_collab.xes` (the CL, identical to the InfSys
  input except for two Real4 activity names; see the provenance notes). Reference:
  `infsys/collectivelog_<n>_collab.sqlite`.
- **Hobeck et al., collaborative logs.** Input:
  `hobeck/collectivelog_<n>_uniqueInteraction.xes`, the deduplicated log that
  `xescol2ocelchor` converted. Reference: `hobeck/<n>_uniqueInteraction_ocel.json`. The
  raw log `hobeck/collectivelog_<n>.xes` is the input of the deduplication
  (`generate_unique_xes.py`). Its OCEL would be larger than the reference.
- **Hobeck et al., Ethereum logs.** Input: `hobeck/<stem>.json` (the transaction traces
  that `trace2ocelchor` converts). Reference: `hobeck/<stem>_ocel.json`.

A comparison with Hobeck et al.'s OCEL must account for its shifted timestamps (see the
provenance notes).

## Folder layout and provenance

### Collaborative XES logs (9 scenarios)

All nine come from collaboration models executed with the log generator of Corradini et
al. (`Corradini24`, <https://bitbucket.org/proslabteam/colliery_validation/>, commit
`74d06e1`; the Artificial and Healthcare models first appear in Corradini et al. 2022,
BPMDS). Peña et al. normalized these logs and derived from them the collaboration log (CL)
and the choreography log (ChL). Both papers start from Peña's files.

`pena/` holds these initial logs. `infsys/` and `hobeck/` hold the object-centric logs
that result from processing them: the OCEL 2.0 log of the collaboration view produced by
the InfSys mapping, and the OCEL 2.0 log of the choreography view produced by
`xescol2ocelchor`. `hobeck/` also holds the XES inputs of Hobeck et al.

| Subfolder | Files | Source |
|---|---|---|
| `pena/` | `collectivelog_<n>_collab.xes` (CL, with the `collab` extension); `collectivelog_<n>_chor.xes` (ChL); `collectivelog_<n>.bpmn` (normative collaboration model by Corradini et al.; absent for Real1 and Smart agriculture) | Peña et al. `PenaADC24`. CL and model: <https://gitlab.fing.edu.uy/open-coal/bpmncollaborativepm>, `Evaluation/` (`gitlabcollab`, commit `c715bea`). ChL: <https://gitlab.fing.edu.uy/open-coal/bpmnchoreographypm>, `Evaluation/` (`gitlabchoreo`, commit `82809e3`). |
| `infsys/` | `collectivelog_<n>_collab.sqlite`: OCEL 2.0 output of the InfSys mapping on the CL, in the format OCPA reads | InfSys `CalegariDPR26`, <https://github.com/dcalegar/ocpm-collab-ppm>, `data/logs/Predict-Collab/` (commit `98d5e697`). The input CL logs were redistributed by Delgado et al. `DelgadoCER25` at <https://gitlab.fing.edu.uy/open-coal/predict-collab>, `experimentation/`. |
| `hobeck/` | `collectivelog_<n>.xes`: Peña's raw log, the input of Hobeck et al.'s pipeline. `collectivelog_<n>_uniqueInteraction.xes`: the raw log deduplicated by `generate_unique_xes.py` to one trace per choreography variant, with traces without sends dropped; it is the input of `xescol2ocelchor`. `<n>_uniqueInteraction_ocel.json`: OCEL 2.0 output of `xescol2ocelchor`, with one event per send (the choreography task, with `choreo:*` qualifiers), and one `choreographyInstance`, one object per participant, and one message object per send | Hobeck et al. `HobeckMMW27`, <https://github.com/23722/ocelchor> (paper tag `v1.1-BPM-2026-PTF`; copied from the local clone, branch `v1.2-IS-2026-CPMDS`, commit `edbb6c1`): `xescol2ocelchor/data/input/`, `xescol2ocelchor/data/input_unique/`, and `ocelchorvalidator/data/input/`. The local clone has CRLF line endings; the committed files have LF and are otherwise identical. |

`infsys/` exists only for the four InfSys logs, and `hobeck/` only for the seven Hobeck
logs. Artificial1 and Artificial5 still have their CL, ChL, and model in `pena/`.

Provenance notes, checked by comparing the files after removing carriage returns:

- **One CL per scenario.** The CL used by InfSys and the CL that ocelchor ships as test
  ground truth (`xescol2ocelchor/tests/data/`) are identical to `pena/*_collab.xes`,
  except for Real4: the InfSys copy drops a trailing space in two activity names
  (`Send request to billing department`, `Wait fot payment`), 100 occurrences each. Only
  Peña's copy is kept. A regression test against the InfSys OCEL of Real4 must therefore
  ignore that trailing space.
- **The raw log is contained in the CL.** Peña's normalized raw log
  (`Evaluation/collectivelog_<n>.xes`) is the input of Hobeck et al.: the files in
  `ocelchor/xescol2ocelchor/data/input/` are identical to it. The CL has the same traces
  and events, with the same attribute values and timestamps (same instants, other time
  zone), plus the `collab:*` attributes. The raw log is kept only in `hobeck/`, as the
  input of Hobeck et al., and only for their seven logs. For Artificial1 and Artificial5,
  removing the `collab:*` attributes from the CL restores it.
- **Corradini's originals are not kept.** Peña's raw logs differ from Corradini's
  `collectivelog.xes` only in the log name (`collog` → `collog_<n>`) and, for Healthcare,
  Real1, and Smart agriculture, in two attribute keys (`msgInstanceID` → `msgInstanceId`,
  `msgRole` → `msgType`). Peña's `collectivelog_<n>.bpmn` files are byte-identical to
  Corradini's `model.bpmn`. The Real2, Real3, and Healthcare models that ocelchor ships
  under `xescol2ocelchor/data/normative BPMN files (from Corradini et al. 2024)/` match
  them except for whitespace.
- **One serialization per OCEL.** InfSys also publishes each OCEL as `.jsonocel`, a mirror
  of the `.sqlite`; only the `.sqlite` is kept.
- **The ChL aligns with the CL sends.** In all nine logs, every ChL event matches the CL
  send at the same position in the same trace (same message identifier, timestamp, and
  activity): Artificial1 200, Artificial5 530, Healthcare 550, Real1 44, Real2 869, Real3
  653, Real4 400, Real5 345, Smart agriculture 114, so 3,705 in total (2,975 for the seven
  Hobeck logs). A CL and its ChL can therefore be merged into one log with the complete
  profile. ocelchor redistributes the same ChL files in `eval_artifacts/input/`.
- **Hobeck's deduplicated XES is a subset of the CL.** Each trace of
  `hobeck/collectivelog_<n>_uniqueInteraction.xes` is a CL trace with the same events and
  attribute values, without the `collab:*` attributes. Selected traces per log:
  Healthcare 17, Real1 1, Real2 96, Real3 59, Real4 1, Real5 3, Smart agriculture 10.
- **Hobeck's OCEL timestamps are shifted.** The pm4py export of the deduplicated XES kept
  the local clock time but replaced the UTC offset with `+00:00`. Every timestamp in the
  OCEL is therefore shifted by a constant 2 h (1 h in Real1). Event order is unaffected,
  but a comparison with the OCEL must account for the offset.
- **Cases without messages.** In Real5, 31 of the 100 cases contain no message: the
  author writes the paper, checks the submission guide, and the case ends. Both derived
  choreography logs leave them out: Peña's ChL has 69 traces, and Hobeck's
  `generate_unique_xes.py` drops "traces with zero send events […] — they have no
  choreography behavior to represent". The CL keeps all 100 cases, so the CL and the ChL
  are both needed.
- Corradini et al. and Peña et al. also publish Artificial2–Artificial4, and Corradini et
  al. publish per-participant logs. Neither paper uses them, so they are not copied.

### BPI Challenge 2013 (`bpic2013/`)

| Subfolder | Files | Source |
|---|---|---|
| `original/` | `BPI_Challenge_2013_incidents.xes.gz`, `DATA_incidents.xml`, `summary.pdf` | Steeman (2013), 4TU.ResearchData, doi:[10.4121/uuid:500573e6-accc-4b0c-9576-aa5468b10cee](https://doi.org/10.4121/uuid:500573e6-accc-4b0c-9576-aa5468b10cee) |
| `infsys/` | `BPI2013_incidents_collaborative.xes` (collaborative reinterpretation); `.sqlite` (OCEL 2.0); `collab_convert.py` (the conversion); `metrics.json` | InfSys `CalegariDPR26`, <https://github.com/dcalegar/ocpm-collab-ppm>, `data/logs/BPIChallenge2013/` |

The source log records only the receiving side of each hand-over. `collab_convert.py`
synthesizes the matching `SendTask` (4,051 events) and flags it with
`collab:synthesized="true"`. As for the other InfSys logs, the `.jsonocel` mirrors of the
OCEL are not kept.

### Ethereum transaction traces (12 datasets, `eth-*/`)

| Subfolder | Files | Source |
|---|---|---|
| `hobeck/` | `<address>_uniqueFunction.json` (one representative transaction per initial contract function); `<address>_uniqueFunction_ocel.json` (OCEL 2.0 choreography log from `trace2ocelchor`) | Hobeck et al. `HobeckMMW27`, <https://github.com/23722/ocelchor>, `trace2ocelchor/data/input_unique/` and `ocelchorvalidator/data/input/` |

The traces were extracted by Corradini et al. 2026 (PerCom Workshops) and are published in
Marcelletti's BlockchainDataset, <https://github.com/AlessandroMarcellettiUnicam1/BlockchainDataset>
(commit `5e520f5`). That repository stores the full trace family through Git LFS (about
3.3 GB; for example, SushiSwap Router 1.0 GB and TornadoRouter 1.3 GB), so it is not
copied here. Download it from the upstream repository if the full traces are needed.

`eth-tornadocash-governance/hobeck/` also contains `0x5e_cd49912.json` and its OCEL: the
single `unlock` transaction that Hobeck et al. use as the running example (Fig. 3) and that
`generate_fig4.py` renders. It is not one of the 12 evaluation datasets.

## References

BibTeX keys refer to `bibliography.bib` in the paper repository
(`dcalegar/ICPM27Cominds-PredCoreo`). The three entries
marked *(not in bib)* would have to be added before citing them.

| Key | Reference |
|---|---|
| `CalegariDPR26` | D. Calegari, A. Delgado, L. Peña, M. Rubio. A Framework for Object-Centric Predictive Monitoring of Collaborative Processes. arXiv:2608.27671 (2026). Code and data: <https://github.com/dcalegar/ocpm-collab-ppm> |
| `HobeckMMW27` | R. Hobeck, A. Marcelletti, A. Morichetta, I. Weber. Representing BPMN Choreographies in OCEL 2.0. BPM 2026 PTF, LNBIP 600, pp. 195–210 (2027). doi:10.1007/978-3-032-36710-5_13. Code and data: <https://github.com/23722/ocelchor> |
| `Corradini24` | F. Corradini, S. Pettinari, B. Re, L. Rossi, F. Tiezzi. A technique for discovering BPMN collaboration diagrams. SoSyM 23(6), 1323–1343 (2024). Data: <https://bitbucket.org/proslabteam/colliery_validation/> |
| `PenaADC24` | L. Peña, D. Andrade, A. Delgado, D. Calegari. Inter-organizational collaborative BPMN 2.0 business process discovery. JIIS (2024) |
| `gitlabcollab` | Peña, Delgado, Calegari. BPMN 2.0 collaborative process discovery ProM plugin (2022). <https://gitlab.fing.edu.uy/open-coal/bpmncollaborativepm> |
| `gitlabchoreo` | Andrade, Delgado, Calegari. BPMN 2.0 choreography process discovery ProM plugin (2023). <https://gitlab.fing.edu.uy/open-coal/bpmnchoreographypm> |
| `DelgadoCER25` | A. Delgado, D. Calegari, C. Espino, N. Ribero. Predictive process monitoring for collaborative business processes: concepts and application. Discover Analytics 3(1), 5 (2025). doi:10.1007/s44257-025-00031-8. Tool: <https://gitlab.fing.edu.uy/open-coal/predict-collab> |
| *(not in bib)* | F. Corradini, B. Re, L. Rossi, F. Tiezzi. A technique for collaboration discovery. BPMDS 2022, LNBIP 450, pp. 63–78 (2022). doi:10.1007/978-3-031-07475-2_5 |
| *(not in bib)* | F. Corradini, L. Luzi, A. Marcelletti, A. Morichetta, B. Re. Extracting and decoding internal transactions in EVM-based blockchains. PerCom Workshops 2026, pp. 1–6. IEEE (2026). Data: <https://github.com/AlessandroMarcellettiUnicam1/BlockchainDataset> |
| *(not in bib)* | W. Steeman. BPI Challenge 2013, incidents [dataset]. 4TU.ResearchData (2013). doi:10.4121/uuid:500573e6-accc-4b0c-9576-aa5468b10cee |
