# E.ON – Távleolvasás integráció Home Assistant

## About

Ezzel az appdaemon scripttel a magyar E.ON távleolvasási portálon keresztül jövő adatokat lehet Home Assistant rendszernek továbbküldeni.
Szabadon továbbfejleszthető, 1-2 óra alatt készült el ezért nagy hibakezelések és szofisztikált feladatok megoldására nem alkalmas.

# Követelmények

* Olyan GSM-es oda-vissza mérő (ad-vesz) villanyóra, ami küldi az adatokat a szolgáltató felé.
* E.ON távleolvasási portálján érvényes regisztráció: https://energia.eon-hungaria.hu/W1000
* MariaDB Add-On integráció (Bővítménybolt, https://github.com/home-assistant/addons/blob/master/mariadb/DOCS.md)
* AppDaemon Add-On integráció (Bővítménybolt, https://github.com/hassio-addons/addon-appdaemon)
* Érvényes POD

# Lépések
* Regisztrálni az https://energia.eon-hungaria.hu/W1000 oldalon, és amint az EON jóváhagyja a regisztrációt, a regisztrációkor használt belépési adatokat tudjuk használni az integrációnál.
* Amint megkaptuk a visszaigazolást akkor létre kell hozni ezeket a jelentéseket:
  * Jelentés 1 : hét nézet 1.8 – 2.8 (2.8 a visszatermelés napelem esetén)
  * Jelentés 2: - A /+ A  
  amikor ez meg van belépés előtt a chrome böngészőben (F12) megnyom és a Network fül kiválaszt ahogy a képen is látható ... legörgetni ezekhez a fülekhez és dupla kattintással ellenőrizzük hogy melyik ID a ReportID és melyik a ChartID, amit később a HA integrációnál szükséges lesz a ead_eon.yaml file konfigurálásához.
  * ReportID ( a kitakart zónában megjelenő 6 jegyű azonosító amire szükség lesz, ez ami az 1.8.-2.8 napi fogyasztás / visszatermelést mutatja a villanyóránkon ).
    <p align="center">    
            <img src="https://github.com/amargo/appdeamon-scripts/raw/main/eon/img/eon_jelentes_1_2.jpg" alt="eon-mqtt">
        <br>
    </p>
  * chartID (pirossal jelölt) + hypen (sárgával jelölt) -> ( a kitakart zónában megjelenő 6 jegyű azonosító, amire szükség lesz, ez ami az aktuális betermelést / fogyasztást 15 percenként frissíti az EON oldala a távleolvasási funkcióval a web oldalon).
    <p align="center">    
            <img src="https://github.com/amargo/appdeamon-scripts/raw/main/eon/img/eon_jelentes.jpg" alt="eon-mqtt">
        <br>
    </p>

# MariaDB integració (Add-ON)

  <p align="center">    
          <img src="https://github.com/amargo/appdeamon-scripts/raw/main/eon/img/mariaDB.jpg" alt="eon-mqtt">
          <img src="https://github.com/amargo/appdeamon-scripts/raw/main/eon/img/mariaDB_config.jpg" alt="eon-mqtt">
      <br>
  </p>

* Telepítés utan a config / konfiguráció fülön megadjuk a következő adatokat
  * TOVÁBBI OPCIOK FÜLÖN:
    * ADATBAZIS NEVE: homeassistant (ebben a példában)
    * Jelszó / Password: homeassistant (ebben a példában, ha nem adunk meg jelszót nem lehet menteni a konfigurációt)
  * HÁLOZAT FÜLÖN:
    * Port : 3306 (ezt kell megadni)
  * FileEditorral vagy file kezelőben szerkesztésre megnyitjuk a configuration.yaml file-t, dokumentáció szerint beillesztjük pl.: 
    ```
    recorder:
    db_url: mysql://homeassistant:homeassistant@core-mariadb/homeassistant?charset=utf8mb4
    ```
    a fentebbi példa jelszó / adatbázis név stb. van itt is megadva
      <p align="center">    
              <img src="https://github.com/amargo/appdeamon-scripts/raw/main/eon/img/ha_recorder.jpg" alt="eon-mqtt">
          <br>
      </p>

  <mark>
  fejlesztői eszközök -> konfiguráció ellenőrzése -> HA újraindítása
  </mark>
  
* HA újraindulasa utan:
  Bővítmények -> az Info fülre kattintva -> inditsuk el a MariDB-t a LOG fülre kattintva megnézhetjük / ellenőrizhetjük hogy a MariaDB rendben lefutott
    <p align="center">    
            <img src="https://github.com/amargo/appdeamon-scripts/raw/main/eon/img/mariaDB_log.jpg" alt="eon-mqtt">
        <br>
    </p>    

# AppDaemon integració (Add-ON)

  <p align="center">    
          <img src="https://github.com/amargo/appdeamon-scripts/raw/main/eon/img/appdaemon.jpg" alt="eon-mqtt">
          <img src="https://github.com/amargo/appdeamon-scripts/raw/main/eon/img/appdaemon_config.jpg" alt="eon-mqtt">
      <br>
  </p>

* TOVÁBBI OPCIOK FÜLÖN:
  * Python packeges-nel következőket felvenni
    * requests
    * bs4
    * datetime
    * pymysql
  * HÁLOZAT FÜLÖN:
    * Port : 5050 (ezt kell megadni ha nem lenne megadva automatikusan)
* A github linkről letöltött .tar file-t kicsomagoljuk , és a Home Assistan config/AppDaemon/apps mappába bemásoljuk ezt egyszerűen meg tehetjük Samba share-t a Add-on ként feltesszük a HA-ba és mint meghajtókent lathatjuk a file kezelőben vagy VS Code Add-on-t használjuk.
* Először  csak a read_eon.yaml fontos, hogy lássuk maga az EON távolvasási portálról műküdik az adat olvasás... addig a normalized_energy_usage mappát nem is kell átmasolnunk csak a többit! Különben nem latjuk hogy az read_eon.yaml milyen hibaüzenetet ad és hogy jól fut-e a gépünkön.
* Következő lépésként text Editor segítségével beírjuk a read_eon.yaml file-be az alábbiakat:
  ```yaml
  Eon:
    module: read_eon
    class: ReadEon
    eon_user: '<username>'
    eon_password: '<password>'
    eon_report_id_180_280: '<reportId a jelentés 1-hez>'
    eon_report_id_pa_ma: '<reportId a jelentés 2-höz>'
    offset: -4
    run_daily_at: '07:30'

    db_host: '<database connection host>'
    db_user: '<database username>'
    db_password: '<database password>'
    db_name: '<database name>'
    sensor_1_8_0: sensor.eon_1_8_0_energy_total
    sensor_2_8_0: sensor.eon_2_8_0_energy_total
    positive_a_energy: sensor.eon_positive_a_energy_power
    negative_a_energy: sensor.eon_negative_a_energy_power
  ```
  Ez után azt kell látnunk hogy megjelenik az áttekintés fülön a HA-ban

* normalized_energy_usage.yaml -> konfigurálása:
  ```yaml
  normalized_energy_usage:
    class: NormalizedEnergyUsage
    module: normalized_energy_usage
    db_host: <database connection host>
    db_user: <username_db>
    db_password: <password_db>
    db_name: <database name>
    numdays: 4
    every_hour: 12
    run_daily_at: '07:40'
    sensor_1_8_0: sensor.eon_1_8_0_energy_total
    sensor_2_8_0: sensor.eon_2_8_0_energy_total
  ```  
# Végeredmény
<p align="center">    
        <img src="https://github.com/amargo/appdeamon-scripts/raw/main/eon/img/ha_energy.jpg" alt="eon-mqtt">
    <br>
</p>

# Végszó
Nagy köszönet Pintér Roland-nak a részletes dokumentáció elkészítésében :)
