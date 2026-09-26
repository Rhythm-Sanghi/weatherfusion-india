# WeatherFusion India data sources and permitted use

## Approved sources

WeatherFusion India uses only the sources below unless the project owner adds a new source to this document after verifying its permissions and terms.

### Approved final prototype scope

The approved prototype configuration is **Open-Meteo plus controlled demonstration data**. Open-Meteo is the only external live weather-data provider. No additional live source, credential, platform integration, or API key may be introduced without separate project-owner approval.

Use the existing `https://api.open-meteo.com/v1/forecast` configuration and the free non-commercial tier only. Do not add an API key, paid subscription configuration, or any credential-backed fallback. If Open-Meteo is unavailable, return an explicit unavailable result or a clearly labelled cached response; never substitute controlled data and label it as live.

The demonstration must remain usable without external connectivity. It uses previously prepared local controlled reports and/or clearly labelled cached Open-Meteo observations. A network outage must never prevent the incident-management walkthrough from completing.

| Source | Approved use | Provenance required | Restrictions |
| --- | --- | --- | --- |
| NOAA Storm Events Database | Historical weather-event context and ML work only where the data supports the specific task | Original event and episode IDs, source filename, row reference, source URL, file hash, dataset version, download date when known, and NOAA attribution | Do not infer false-report, truthfulness, or duplicate-report labels. Do not treat `EPISODE_ID` as a verified duplicate label. |
| Open-Meteo | Live weather context for the non-commercial prototype, subject to its current limits and terms | Request URL, response timestamp, requested coordinates/variables, source mode (`live` or `cached`), cache age, provider name, and licence/attribution | Respect non-commercial free-tier limits. Do not describe forecast/current-model output as independently verified ground truth. |
| Controlled demonstration data | Development, UI demonstration, workflow tests, and offline rehearsal | Stable fixture ID, `origin_mode=CONTROLLED_DEMO`, scenario version, creation date, and an explicit synthetic label | Never present as a genuine historical incident or use it to report real-world model performance. |

Restricted sources are out of scope: scraped or restricted social-media platforms, copyrighted news content, and third-party websites without confirmed permission.

## Provenance rules

Every event must retain exactly one visible origin category:

- `NOAA_HISTORICAL`: original NOAA record and its source provenance.
- `OPEN_METEO_LIVE`: response obtained during the current API request.
- `OPEN_METEO_CACHED`: prior Open-Meteo response reused after a live request was unavailable or intentionally bypassed.
- `CONTROLLED_DEMO`: synthetic scenario or fixture created for the prototype.

The UI must show the origin category in Event Detail and Incident Brief. Cached observations must include their retrieval time and must not be represented as current live data. Controlled records must use visible language such as “Controlled demo report”; labels must not merely appear in hidden metadata.

The database and API must preserve the same distinction. At minimum, event metadata must retain `origin_mode`, source identity, source reference, and the capture/retrieval timestamp. Cached Open-Meteo records must additionally retain the original retrieval timestamp and cache age. NOAA-derived records must retain NOAA event ID, episode ID when supplied, source-file identifier, and dataset provenance.

## ML-use rules

NOAA `EVENT_TYPE` can be used only as the source label for an event-type task when the input fields, class taxonomy, and leakage-resistant split are appropriate. Precision, recall, and F1 require a legitimate ground-truth label and held-out test set.

The supplied 1950–1959 NOAA files have no narratives and no episode IDs. They are therefore not used to train or evaluate the WeatherFusion report-text classifier, duplicate classifier, or truthfulness classifier. See [NOAA Storm Events dataset assessment](../ml/docs/NOAA_STORM_EVENTS_DATASET.md).

NOAA may be used for independently evaluated ML tasks only when a selected collection has suitable genuine inputs, legitimate labels, and a leakage-resistant held-out split. It is historical context, not a live operational source in this approved prototype scope.

Synthetic records can test ingestion, UI state, scoring display, review, and audit functionality. They cannot be used to claim real-world ML accuracy, precision, recall, F1, or duplicate-detection performance.

## Required acknowledgments

### In project documentation

Use the following acknowledgments near the relevant source description:

> Historical storm-event records: NOAA National Centers for Environmental Information, Storm Events Database. Source records retain original NOAA identifiers and source-file provenance. https://www.ncei.noaa.gov/stormevents/

> Live weather context: Open-Meteo weather API. Data are used subject to Open-Meteo terms and CC BY 4.0 attribution requirements. https://open-meteo.com/en/terms

> Controlled demo reports are synthetic scenarios created for WeatherFusion India. They are not historical incidents and are not used as evidence of real-world model performance.

For a specific Open-Meteo model or downstream provider, add any model/provider acknowledgement that Open-Meteo requires for that endpoint before release.

### Presentation slide text

Add a final “Data sources and limitations” slide containing:

> **NOAA Storm Events Database** — historical U.S. storm records from NOAA/NCEI; used with retained provenance.
>
> **Open-Meteo** — live weather context for this non-commercial prototype; attribution required under CC BY 4.0. Live, cached, and controlled-demo data are labeled separately.
>
> **Controlled demo data** — synthetic workflow fixtures only; not real incidents or real-world ML evaluation evidence.
>
> The prototype uses automated evidence to prioritize human review. It does not use restricted social-media or news scraping, and it does not claim automated truth determination.

## Verification before adding a source

Before a new source is added, record its owner, URL, licence/terms, allowed project use, retrieval date, attribution wording, rate limits, retention constraints, and any required downstream-provider credits. Exclude the source until each item is verified.

## References

- NOAA NCEI, [Storm Events Database](https://www.ncei.noaa.gov/stormevents/), including its bulk-data access information.
- Open-Meteo, [Terms of Use](https://open-meteo.com/en/terms), including the free non-commercial tier and CC BY 4.0 data terms.
- Open-Meteo, [pricing and attribution information](https://open-meteo.com/en/pricing), which notes that attribution and indication of modifications are required for data under CC BY 4.0.
