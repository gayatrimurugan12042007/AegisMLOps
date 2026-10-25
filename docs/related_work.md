# Related work and contribution boundary

Research review for AegisMLOps, checked 2026-10-25. The study is an applied, single-location replay evaluation. It does not claim a new drift detector or a universally optimal retraining method.

## Drift and monitoring

Data and concept drift are distinct. A change in the marginal input distribution can be detected without labels, but it does not establish that predictive risk increased. Label-based monitoring measures consequences for the model, but depends on labels being available. Sequential methods such as ADWIN provide an adaptive window for detecting changes in a stream; Page-Hinkley and CUSUM are cumulative change detectors. The experiment combines simple, inspectable PSI/KS feature monitoring with delayed absolute-error monitoring and measures their false triggers and missed events under controlled scenarios. These are established techniques, not novel contributions.

## Retraining as a cost-sensitive decision

Mahadevan and Mathioudakis formalize the trade-off between staleness and retraining cost and propose CARA, an online cost-aware retraining algorithm. Therefore AegisMLOps will not describe “cost-aware retraining” itself as novel. The narrow empirical question here is whether a simple, auditable policy using marginal drift, delayed model error, and forecast/model disagreement offers a useful cost/error trade-off for one-hour temperature prediction at Chennai under the particular replay and label-delay assumptions. It will be compared to periodic, single-signal, never-retrain, and oracle policies.

## Delayed labels

Delayed labels are a recognized streaming-learning setting. Plasse and Adams provide a taxonomy of delayed labeling and a framework for incorporating delayed labels in temporally evolving streams; Cerqueira et al. study how evaluation conclusions can depend on label delay and model evolution. Accordingly, this protocol models feedback availability explicitly at 0 hours, 24 hours, and 120 hours (approximately five days). The 120-hour case is motivated by the current ERA5 delay, not treated as a universal observation delay. Because ERA5 is gridded reanalysis rather than a station observation, the evaluation is a proxy study rather than live ground-truth validation.

## Unlabeled and disagreement signals

Unlabeled distributional tests and model uncertainty have been studied as ways to signal potential change before labels arrive. For example, Sethi and Kantardzic study reliable concept-change detection from unlabeled streams with margin-density monitoring. Ensemble/tree spread and disagreement among alternative weather forecasts are related warning signals, but disagreement can rise because two valid weather models differ even when the deployed model's expected loss has not worsened. AegisMLOps will treat these signals only as candidate evidence, measure false triggers on no-drift periods, and make no claim that disagreement identifies concept drift by itself.

## Weather-data implications

Open-Meteo distinguishes historical reanalysis from archived forecasts. ERA5 is a 0.25-degree hourly reanalysis updated daily with about a five-day delay; it is a grid-cell estimate, not a Chennai station reading. The Historical Forecast API archives forecast model outputs from around 2022 and stitches the first hours of each run into a continuous series. Forecast inputs and ERA5 targets therefore have different provenance and can introduce training-serving skew. This is both a limitation and an explicit test condition, not evidence of real station-level model performance.

## Contribution statement

The defensible contribution, if supported by saved results, is a reproducible, cost-constrained replay comparison of a transparent multi-signal retraining rule against specified baselines for one-hour Chennai temperature prediction, including explicit label delays, synthetic covariate and concept shifts, forecast disagreement, and an estimated retraining-compute cost. The work will report the settings in which the rule helps and fails. It will not claim novelty for PSI, KS, CUSUM, Page-Hinkley, disagreement monitoring, delayed-label learning, or cost-aware retraining, and it will not generalize beyond the one location and data sources tested.

## References

1. Mahadevan, A., & Mathioudakis, M. (2024). “Cost-aware retraining for machine learning.” *Knowledge-Based Systems*, 293, 111610. https://doi.org/10.1016/j.knosys.2024.111610
2. Ditzler, G., Roveri, M., Alippi, C., & Polikar, R. (2015). “Learning in Nonstationary Environments: A Survey.” *IEEE Computational Intelligence Magazine*, 10(4), 12–25. https://doi.org/10.1109/MCI.2015.2471196
3. Plasse, J., & Adams, N. (2016). “Handling delayed labels in temporally evolving data streams.” *2016 IEEE International Conference on Big Data*, 2416–2424. https://doi.org/10.1109/BigData.2016.7840877
4. Grzenda, M., Gomes, H. M., & Bifet, A. (2020). “[Delayed labelling evaluation for data streams](https://doi.org/10.1007/s10618-019-00654-y).” *Data Mining and Knowledge Discovery*, 34, 1237–1266. https://doi.org/10.1007/s10618-019-00654-y
5. Žliobaitė, I., Bifet, A., Pfahringer, B., & Holmes, G. (2014). “Active Learning with Drifting Streaming Data.” *IEEE Transactions on Neural Networks and Learning Systems*, 25(1), 27–39. https://doi.org/10.1109/TNNLS.2012.2236570
6. Bifet, A., & Gavaldà, R. (2007). “Learning from Time-Changing Data with Adaptive Windowing.” *Proceedings of the 2007 SIAM International Conference on Data Mining*, 443–448. https://doi.org/10.1137/1.9781611972771.42
7. Sethi, T. S., & Kantardzic, M. (2017). “On the reliable detection of concept drift from streaming unlabeled data.” *Expert Systems with Applications*, 82, 77–99. https://doi.org/10.1016/j.eswa.2017.04.008
8. Open-Meteo. “Historical Weather API,” “Historical Forecast API,” “Previous Runs API,” and “Weather Forecast API” documentation. https://open-meteo.com/en/docs/historical-weather-api ; https://open-meteo.com/en/docs/historical-forecast-api ; https://open-meteo.com/en/docs/previous-runs-api ; https://open-meteo.com/en/docs
9. ECMWF Copernicus Climate Change Service. “ERA5 hourly data on single levels from 1940 to present.” https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels

## Source verification notes

- Current Open-Meteo documentation states ERA5 is hourly at 0.25 degrees and updates daily with a five-day delay. The CDS documentation independently reports about five days of latency.
- The Historical Forecast API page states that the archive begins around 2022 and stitches the first few hours of successive runs.
- The current Forecast and Historical Forecast API documentation lists global model products including ECMWF IFS HRES / IFS 0.25°, CMA GRAPES Global, BOM ACCESS Global, NOAA GFS Global, NCEP AIGFS/HGEFS, JMA GSM, KMA GDPS, and DWD ICON Global. Their global coverage makes them candidate Chennai alternatives; regional offerings (for example HRRR, NBM, NAM, European or Korean limited-area models) are excluded unless the API explicitly returns Chennai coverage. Exact API model identifiers, variables, and coverage in each archive remain subject to the A2 endpoint smoke checks before acquisition.
