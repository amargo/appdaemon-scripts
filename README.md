# amargo's Appdaemon Scripts

## About

This repository containing all of my Appdaemon application scripts.

## How to use

If you have never used Appdaemon before please you read the following tutorials:
[tutorial](https://appdaemon.readthedocs.io/en/latest/TUTORIAL.html)
[guide](https://appdaemon.readthedocs.io/en/latest/APPGUIDE.html)

## App list

* [EON](#eon)

### EON

Are explained [here](eon/README.md)

```yaml
Eon:
  module: read_eon
  class: Eon
  eon_url: 'https://energia.eon-hungaria.hu/W1000'
  username: '<felhasználói azonosítód>'
  password: '<felhasználói jelszavad>'
  report_id: '<reportId>'
  every_hour: 6
  hyphen: '<->'
  offset: 0
  class: Eon
  de
