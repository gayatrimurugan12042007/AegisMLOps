# AegisMLOps research protocol

**Status:** preregistered design, frozen by the commit that introduces this file and `related_work.md`. Any later change requires a dated entry in `docs/protocol_changes.md` before analysis is rerun. Protocol values below are design decisions, not experimental findings.

## 1. Question and scope

For one-hour-ahead 2 m air temperature at Chennai (13.0827, 80.2707), does a simple cost-aware retraining policy using input-distribution drift, delayed absolute-error feedback, and unlabeled prediction disagreement maintain error close to strong baselines with fewer model replacements and lower total cost? Does disagreement reduce detection delay when reference labels are delayed, and how does the result change with retraining cost relative to error penalty?

This is a single-location, offline replay study. ERA5 is the reference target source, not an in-situ station truth. Historical Forecast API weather-model values are the candidate operational-style inputs; the two sources have different provenance. Results cannot establish live AWS performance, station-level accuracy, or transfer to other locations.

## 2. Data and information timing

- Location: latitude 13.0827, longitude 80.2707.
- Fixed temporal partitions: train 2015-01-01 through 2021-12-31; validation 2022-01-01 through 2022-12-31 (model selection only); policy calibration 2023-01-01 through 2023-12-31 (all thresholds and trigger settings); frozen test/replay stream 2024-01-01 through the latest complete date available at acquisition. The 2024-latest stream is evaluated once after all choices are frozen.
- Reanalysis source: explicitly request `models=era5` from the Historical Weather API. Target is `temperature_2m` at t+1 hour. ERA5 hourly values are a grid-cell reanalysis estimate at approximately 0.25 degrees; not a station observation. The preliminary ERA5/ERA5T stream is updated daily with about five days of latency and can be revised later.
- Operational-style input source: Historical Forecast API archive, requested using exact model identifiers selected after Chennai availability smoke checks. For each prediction origin t, features may use only values with valid time at or before t, and must correspond to data available in the archived forecast timeline then. The target remains the ERA5 temperature at t+1. Record each source/model and timestamp in the replay row. Do not substitute same-time observations or future forecast values for available inputs.
- Current live Forecast API and Previous Runs API data are not silently treated as historical ground truth. Previous Runs model output at fixed forecast lead times is auxiliary disagreement evidence only. Model availability, update ranges, missing fields, units, and API request limits are rechecked before A2 acquisition.
- Label delay is applied after prediction: 0, 24, and 120 hours. Five days is based on ERA5's stated update latency. A label becomes eligible only after its delay; no policy may access its target earlier. Predictions and features are immutable once emitted.
- All transformations, scaling, thresholds, reference bins, rolling statistics, and missing-value rules are fitted using training data, with model choices restricted to validation and policy settings restricted to 2023 calibration. Test data cannot influence any selection.

## 3. Model and baseline contract

The initial predictor is a scikit-learn RandomForestRegressor trained on ERA5-derived features from the training partition. Features will be finalized before test evaluation and will include lagged weather values, shifted rolling summaries, cyclical hour/day-of-year encodings, and weather covariates. Every feature at time t must be available by t; rolling windows are shifted so the target hour cannot leak.

On the 2022 validation year only, compare persistence, seasonal-naive, linear regression, and a small logged RF search. Choose the smallest RF whose validation MAE is within 0.01 °C of the best RF. Freeze the selected feature schema and model configuration before policy calibration. This protocol does not imply that model-training data are an independent station truth.

During replay, any retraining uses a fixed, documented reduced RF configuration and only the most recent 365 days of training examples whose labels have become available by the retraining time. Candidate deployment is immediate in the simulator after it passes the simulator's fixed schema and data-availability checks; no later outcome may be used to decide promotion.

Baselines, run on the same replay rows and label-delay setting:

1. Never retrain.
2. Fixed weekly retraining.
3. Fixed monthly retraining.
4. Drift-only: retrain on calibrated PSI/KS evidence.
5. Delayed-error-only: retrain on calibrated error-control evidence when labels arrive.
6. Disagreement-only: retrain on calibrated prediction/model disagreement.
7. Oracle: retrain at the known onset of each injected drift (upper-bound timing reference; not an implementable policy).

