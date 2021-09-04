# amargo's Appdaemon Scripts

## About

This repository containing all of my Appdaemon application scripts.

## How to use

If you have never used Appdaemon before please you read the following tutorials:
[tutorial](https://appdaemon.readthedocs.io/en/latest/HASS_TUTORIAL.html)
[guide](https://appdaemon.readthedocs.io/en/latest/APPGUIDE.html)

## App list

* [EON](#eon)
* [Energy Usage](#normalized_energy_usage)

### EON

Are explained [here](eon/README.md)

```yaml
Eon:
  module: read_eon
  class: Eon
  eon_url: 'https://energia.eon-hungaria.hu/W1000'
  username: '<username>'
  password: '<password>'
  report_id: '<reportId>'
  chart_id: '<chartId>'
  last_reset: "2020-09-14T11:25:00+00:00" When E.ON reading of meters
  every_hour: 1
  hyphen: '<->'
  offset: -2
  host: '<database connection host>'
  username_db: '<username_db>'
  password_db: '<password_db>'
  database: '<database name>'
  1_8_0_sensor: sensor.eon_1_8_0_energy_total
  2_8_0_sensor: sensor.eon_2_8_0_energy_total
```
### Energy Usage

Are explained [here](normalized_energy_usage/README.md)

```yaml
normalized_energy_usage:
  class: NormalizedEnergyUsage
  module: normalized_energy_usage
  host: '<database connection host>'
  username_db: '<username_db>'
  password_db: '<password_db>'
  database: '<database name>'
  offset: -2
  every_hour: 1
  1_8_0_sensor: sensor.eon_1_8_0_energy_total
  2_8_0_sensor: sensor.eon_2_8_0_energy_total
```
