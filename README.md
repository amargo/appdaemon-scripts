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

## Requirements 
* MariaDB [more information](https://github.com/home-assistant/addons/blob/master/mariadb/DOCS.md)

Are explained [here](eon/README.md)

```yaml
Eon:
  class: ReadEon
  module: read_eon
  eon_user: '<eon_username>'
  eon_password: '<eon_password>'
  eon_report_id_180_280: <reportId>
  eon_report_id_pa_ma: <reportId>  

  db_host: <database_host>
  db_user: <db_username>
  db_password: <db_password>
  db_name: <database_name>

  offset: -4
  run_daily_at: 07:30
  1_8_0_sensor: sensor.eon_1_8_0_energy_total
  2_8_0_sensor: sensor.eon_2_8_0_energy_total
  positive_a_energy: sensor.eon_positive_a_energy_power
  negative_a_energy: sensor.eon_negative_a_energy_power 
```
### Energy Usage

Are explained [here](normalized_energy_usage/README.md)

```yaml
normalized_energy_usage:
  class: NormalizedEnergyUsage
  module: normalized_energy_usage
  host: <database_connection_host>
  username: <username_db>
  password: <password_db>
  database: <database name>
  numdays: 4
  every_hour: 12
  run_daily_at: 07:30
  1_8_0_sensor: sensor.eon_1_8_0_energy_total
  2_8_0_sensor: sensor.eon_2_8_0_energy_total
```
