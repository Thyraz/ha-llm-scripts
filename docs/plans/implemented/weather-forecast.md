# Weather Forecast Plan

Status: implemented in repo and validated in Home Assistant.

This plan defines the first read-only Weather Forecast LLM Tool. The supplied
external blueprint is background only; implementation should follow this repo's
LLM Tool Script, Python Helper, scalar parameter, and structured response
patterns.

Source checked: https://www.home-assistant.io/actions/weather.get_forecasts/

## Purpose

Weather Forecast lets an Assistant read Home Assistant weather forecasts for a
requested local time range. It should help small Assistants answer concise
weather questions without over-reporting low-value forecast attributes or
misstating weekdays.

## Current decisions

- Tool name: Weather Forecast.
- Script ID: `llmtool_weather_forecast`.
- Entity after reload: `script.llmtool_weather_forecast`.
- Python action: `python_script.llmtool_weather_forecast`.
- Weather Forecast v1 reads forecasts only.
- Weather Forecast uses Home Assistant `weather.get_forecasts`.
- Supported Home Assistant forecast types:
  - `daily`
  - `hourly`
- Do not expose `twice_daily` in v1.
- Public parameters:
  - `weather_entity_id`
  - `forecast_type`
  - `start_time`
  - `end_time`
  - `verbosity`
  - `limit`
- `weather_entity_id` is required.
- `weather_entity_id` must be an exact Home Assistant `weather.*` entity ID.
- If the Assistant does not know the weather entity ID, it should use Entity
  Index first.
- No default weather entity in v1.
- Unknown, empty, or non-weather entity IDs return a soft validation failure.
- If `weather_entity_id` is empty, the soft failure should include
  `available_weather_entity_ids` from Home Assistant state when possible.
- Weather Forecast never chooses a weather entity on the Assistant's behalf.
- Dates are local Home Assistant times.
- Date input format is exactly `YYYY-MM-DD HH:MM:SS`.
- Relative time text, timezone suffixes, dates without seconds, and ISO `T`
  separators are invalid.
- For `forecast_type=daily`, `start_time` and `end_time` must both use
  `00:00:00`.
- `forecast_type=daily` requires at least one full day.
- Partial-day weather requests must use `forecast_type=hourly`.
- `forecast_type=hourly` may cover multi-day ranges.
- Hourly range length is limited by `limit` and by provider data.
- `start_time` is inclusive.
- `end_time` is exclusive.
- Include forecast rows where `start_time <= row datetime < end_time`.
- For daily forecast rows, compare the local day start against the requested
  Weather Forecast Time Range.
- Do not accept a weekday input.
- Returned Weather Forecast days include `weekday`.
- Tool descriptions should tell the Assistant to trust returned weekdays, not
  its own date calculation.
- `verbosity` controls forecast detail.
- `verbosity` values:
  - `overview`
  - `detailed`
- Empty `verbosity` means `overview`.
- Tool descriptions should tell the Assistant to use `overview` for normal
  weather reports and `detailed` only when it needs specific forecast
  attributes.
- For `forecast_type=hourly`, group returned hourly rows by local date:
  - `data.days[].date`
  - `data.days[].weekday`
  - `data.days[].periods[]`
- For `forecast_type=daily`, return one Weather Forecast day per matching
  daily row.
- Overview daily baseline fields:
  - `date`
  - `weekday`
  - `condition`
  - `temperature` when available
  - `templow` when available
- Overview hourly period baseline fields:
  - `datetime`
  - `time`
  - `condition`
  - `temperature` when available
- In overview, include precipitation fields when at least one is true:
  - `precipitation >= 0.1`
  - `precipitation_probability >= 30`
  - `condition` is `rainy`, `pouring`, `snowy`, `snowy-rainy`, `hail`, or
    `lightning-rainy`
- Use Home Assistant's `precipitation` field name, not rain amount.
- In overview, include wind fields when at least one is true:
  - `wind_speed >= 30 km/h`
  - `wind_gust_speed >= 45 km/h`
  - `condition` is `windy` or `windy-variant`
