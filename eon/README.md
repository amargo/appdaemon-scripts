# EON

## About

Magyar E.ON távleolvasási portálon keresztül jövő adatokat lehet Home Assistant rendszernek tovább küldeni
Szabadon tovább fejleszthető, 1-2 óra alatt készült el ezért nagy hibakezelések és szofisztikált feladatok megoldására nem alkalmas.

# Requirements

Olyan GSM-es óra, amit küldi az adatokat a szolgáltató felé.
E.ON távleolvasási portálján érvényes regisztráció: https://energia.eon-hungaria.hu/W1000
Érvényes POD elérés után egy munkaterületet kell létrehozni, amin csak az 1.8.0 és 2.8.0 szerepeljen:
<p align="center">    
        <img src="https://github.com/amargo/eon-mqtt/raw/master/img/eon-workarea.PNG" alt="eon-mqtt">
    <br>
</p>

Továbbá két Id-t kellett még megtudnom ezeket postman-os vizsgálatok során vettem észre, a reportId és a hyphen (ami nem tudom mi célt szolgál), de ezeket is át kell adni.
<p align="center">    
        <img src="https://github.com/amargo/eon-mqtt/raw/master/img/E.ON.PNG" alt="eon-mqtt">
    <br>
</p>

Chrome-ban login előtt egy F12 és a Network tabon látszódni fog a reportId és a kötőjel (vagy aláhúzás). 
<p align="center">    
        <img src="https://github.com/amargo/eon-mqtt/raw/master/img/eon_reportId_hyphen.PNG" alt="eon-mqtt">
    <br>
</p>

# Installation

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
  dependencies: globals
```
