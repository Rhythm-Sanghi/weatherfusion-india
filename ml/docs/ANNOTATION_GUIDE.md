# Annotation guide v1

Annotators label what a report's text describes. A classification label does not verify that an incident occurred.

Use `WEATHER_RELEVANT` only for described weather events. Select one supported primary type: HEAVY_RAINFALL, FLOOD, THUNDERSTORM, HEATWAVE, FOG, DUST_STORM, STRONG_WIND, or UNKNOWN. Use `UNCERTAIN` and no type when context is inadequate. Use `NOT_WEATHER_RELEVANT` and no type for unrelated content.

Record language and controlled source provenance. Group reports about the same incident with `incident_group_id`; use `duplicate_group_id` only for copied or identical reports. Forecasts, historical accounts, rumours, reposts, sarcasm, and uncertain times or locations require notes. Annotators must record disagreement in notes. Synthetic fixtures are never training data.
