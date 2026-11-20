# E4: restated InfSys tasks on the choreography view

InfSys pipeline (OCPA features, random forest, 5-fold CV grouped by ChoreographyCase) on the ChL profile. Metric: macro F1 for classification, MAE in seconds or tasks for regression; baseline: majority class or median.

| Log | Task | Kind | Param. | Samples | Labels | Degenerate | Metric | Mean | SD | Baseline | Folds | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| healthcare | NE-NEPr | direct |  | 450 | 7 | False | f1_macro | 0.827 | 0.025 | 0.052 | 5 |  |
| healthcare | NV-TNE | direct |  | 450 | 440 | False | mae | 4.390 | 0.263 | 4.728 | 5 |  |
| healthcare | OB-M | direct | Communicate the need to hospitalise | 450 | 2 | False | f1_macro | 0.620 | 0.097 | 0.402 | 5 |  |
| healthcare | NE-NPaA | redefined |  | 450 | 3 | False | f1_macro | 0.988 | 0.017 | 0.267 | 5 |  |
| healthcare | NE-NMPa | redefined | Hospital | 299 | 3 | False | f1_macro | 0.845 | 0.079 | 0.267 | 5 |  |
| healthcare | NV-NMPr | redefined |  | 450 | 6 | False | mae | 1.084 | 0.150 | 1.326 | 5 |  |
| healthcare | NV-NMPa | redefined | Hospital | 450 | 4 | False | mae | 0.986 | 0.130 | 1.145 | 5 |  |
| healthcare | NV-PrT | redefined |  | 450 | 448 | False | mae | 15.714 | 2.341 | 15.445 | 5 |  |
| healthcare | NV-PaT | redefined | Hospital | 450 | 300 | False | mae | 21.095 | 3.147 | 20.822 | 5 |  |
| healthcare | OB-P | redefined | Hospital | 450 | 2 | False | f1_macro | 0.621 | 0.028 | 0.389 | 5 |  |