- Convert wind thresholds internally for `m/s` and `mph` providers.
- Keep returned wind values in Home Assistant's original unit.
- Include `wind_bearing` in overview only when wind is reported.
- Overview omits:
  - `apparent_temperature`
  - `cloud_coverage`
  - `dew_point`
  - `humidity`
  - `pressure`
  - `uv_index`
- `verbosity=detailed` returns every supported available Home Assistant
  forecast field:
  - `datetime`
  - `date`
  - `weekday`
  - `time`
  - `condition`
  - `temperature`
  - `templow`
  - `apparent_temperature`
  - `dew_point`
  - `humidity`
  - `cloud_coverage`
  - `precipitation`
  - `precipitation_probability`
  - `pressure`
  - `uv_index`
  - `wind_bearing`
  - `wind_gust_speed`
  - `wind_speed`
  - `is_daytime`
- Unknown provider-specific fields are omitted.
- If Home Assistant returns forecast data but no rows match the Weather
  Forecast Time Range, return a soft failure:
  `No forecast rows found for requested Weather Forecast Time Range.`
- Empty results include requested range and `forecast_type` in `meta`.
- `limit` is optional.
- Empty `limit` uses 24.
- Maximum `limit` is 168.
- `limit` caps forecast rows, not Weather Forecast days.
- Capped responses remain successful, set `meta.truncated: true`, add
  `data.truncation`, and make `answer` warn about truncation.
- `answer` is count-only, for example `Found 2 forecast days.` or
  `Found 6 forecast periods.`
- Weather Forecast does not generate a human weather summary inside `answer`.
- The Assistant should compose the user-facing weather report from structured
  `data`.
- No ADR yet. The tool follows existing LLM Tool patterns and the decisions are
  cheap to change before implementation.

## Tool contract sketch

Overview daily response:

```yaml
success: true
answer: "Found 2 forecast days."
data:
  days:
    - date: "2026-07-25"
      weekday: Saturday
      condition: rainy
      temperature: 22
      templow: 16
      precipitation_probability: 70
      precipitation: 3.2
    - date: "2026-07-26"
      weekday: Sunday
      condition: partlycloudy
      temperature: 24
      templow: 17
meta:
  tool: llmtool_weather_forecast
  weather_entity_id: weather.home
  forecast_type: daily
  start_time: "2026-07-25 00:00:00"
  end_time: "2026-07-27 00:00:00"
  verbosity: overview
  count: 2
  total: 2
  limit: 24
```

Overview hourly response:

```yaml
success: true
answer: "Found 6 forecast periods."
data:
  days:
    - date: "2026-07-24"
      weekday: Friday
      periods:
        - datetime: "2026-07-24 18:00:00"
          time: "18:00:00"
          condition: rainy
          temperature: 21
          precipitation_probability: 60
        - datetime: "2026-07-24 19:00:00"
          time: "19:00:00"
          condition: cloudy
          temperature: 20
meta:
  tool: llmtool_weather_forecast
  weather_entity_id: weather.home
  forecast_type: hourly
  start_time: "2026-07-24 18:00:00"
  end_time: "2026-07-25 00:00:00"
  verbosity: overview
  count: 6
  total: 6
  limit: 24
```

## README snippet status

- README now adds Weather Forecast to the status list.
- README now includes installation exposure notes for:
  - `script.llmtool_weather_forecast`
  - `python_script.llmtool_weather_forecast`
- README now includes a usage section with daily and hourly examples.
- README now adds Weather Forecast to the Prompt overview.
- Prompt overview says:
  - use Weather Forecast for weather forecast questions
  - use Entity Index first if weather entity ID is unknown
  - use `overview` for normal weather reports
  - use `detailed` only when a specific forecast attribute is needed
  - trust returned `weekday`

## Validation needs

- Validate YAML configuration.
- Confirm `script.llmtool_weather_forecast` exists.
- Confirm fields appear in Developer Tools -> Actions.
- Run daily overview request.
- Run hourly overview request.
- Run detailed request.
- Check weekday output for known dates.
- Check precipitation threshold behavior.
- Check wind threshold behavior.
- Check truncation behavior.
- Expose the script to Assist.
- Ask the Assistant to use it.
- Inspect Conversation and Script traces.

## Unresolved questions

- None.
