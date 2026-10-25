# Open-Meteo data acquisition plan

Documentation checked 2026-10-25. This project uses the free, non-commercial endpoints only, with attribution to Open-Meteo and its CC BY 4.0 data sources. Do not use `customer-api.open-meteo.com`, API keys, or paid endpoints.

## Verified endpoints and parameters

| Dataset | Endpoint | Intended use / truth |
|---|---|---|
| Historical Weather API | `https://archive-api.open-meteo.com/v1/archive` | Pin `models=era5`; train predictors and use `temperature_2m` at t+1 as the reanalysis reference target. This is a 0.25-degree reanalysis grid-cell estimate, not a station observation. |
| Historical Forecast API | `https://historical-forecast-api.open-meteo.com/v1/forecast` | Archived forecast products in the same response format as live Forecast API. Use as operational-style forecast input data and potential alternative-model evidence; not observation truth. Archive coverage starts around 2021/2022 and each run's initial hours are stitched to a continuous series. |
| Previous Runs API | `https://previous-runs-api.open-meteo.com/v1/forecast` | Alternative-model forecast values at fixed day-ahead offsets. These are forecasts, not truth; record lead-time suffixes and verify support before choosing one for disagreement signals. |
| Forecast API | `https://api.open-meteo.com/v1/forecast` | Live-serving inputs with `past_days` / forecast horizon; model output is a forecast and never ground truth. |

The requested hourly names are `temperature_2m`, `relative_humidity_2m`, `dew_point_2m`, `pressure_msl`, `surface_pressure`, `cloud_cover`, `wind_speed_10m`, `wind_direction_10m`, `precipitation`, and `shortwave_radiation`. The API uses `latitude`, `longitude`, `hourly`, `start_date`, `end_date`, `timezone`, `temperature_unit`, `wind_speed_unit`, and `precipitation_unit`; exact response units are saved from `hourly_units`. Requests use Chennai coordinates `(13.0827, 80.2707)`, UTC, Celsius, m/s, and mm. Historical Weather supports explicit `models=era5`; forecast endpoints expose `models` for selecting one or more model IDs.

## Chennai model candidates

Open-Meteo's current model table identifies “everywhere else” (including Chennai) as global-model coverage only. Current global products in the documented forecast/archive selectors include ECMWF IFS HRES / IFS 0.25°, NOAA NCEP GFS, DWD ICON Global, JMA GSM, KMA GDPS, Canadian GEM Global, BOM ACCESS-G, CMA GRAPES Global, NCEP AIGFS and HGEFS, and UKMO Global. The corresponding current Forecast API model identifiers include `ecmwf_ifs`, `ecmwf_ifs025`, `ncep_gfs_global`, `ncep_gfs_seamless`, `icon_global`, `jma_gsm`, `kma_gdps`, `cmc_gem_gdps`, `bom_access_global`, `cma_grapes_global`, `ncep_aigfs025`, `ncep_hgefs025_ensemble_mean`, and `ukmo_global_deterministic_10km`. The exact set that can be selected from the Historical Forecast / Previous Runs archives at Chennai is not assumed from this general list; it must pass the live one-week model smoke check and have the required temperature variable.

Regional offerings such as HRRR, NBM, NAM, ICON-EU/D2, JMA MSM, and Europe-only models are not valid Chennai alternatives. `best_match` is not used as an independent model-disagreement stream because it blends model outputs and can change composition over time.

## Free limits and call accounting

The free API is non-commercial and currently documents 600 calls/minute, 5,000/hour, and 10,000/day. Open-Meteo counts requests extending beyond 10 weather variables or 14 days as multiple API calls; its examples show 15 variables over 14 days as 1.5 calls and 4 weeks as 3 calls. Acquisition therefore slices requests into no more than 14 days and uses at most 10 hourly variables. The downloader reports actual HTTP request count separately from estimated call units. Current API-call limits and billing definitions must be rechecked before any later large acquisition.

## Cache, immutability, and validation

`scripts/fetch_open_meteo.py` writes raw JSON plus a SHA-256 manifest beneath ignored `data/raw/open_meteo/<source>/` paths. It never overwrites a complete cached pair, refuses partial pairs, verifies the checksum on cache reads, retries HTTP 429 and 5xx with bounded backoff, sleeps between network requests, and validates response structure, expected row count, time continuity/range, array lengths, units, finite numeric values, and null counts. Each manifest has the same schema across sources and records request URL/parameters, source, model, timestamps, HTTP status, estimated calls, raw bytes, row metadata, units, null counts, and SHA-256.

The first live acquisition is limited to a one-week smoke interval. No longer-range download should start until that output is inspected. After smoke approval, use no more than 14-day chunks. Keep an acquisition ledger with HTTP calls and estimated billable call units; the historical archive request count will be estimated from the actual chunks and model identifiers used.

## One-week smoke result (2026-10-25)

Interval: 2026-10-11 00:00 through 2026-10-17 23:00 UTC, Chennai requested coordinates. The API returned its nearest grid cell at latitude 13.0, longitude 80.25 (not a station). Both datasets reported timezone `GMT` and UTC offset 0.

| Source | Selected model | HTTP status | Rows | Variables | Nulls | Temperature range | Estimated calls |
|---|---|---:|---:|---:|---:|---:|---:|
| Historical Weather | `era5` | 200 | 168 | 10 requested | 0 | 25.3–32.8 °C | 1 |
| Historical Forecast | `ncep_gfs_global` | 200 | 168 | `temperature_2m` | 0 | 24.6–34.0 °C | 1 |
| Historical Forecast | `ecmwf_ifs025` | 200 | 168 | `temperature_2m` | 0 | see saved raw response | 1 |

Raw SHA-256 values: ERA5 `40afa227487f7ea63c9f73fee87765afcc7ee43be57bd5becf79703d8a32848a`; GFS `e9024733a4d69c90b0d14d1fe19b0289ac5ce7805073b2dde32643b8a8d4b2a8`; ECMWF `b84ec889f1a9acb1a56e23eee31504c3ad2237b11f4b7e34d1060e91dd901549`. This smoke validates the endpoint shapes and selected model access; the one-week forecast and reanalysis ranges are descriptive, not a forecast skill comparison. The three successful HTTP requests used three estimated API call units total. Raw files and per-file manifests remain in the ignored local `data/raw/open_meteo/` cache.

## Sources

- Historical Weather API: https://open-meteo.com/en/docs/historical-weather-api
- Historical Forecast API: https://open-meteo.com/en/docs/historical-forecast-api
- Previous Runs API: https://open-meteo.com/en/docs/previous-runs-api
- Forecast API and model coverage: https://open-meteo.com/en/docs
- Current Forecast API parameter/model schema: https://raw.githubusercontent.com/open-meteo/open-meteo/main/openapi/forecast.yml
- Free usage limits and call accounting: https://open-meteo.com/en/pricing and https://open-meteo.com/en/terms
- ERA5 latency: https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels
