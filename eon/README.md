# E.ON – Távleolvasás integráció Home Assistant

## About

Magyar E.ON távleolvasási portálon keresztül jövő adatokat lehet Home Assistant rendszernek tovább küldeni
Szabadon tovább fejleszthető, 1-2 óra alatt készült el ezért nagy hibakezelések és szofisztikált feladatok megoldására nem alkalmas.

# Követelmények

* Olyan GSM-es óra, amit küldi az adatokat a szolgáltató felé.
* E.ON távleolvasási portálján érvényes regisztráció: https://energia.eon-hungaria.hu/W1000
* MariaDB Add-On integráció (Bővítménybolt, https://github.com/home-assistant/addons/blob/master/mariadb/DOCS.md)
* AppDaemon Add-On integráció (Bővítménybolt, https://github.com/hassio-addons/addon-appdaemon)
* Érvényes POD elérés után egy munkaterületet kell létrehozni, amin csak az 1.8.0 és 2.8.0 szerepeljen:
<p align="center">    
        <img src="https://github.com/amargo/eon-mqtt/raw/master/img/eon-workarea.PNG" alt="eon-mqtt">
    <br>
</p>

# Lépések
* Regisztrálni az https://energia.eon-hungaria.hu/W1000 oldalon és amint az EON jóváhagyja a regisztrációt akkor, a regisztrációkor használt belépési adatokat tudjuk használni az integrációnál
* Amint megkaptuk a visszaigazolást akkor létre kell hozni ezeket a jelentéseket:
  * Jelentés 1 : hét nézet 1.8 – 2.8 (2.8 a visszatermelés napelem esetén)
  * Jelentés 2: - A /+ A  
  amikor ez meg van , belépés előtt a chrome böngészőben (F12) megnyom és a Network fül kiválaszt ahogy a képen is látható …. legörget ezekhez a fülekhez és dupla kattintással ellenőrizzük hogy melyik ID a ReportID és melyik a ChartID, amir később a HA integrációnál szükséges lesz a ead_eon.yaml file konfigurálásához.
  * ReportID ( a kitakart zónában megjelenő 6 jegyű azonosító amire szükség lesz, ez ami az 1.8.-2.8 napi fogyasztás / visszatermelést mutatja a villanyóránkon ).
    <p align="center">    
            <img src="https://github.com/amargo/appdeamon-scripts/eon/raw/master/img/eon_jelentes_1_2.jpg" alt="eon-mqtt">
        <br>
    </p>
  * chartID (pirossal jelölt) + hypen (sárgával jelölt) -> ( a kitakart zónában megjelenő 6 jegyű azonosító, amire szükség lesz, ez ami az aktuális betermelést / fogyasztást 15 percenként frissíti az EON oldala a távleolvasási funkcióval a web oldalon).
    <p align="center">    
            <img src="https://github.com/amargo/appdeamon-scripts/eon/raw/master/img/eon_jelentes.jpg" alt="eon-mqtt">
        <br>
    </p>

* MariaDB integracio (Add-ON / bővítményboltbol)
    <p align="center">    
            <img src="https://github.com/amargo/appdeamon-scripts/eon/raw/master/img/mariaDB.jpg" alt="eon-mqtt">
            <img src="https://github.com/amargo/appdeamon-scripts/eon/raw/master/img/mariaDB_config.jpg" alt="eon-mqtt">            
        <br>
    </p>
  Telepítés utan a config / konfiguráció fülön megadjuk a következő adatokat

    * TOVÁBBI OPCIOK FÜLÖN:
      * ADATBAZIS NEVE: homeassistant (ebben a példában)
      * Jelszó / Password: homeassistant (ebben a példában, ha nem adunk meg jelszót nem lehet menteni a konfigurációt)
    * HÁLOZAT FÜLÖN:
      * Port : 3306 (ezt kell megadni)
  * FileEditorral vagy file kezelőben szerkesztésre megnyitjuk a configuration.yaml file-t, dokumentáció szerint beillesztjük pl.: 
  * 
    ```
    recorder:
    db_url: mysql://homeassistant:homeassistant@core-mariadb/homeassistant?charset=utf8mb4
    ```
    a fentebbi példa jelszó / adatbázis név stb. van itt is megadva
      <p align="center">    
              <img src="https://github.com/amargo/appdeamon-scripts/eon/raw/master/img/ha_recorder.jpg" alt="eon-mqtt">
          <br>
      </p>
  <mark>
  fejlesztői eszközök -> konfiguráció ellenőrzése -> HA újraindítása
  </mark>
  
  * HA ujraindulasa utan:
    Bővítmények -> az Info fülre kattintva -> inditsuk el a MariDB-t a LOG fülre kattintva megnezhetjük / ellenőrizhetjük hogy a MariaDB rendben lefutott
      <p align="center">    
              <img src="https://github.com/amargo/appdeamon-scripts/eon/raw/master/img/mariaDB_log.jpg" alt="eon-mqtt">
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
