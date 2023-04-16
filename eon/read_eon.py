import appdaemon.plugins.hass.hassapi as hass
import datetime
import requests
import pytz
import pymysql.cursors

import json
from os.path import exists

from bs4 import BeautifulSoup
from pathlib import Path

EON_BASE_URL = 'https://energia.eon-hungaria.hu/W1000/'
EON_ACCOUNT_URL = f'{EON_BASE_URL}Account/Login'
EON_PROFILE_DATA_URL = f'{EON_BASE_URL}ProfileData/ProfileData'
__FILE = Path(__file__)
BASE_DIR = __FILE.parent

class ReadEon(hass.Hass):
    config = {}
    session = {}

    def initialize(self):
        self.config = self.args
        if 'run_daily_at' in self.config:
            runtime = datetime.datetime.strptime(self.config['run_daily_at'], '%H:%M').time()
        else:
            runtime = datetime.time(7, 30, 0)

        self.log(f"START - daily at {runtime}", level="INFO")
        self.run_daily(self.read_data, runtime)


    def get_verificationtoken(self, content):
        self.log("get verification token from E.ON portal", level="INFO")
        toke = content.find('input', {'name': '__RequestVerificationToken'})
        return toke.get('value')

    def read_data(self, kwargs):
        username = self.config['eon_user']
        password = self.config['eon_password']
        self.db_host = self.config['db_host']
        self.db_name = self.config['db_name']
        self.db_password = self.config['db_password']
        self.db_user = self.config['db_user']
        self.offset = self.config['offset']
        self.sensor_1_8_0 = self.config["sensor_1_8_0"]
        self.sensor_2_8_0 = self.config["sensor_2_8_0"]

        self.log("Starting E.ON reader", level="INFO")
        self.session = self.login(username, password)
        self.log("Start receiving data", level="INFO")
        eon_1_8_0_report, eon_2_8_0_report = self.get_report_data()
        self.log(f"Start receiving chart data", level="INFO")
        self.get_chart_data(eon_1_8_0_report, eon_2_8_0_report)
        self.log("END processing data", level="INFO")

    def get_chart_data(self, eon_1_8_0_report, eon_2_8_0_report):
        positive_a_energy = self.config["positive_a_energy"]
        negative_a_energy = self.config["negative_a_energy"]
        self.timezone = pytz.timezone("Europe/Budapest")
        self.eon_report_id_pa_ma = self.config["eon_report_id_pa_ma"]

        self.log(f"eon_1_8_0_report: {eon_1_8_0_report}", level="INFO")
        json_response_data= {}
        
        for eon_daily_time, eon_daily_value in eon_1_8_0_report.items():
            eon_daily_time_tmp = eon_daily_time.astimezone(tz=self.timezone)
            final_since_time = eon_daily_time_tmp + datetime.timedelta(minutes=14)
            final_until_time = (
                final_since_time
                + datetime.timedelta(hours=23)
                + datetime.timedelta(minutes=32)
            )
            
            eon_energy_pa_ma_file = f"{BASE_DIR}/eon_energy_pa_ma.json"
            if exists(eon_energy_pa_ma_file):
                json_response_data[eon_daily_time_tmp.strftime("%Y-%m-%d")] = json.load(open(eon_energy_pa_ma_file))
            else:
                json_response_data[eon_daily_time_tmp.strftime("%Y-%m-%d")] = self.get_data(
                    report_id=self.eon_report_id_pa_ma,
                    per_page_number=120,
                    since=final_since_time,
                    until=final_until_time,
                )

        self.report_180_280(
            data=json_response_data,
            idx=0,
            report_items=eon_1_8_0_report,
            a_energy=positive_a_energy,
            eon_sensor_entity_id=self.sensor_1_8_0,
            friendly_name="EON +A energy power",
            total_friendly_name="EON consumption energy total",
        )

        self.log(f"eon_2_8_0_report: {eon_2_8_0_report}", level="INFO")

        self.report_180_280(
            data=json_response_data,
            idx=1,
            report_items=eon_2_8_0_report,
            a_energy=negative_a_energy,
            eon_sensor_entity_id=self.sensor_2_8_0,
            friendly_name="EON -A energy power",
            total_friendly_name="EON export energy total",
        )

    def report_180_280(
        self,
        data,
        idx,
        report_items,
        a_energy,
        eon_sensor_entity_id,
        friendly_name,
        total_friendly_name,
    ):
        for eon_daily_time, eon_daily_value in report_items.items():
            eon_a = {}
            eon_a_total = {}
            eon_daily_time_tmp = eon_daily_time.astimezone(tz=self.timezone)
            json_response = data[eon_daily_time_tmp.strftime("%Y-%m-%d")]

            eon_sum_value = eon_daily_value
            for a in json_response[idx]["data"]:
                eon_sum_value = self.collect_chart_data(
                    a=a,
                    a_energy=a_energy,
                    eon_a=eon_a,
                    eon_report=report_items,
                    eon_a_total=eon_a_total,
                    eon_report_time=eon_daily_time,
                    eon_report_value=eon_sum_value,
                    eon_sensor_entity_id=eon_sensor_entity_id,
                    friendly_name=friendly_name,
                    total_friendly_name=total_friendly_name,
                )

            eon_sum_value = eon_daily_value
            for a in json_response[idx]["data"]:
                eon_sum_value = self.collect_chart_data(
                    a=a,
                    a_energy=a_energy,
                    eon_a=eon_a,
                    eon_report=report_items,
                    eon_a_total=eon_a_total,
                    eon_report_time=eon_daily_time,
                    eon_report_value=eon_sum_value,
                    eon_sensor_entity_id=eon_sensor_entity_id,
                    friendly_name=friendly_name,
                    total_friendly_name=total_friendly_name,
                )

            if len(eon_a_total) > 0:
                eon_a_total = {key: val for key, val in eon_a_total.items() if val != 0}
                self.normalize_eon_chart_data(eon_sensor_entity_id, eon_a_total)

            if len(eon_a) > 0:
                self.normalize_eon_chart_data(a_energy, eon_a)

    def collect_chart_data(self, a, a_energy, eon_a, eon_report, eon_a_total, eon_report_time, eon_report_value, eon_sensor_entity_id, friendly_name, total_friendly_name):
        eon_a_value = round(a['value'], 5)
        eon_a_time = datetime.datetime.strptime(
            a['time'], '%Y-%m-%dT%H:%M:%S').astimezone(tz=datetime.timezone.utc)
        extra_parameter = " AND JSON_CONTAINS(sa.shared_attrs, '\"" + eon_a_time.strftime(
            '%Y-%m-%d %H:%M:%S') + "\"', '$.last_changed')"
        eon_a[eon_a_time] = eon_a_value

        extra_parameter = " AND JSON_CONTAINS(sa.shared_attrs, '\"" + eon_a_time.strftime(
            '%Y-%m-%d %H:%M:%S') + "\"', '$.last_changed')"
        total_rows = self.get_states(eon_sensor_entity_id, extra_parameter)
        eon_sum_value = eon_report_value + eon_a_value
        eon_sum_value = round(eon_sum_value, 5)
        eon_report[eon_report_time] = eon_sum_value
        eon_a_total[eon_a_time] = eon_sum_value
        if len(total_rows) == 0 and eon_sum_value > 0:
            self.set_state(eon_sensor_entity_id, 
                           state=eon_sum_value, 
                           unit_of_measurement='kWh', 
                           attributes={
                               "state_class": "total_increasing", 
                               "last_changed": eon_a_time.strftime('%Y-%m-%d %H:%M:%S'), 
                               "unit_of_measurement": 'kWh',
                               "friendly_name": total_friendly_name, "device_class": "energy"})
            self.log(
                f"{eon_sensor_entity_id}: eon_sum_value is {str(eon_sum_value)}, eon_time: {eon_a_time.strftime('%Y-%m-%d %H:%M:%S')}", level="INFO")

        a_rows = self.get_states(a_energy, extra_parameter)
        if len(a_rows) == 0:
            self.log(
                f"{a_energy}: eon_a_value is {str(eon_sum_value)}, eon_time: {eon_a_time.strftime('%Y-%m-%d %H:%M:%S')}", level="INFO")
            self.set_state(a_energy, state=eon_a_value, unit_of_measurement='kWh', attributes={
                           "friendly_name": friendly_name, "last_changed": eon_a_time.strftime('%Y-%m-%d %H:%M:%S'), "unit_of_measurement": 'kWh', "device_class": "power"})

        return eon_sum_value

    def get_report_data(self):
        self.eon_report_id_180_280 = self.config["eon_report_id_180_280"]
        eon_report_id_180_280_file = "./eon_report_id_180_280.json"
        if exists(eon_report_id_180_280_file):
            json_response = json.load(open(eon_report_id_180_280_file))
        else:
            json_response = self.get_data(
                report_id=self.eon_report_id_180_280,
                per_page_number=10,
                since=None,
                until=None,
            )
        self.log(
            f"eon_report_id_180_280: {json_response}", level="DEBUG", ascii_encode=False
        )

        eon_1_8_0_report = self.get_report_data_sub(
            data=json_response[0]["data"],
            eon_sensor_entity_id=self.sensor_1_8_0,
            total_friendly_name="EON consumption energy total",
        )

        eon_2_8_0_report = self.get_report_data_sub(
            data=json_response[1]["data"],
            eon_sensor_entity_id=self.sensor_2_8_0,
            total_friendly_name="EON export energy total",
        )

        return eon_1_8_0_report, eon_2_8_0_report

    def get_report_data_sub(self, data, eon_sensor_entity_id, total_friendly_name):
        eon_report = {}
        self.log(
            f"eon_sensor_entity_id: {eon_sensor_entity_id} - {data}",
            level="DEBUG",
            ascii_encode=False,
        )
        for eon_data in data:
            self.collect_daily_data(
                eon_data, eon_sensor_entity_id, eon_report, total_friendly_name
            )

        if len(eon_report) > 0:
            eon_report = {key: val for key, val in eon_report.items()}
            self.normalize_eon_chart_data(eon_sensor_entity_id, eon_report)

        return eon_report

    def collect_daily_data(self, eon_data, eon_sensor, eon_report, friendly_name):
        eon_value = round(eon_data['value'], 5)
        eon_time = datetime.datetime.strptime(
            eon_data['time'], '%Y-%m-%dT%H:%M:%S').astimezone(tz=datetime.timezone.utc)
        extra_parameter = " AND JSON_CONTAINS(sa.shared_attrs, '\"" + eon_time.strftime(
            '%Y-%m-%d %H:%M:%S') + "\"', '$.last_changed')"
        rows = self.get_states(eon_sensor, extra_parameter)
        eon_report[eon_time] = eon_value
        if len(rows) == 0 and eon_value > 0:
            self.set_state(eon_sensor,
                           state=eon_value,
                           unit_of_measurement='kWh',
                           attributes={"state_class": "total_increasing",
                                       "last_changed": eon_time.strftime('%Y-%m-%d %H:%M:%S'),
                                       "unit_of_measurement": 'kWh',
                                       "friendly_name": friendly_name,
                                       "device_class": "energy"})
            self.log(
                f"{eon_sensor}: eon_value is {str(eon_value)}, eon_time: {eon_time.strftime('%Y-%m-%d %H:%M:%S')}", level="DEBUG")

    def get_data(self, report_id, per_page_number, since, until):

        offset = int(self.offset)
        if not since:
            since = (datetime.datetime.now() + datetime.timedelta(days=-1 + offset))
        if not until:
            until = datetime.datetime.now()

        params = {
            "page": 1,
            "perPage": per_page_number,
            "reportId": report_id,
            "since": since.strftime('%Y-%m-%d'),
            "until": until.strftime('%Y-%m-%dT23:00:00.000Z')
        }

        self.log(f"get_eon_params: {params}", level="DEBUG")
        data_content = self.session.get(EON_PROFILE_DATA_URL, params=params, verify=True)
        json_response = data_content.json()
        self.log(f"report_id:{report_id} - {json_response}", level="DEBUG", ascii_encode=False)
        return json_response

    def login(self, username, password):
        session = requests.Session()
        content = session.get(EON_ACCOUNT_URL, verify=True)
        index_content = BeautifulSoup(content.content, "html.parser")
        request_verification_token = self.get_verificationtoken(index_content)

        payload = {
            "UserName": username,
            "Password": password,
            "__RequestVerificationToken": request_verification_token
        }

        header = {"Content-Type": "application/x-www-form-urlencoded"}
        content = session.post(EON_ACCOUNT_URL, data=payload,
                               headers=header, verify=True)
        return session

    def normalize_eon_chart_data(self, eon_type, data):
        self.log(
            f"normalize_eon_chart_data - '{eon_type}', '{data}'", level="DEBUG")
        for eon_time, eon_value in data.items():
            extra_parameter = " AND JSON_CONTAINS(sa.shared_attrs, '\"" + eon_time.strftime(
                '%Y-%m-%d %H:%M:%S') + "\"', '$.last_changed')"
            rows = self.get_states(eon_type, extra_parameter)
            for row in rows:
                event_id = row['event_id']

                state_id = row['state_id']
                self.set_timestamp_and_state(eon_time, eon_value, state_id, event_id)


        self.log("END - normalize_eon_chart_data", level="DEBUG")

    def set_timestamp_and_state(self, eon_time, eon_value, state_id, event_id):
        connection = pymysql.connect(host=self.db_host,
                                     user=self.db_user,
                                     password=self.db_password,
                                     db=self.db_name,
                                     charset='utf8mb4',
                                     cursorclass=pymysql.cursors.DictCursor)
        try:
            with connection.cursor() as cursor:
                sql_query = """UPDATE states SET last_changed_ts = %s, last_updated_ts  = %s, state = %s WHERE state_id = %s"""
                sql_params = (datetime.datetime.timestamp(eon_time), datetime.datetime.timestamp(eon_time),
                         str(eon_value), state_id)
                cursor.execute(sql_query, sql_params)
                connection.commit()
            # with connection.cursor() as cursor:
            #     sql_query = """UPDATE events SET time_fired_ts = %s WHERE event_id = %s"""
            #     # eon_formatted_date = eon_time.strftime('%Y-%m-%d %H:%M:%S')
            #     sql_params = (datetime.datetime.timestamp(eon_time), event_id)
            #     cursor.execute(sql_query, sql_params)
            #     connection.commit()
        except Exception as err:
            self.log(f"Error - set_timestamp: {err}", level="ERROR")
        finally:
            connection.close()

    def get_states(self, eon_type, extra_parameter):


        self.log(
            f"Connect to the database - get_states - {extra_parameter}", level="DEBUG")
        connection = pymysql.connect(host=self.db_host,
                                     user=self.db_user,
                                     password=self.db_password,
                                     db=self.db_name,
                                     charset='utf8mb4',
                                     cursorclass=pymysql.cursors.DictCursor)
        try:
            with connection.cursor() as cursor:
                sql_query = (
                    "SELECT state_id, statem.entity_id as entity_id, state, event_id FROM states s "
                       "JOIN state_attributes sa on s.attributes_id = sa.attributes_id "
                    "JOIN states_meta statem on s.metadata_id = statem.metadata_id "
                    "WHERE statem.entity_id = %s "
                )
                if extra_parameter:
                    sql_query += extra_parameter
                cursor.execute(sql_query, (eon_type))
                rows = cursor.fetchall()
                self.log(f"rows - get_states {rows}.", level="DEBUG")
        except Exception as err:
            self.log(f"Error - get_states: {err}", level="ERROR")
        finally:
            connection.close()
            return rows