## 4. Drift scenarios

Inject each scenario into a copy of the frozen test stream, preserving an untouched no-drift control. Use 10 deterministic seeds in full mode and a documented subset in `--quick` mode. Use a declared event schedule and identical seeds across policies. Scenario definitions apply only after the event onset and are parameterized by severity levels 1, 2, and 3:

- **No-drift control:** no injected modification.
- **Sudden input offset:** add `s × 0.5 °C` to temperature input and `s × 2` percentage points to relative humidity, where `s ∈ {1,2,3}`; do not alter target values.
- **Gradual input trend:** linearly ramp the same temperature and humidity offsets from zero to the sudden-offset magnitude over 30 days.
- **Variance increase:** multiply deviations from each feature's training mean by `1 + 0.25s`; do not alter target values.
- **Stuck/missing feature:** set wind speed to its training median for a 14-day event; also test a missingness variant that replaces it with the training-median imputation value and raises the missingness indicator. These are separate subcases.
- **Concept change:** add `s × 0.25 °C` times the standardized temperature-lag feature to the target after onset while leaving inputs unchanged. This controlled intervention changes the conditional target relation and is not claimed to reproduce a real weather process.

Apply injections to the replay inputs and/or target only as specified. Log scenario, severity, seed, onset, and end. Do not use injected scenario labels as inputs to non-oracle policies.

## 5. Monitoring signals and policy

- **Input drift:** per-feature PSI using reference quantile bins from training data, plus two-sample KS statistic between a fixed recent window and a fixed training reference sample. A composite feature-drift flag requires at least one of the calibrated PSI/KS rules to cross its 2023-calibrated threshold on two consecutive daily checks.
- **Delayed error:** absolute-error Page-Hinkley/CUSUM and rolling-MAE ratio against the frozen training reference MAE. Only labels available by the current simulated time contribute. Require minimum evidence equal to the calibration-selected window size; no peeking at pending labels.
- **Unlabeled disagreement:** standardized spread among RF tree predictions and, where available, absolute difference between deployed prediction and the selected independent global weather-model temperature forecast for the target valid time. Normalize by training/calibration scale. A disagreement flag requires its calibrated threshold to be crossed on two consecutive checks. If no independent model is available for a replay row, mark disagreement missing and do not interpret missing as zero.
- **Proposed policy:** estimate error reduction over the next fixed 7-day horizon from the calibration-year relationship between the current signal state and errors following candidate refreshes. Trigger only when calibrated expected reduction exceeds the cost threshold for the selected cost ratio, there is minimum evidence, and at least a 7-day cooldown has elapsed. If expected benefit is not estimable from calibration data, do not trigger. Policy formula, feature normalizations, calibration windows, candidate RF configuration, and tie-breaking are fixed before test.
- **Threshold selection:** evaluate the finite documented threshold grid on the 2023 calibration partition only. Select settings minimizing calibration total cost, breaking ties by fewer retrains and then simpler thresholds. Report the full calibration search space and selected settings. No test-set threshold changes are allowed.

Ablations of the proposed policy: remove disagreement; remove delayed error; remove cost gate; remove cooldown. Ablations share all other frozen settings.

## 6. Cost model and sensitivity grid

The empirical cost objective is `J = sum_t |error_t| + rho * sum_k fit_minutes_k`, where `fit_minutes_k` is measured end-to-end CPU wall time for each simulator candidate fit, and `rho` is the error penalty in °C-hours per measured fit minute after summing hourly errors (the exact unit conversion will be implemented and documented). Report raw cumulative MAE/RMSE and total fit seconds as separate metrics as well. Do not claim dollar cost: no AWS resources are used in Stage A and local/Colab compute time is not an AWS bill.

