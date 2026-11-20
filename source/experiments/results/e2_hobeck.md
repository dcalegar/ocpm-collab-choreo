# E2: reproduction of Hobeck et al. (eta_H(mu_U(L)) vs. their OCEL)

| Dataset | Equivalent | Tasks (ours/ref) | Tasks differing | Instances | Scopes | Message sharing | Participant types (N2) | None values (N3) | Attributes only ours (N4) | Attributes only ref (N4) | Common attr. values differing |
|---|---|---|---|---|---|---|---|---|---|---|---|
| healthcare | yes | 116/116 | 0 | 17/17 | 0/0 | yes | identical | 0 | elemType, fromParticipant, msgType, participant | concept:name | 0 |
| real1 | yes | 2/2 | 0 | 1/1 | 0/0 | yes | identical | 0 | case:creator, case:variant, case:variant-index, elemType, fromParticipant, msgType, participant | concept:name | 0 |
| real2 | yes | 842/842 | 0 | 96/96 | 0/0 | yes | identical | 0 | elemType, fromParticipant, msgFlow, msgType, participant | concept:name, msgName | 0 |
| real3 | yes | 472/472 | 0 | 59/59 | 0/0 | yes | identical | 0 | elemType, fromParticipant, msgFlow, msgType, participant | concept:name, msgName | 0 |
| real4 | yes | 4/4 | 0 | 1/1 | 0/0 | yes | identical | 0 | elemType, fromParticipant, msgFlow, msgType, participant | concept:name, msgName | 0 |
| real5 | yes | 15/15 | 0 | 3/3 | 0/0 | yes | renamed | 0 | elemType, fromParticipant, msgFlow, msgType, participant | concept:name, msgName | 0 |
| smartagriculture | yes | 114/114 | 0 | 10/10 | 0/0 | yes | renamed | 0 | case:creator, case:variant, case:variant-index, elemType, fromParticipant, msgType, participant | concept:name | 0 |
| eth-beanstalk-attack | yes | 489/489 | 0 | 3/3 | 139/139 | yes | identical | 52 | — | — | 0 |
| eth-boredapeyachtclub | yes | 18/18 | 0 | 9/9 | 5/5 | yes | identical | 1 | — | — | 0 |
| eth-cryptokitties-core | yes | 204/204 | 0 | 22/22 | 59/59 | yes | identical | 79 | — | — | 0 |
| eth-cryptokitties-saleauction | yes | 6/6 | 0 | 2/2 | 2/2 | yes | identical | 4 | — | — | 0 |
| eth-depositcontract | yes | 9/9 | 0 | 1/1 | 1/1 | yes | identical | 0 | — | — | 0 |
| eth-ensgovernor | yes | 21/21 | 0 | 9/9 | 6/6 | yes | identical | 2 | — | — | 0 |
| eth-nounstoken | yes | 12/12 | 0 | 7/7 | 3/3 | yes | identical | 0 | — | — | 0 |
| eth-pancakeswap-masterchefv3 | yes | 241/241 | 0 | 13/13 | 64/64 | yes | identical | 37 | — | — | 0 |
| eth-sushiswap-router | yes | 267/267 | 0 | 19/19 | 67/67 | yes | identical | 40 | — | — | 0 |
| eth-tornadocash-governance | yes | 4/4 | 0 | 1/1 | 2/2 | yes | identical | 1 | — | — | 0 |
| eth-tornadocash-governance | yes | 35/35 | 0 | 11/11 | 17/17 | yes | identical | 11 | — | — | 0 |
| eth-tornadocash-router | yes | 85/85 | 0 | 2/2 | 13/13 | yes | identical | 8 | — | — | 0 |
| eth-uniswap-v2pair-usdc-weth | yes | 61/61 | 0 | 6/6 | 17/17 | yes | identical | 1 | — | — | 0 |

N1 (identifiers) applies to every row. See the docstring of `e2_hobeck.py`.