For decision-threshold sensitivity, evaluate a predeclared logarithmic grid of retrain-cost/error-penalty ratios `{0.01, 0.1, 1, 10, 100}`. Also report the zero-retrain-cost boundary as a diagnostic, not as a realistic deployment point. Record the measured fit-time distribution. Comparisons at different ratios use the same predictions, seeds, and stream rows.

## 7. Outcomes

Primary outcomes: cumulative absolute error, MAE, RMSE, retraining count, measured total fit time, and composite cost J. Report each overall and in fixed 30-day stream blocks.

Secondary outcomes: detection delay from injection onset to first trigger; false-trigger rate on no-drift windows; missed-drift rate (no trigger within 30 days of onset); recovery time until 7-day rolling MAE returns within the calibration-derived validation tolerance for 7 consecutive days; and regret in J versus the oracle. State definitions exactly in code and results.

## 8. Statistical analysis and success/failure criteria

- Full mode: at least 10 paired random seeds per scenario and policy. Use the same seeds, injected streams, and replay schedule for all policies. `--quick` is for development only and is never described as inferential evidence.
- Summaries: mean ± standard deviation; paired bootstrap 95% confidence intervals over seed-level differences; paired Wilcoxon signed-rank tests for proposed policy versus each baseline; Holm correction across those comparisons; and paired rank-biserial effect sizes. If ties or sample-size constraints make a test invalid, report that fact and the available paired data without substituting an unplanned test.
- H1 is supported only if proposed MAE is non-inferior to the best implementable baseline within a margin set before test as one standard error of 2022 validation weekly-MAE estimates, while using fewer retrains, and composite cost is lower under at least one predeclared nonzero cost ratio with a corrected 95% interval that excludes no difference. Otherwise report H1 not supported or inconclusive.
- H2 is supported only if, at 24-hour and/or 120-hour label delay, the proposed policy's time-to-first-trigger is lower than delayed-error-only in drift scenarios, while its false-trigger rate on no-drift is also reported. Earlier triggering alone is insufficient if caused by false alarms.
- H3 is evaluated by the predeclared cost-ratio sweep. Report whether policy choice, retrain count, and comparative total cost change across the grid; do not claim dependence if the paired estimates do not show it.
- Publish negative and mixed results. Do not cherry-pick scenarios, seeds, or ratios. Test is evaluated once after protocol freeze; if an implementation bug is found, log it in `protocol_changes.md`, fix it without using result-driven tuning, and rerun the full frozen evaluation with all prior outputs retained.

## 9. Reproducibility and artifacts

Fix and record seeds, package versions, data request URLs/parameters, acquisition timestamp, raw-file SHA-256, exact source/model identifiers, split boundaries, feature schema, model configuration, policy configuration, and code commit. Keep raw responses immutable. Cache experiment results by a hash of protocol, data manifest, code version, and parameters; checkpoint/resume must not change the event order. Save per-seed and per-time-step metrics before aggregating. Every result reported in `docs/results.md` must trace to saved machine-readable output.

## 10. Limitations

ERA5 is gridded reanalysis (~0.25-degree cells), not station observation. It has an approximately five-day update latency and preliminary values may be revised. Historical/live forecast inputs differ from ERA5 training features, creating training-serving skew. Archived forecast coverage begins around 2022, so earlier partitions cannot use a matching forecast archive. One location and one target do not support geographic or target generalization. Synthetic feature and concept changes are controlled stress tests, not claims about actual Chennai climate change. CPU wall time is a proxy for retraining cost, not money or energy. Open-Meteo model coverage and free service limits can change; Phase A2 will verify them before requests.

## Sources used to establish data timing and API scope

- Open-Meteo Historical Weather API: https://open-meteo.com/en/docs/historical-weather-api
- Open-Meteo Historical Forecast API: https://open-meteo.com/en/docs/historical-forecast-api
- Open-Meteo Previous Runs API: https://open-meteo.com/en/docs/previous-runs-api
- Open-Meteo Weather Forecast API: https://open-meteo.com/en/docs
- Open-Meteo Open Data model table: https://github.com/open-meteo/open-data
- ECMWF/Copernicus ERA5 dataset: https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels
