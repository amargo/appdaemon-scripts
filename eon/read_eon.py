import appdaemon.plugins.hass.hassapi as hass
import json
import requests
import datetime
import time
import pytz
import pymysql.cursors

# from config_args import Config
from bs4 import BeautifulSoup

BASE_URL = 'https://energia.eon-hungaria.hu/W1000/'
ACCOUNT_URL = f'{BASE_URL}Account/Login'
PROFILE_DATA_URL = f'{BASE_URL}ProfileData/ProfileData'

class Config():
    CONFIG = {}

    def __init__(self, args, log):
        self.__class__.CONFIG['db_user'] = args['db_user']
        self.__class__.CONFIG['db_password'] = args['db_password']
        self.__class__.CONFIG['db_name'] = args['db_name']
        self.__class__.CONFIG['db_host'] = args['db_host']

        self.__class__.CONFIG['eon_user'] = args['eon_user']
        self.__class__.CONFIG['eon_password'] = args['eon_password']
        self.__class__.CONFIG['report_id_180_280'] = args['eon_report_id_180_280']
        self.__class__.CONFIG['report_id_pa_ma'] = args['eon_report_id_pa_ma']

        self.__class__.CONFIG['every_hour'] = args['every_hour']
        self.__class__.CONFIG['offset'] = args['offset']

        self.__class__.CONFIG['1_8_0_sensor'] = args['1_8_0_sensor']
        self.__class__.CONFIG['2_8_0_sensor'] = args['2_8_0_sensor']
        self.__class__.CONFIG['positive_a_energy'] = args['positive_a_energy']
        self.__class__.CONFIG['negative_a_energy'] = args['negative_a_energy']

class Eon(hass.Hass):
    def initialize(self):
        every_hour = self.args['every_hour']
        # time = datetime.time(0, 0, 0)
        self.run_every(self.read_data, "now", every_hour * (60*60))

    def get_verificationtoken(self, content):
        self.log("get verification token from E.ON portal", level="INFO")
        toke = content.find('input', {'name': '__RequestVerificationToken'})
        return toke.get('value')

    def read_data(self, kwargs):
        Config(self.args, self.log)
        account_url = ACCOUNT_URL
        profile_data_url = PROFILE_DATA_URL
        username = Config.CONFIG['eon_user']
        password = Config.CONFIG['eon_password']
        self.db_host = Config.CONFIG['db_host']
        self.db_name = Config.CONFIG['db_name']
        self.db_password = Config.CONFIG['db_password']
        self.db_user = Config.CONFIG['db_user']
        self.offset = Config.CONFIG['offset']

        self.log("Starting E.ON reader", level="INFO")
        session = self.login(account_url, username, password)
        self.log("Start receiving data", level="INFO")
        eon_1_8_0_report, eon_2_8_0_report = self.get_report_data(
            profile_data_url, session)
        self.log(f"Start receiving chart data", level="INFO")
        self.get_chart_data(profile_data_url, session,
                            eon_1_8_0_report, eon_2_8_0_report)
        self.log("END processing data", level="INFO")

    def get_chart_data(self, profile_data_url, session, eon_1_8_0_report, eon_2_8_0_report):
        sensor_1_8_0_sensor = Config.CONFIG['1_8_0_sensor']
        sensor_2_8_0_sensor = Config.CONFIG['2_8_0_sensor']
        positive_a_energy = Config.CONFIG['positive_a_energy']
        negative_a_energy = Config.CONFIG['negative_a_energy']
        report_id = Config.CONFIG['report_id_pa_ma']
        timezone = pytz.timezone("Europe/Budapest")

        self.log(f"eon_1_8_0_report: {eon_1_8_0_report}", level="INFO")

        for eon_daily_time, eon_daily_value in eon_1_8_0_report.items():
            eon_positive_a = {}
            eon_positive_a_total = {}

            eon_daily_time_tmp = eon_daily_time.astimezone(tz=timezone)
            final_since_time = eon_daily_time_tmp + \
                datetime.timedelta(minutes=14)
            final_until_time = final_since_time + \
                datetime.timedelta(hours=23) + datetime.timedelta(minutes=32)
            jsonResponse = self.get_data(profile_data_url, session, report_id, 200, final_since_time, final_until_time)
            # self.log("Test1", level="INFO")

            eon_sum_value = eon_daily_value
            self.log(jsonResponse[0]['data'], level="DEBUG", ascii_encode=False)
            for positive_a in jsonResponse[0]['data']:
                eon_sum_value = self.collect_chart_data(positive_a, positive_a_energy, eon_positive_a, sensor_1_8_0_sensor, eon_1_8_0_report,
                                                        eon_positive_a_total, eon_daily_time, eon_sum_value, sensor_1_8_0_sensor, "EON +A energy power", "EON consumption energy total")

            if len(eon_positive_a_total) > 0:
                eon_positive_a_total = {
                    key: val for key, val in eon_positive_a_total.items() if val != 0}
                self.normalize_eon_chart_data(
                    sensor_1_8_0_sensor, eon_positive_a_total)

            if len(eon_positive_a) > 0:
                self.normalize_eon_chart_data(
                    positive_a_energy, eon_positive_a)

        self.log(f"eon_2_8_0_report: {eon_2_8_0_report}", level="INFO")

        for eon_daily_time, eon_daily_value in eon_2_8_0_report.items():
            eon_negative_a = {}
            eon_negative_a_total = {}
            eon_daily_time_tmp = eon_daily_time.astimezone(tz=timezone)
            final_since_time = eon_daily_time_tmp + \
                datetime.timedelta(minutes=14)
            final_until_time = final_since_time + \
                datetime.timedelta(hours=23) + datetime.timedelta(minutes=32)
            jsonResponse = self.get_data(profile_data_url, session, report_id, 200, final_since_time, final_until_time)

            eon_sum_value = eon_daily_value
            self.log(jsonResponse[1]['data'], level="DEBUG", ascii_encode=False)
            for negative_a in jsonResponse[1]['data']:
                eon_sum_value = self.collect_chart_data(negative_a, negative_a_energy, eon_negative_a, sensor_2_8_0_sensor, eon_2_8_0_report,
                                                        eon_negative_a_total, eon_daily_time, eon_sum_value, sensor_2_8_0_sensor, "EON -A energy power", "EON export energy total")

            if len(eon_negative_a_total) > 0:
                eon_negative_a_total = {
                    key: val for key, val in eon_negative_a_total.items() if val != 0}
                self.normalize_eon_chart_data(
                    sensor_2_8_0_sensor, eon_negative_a_total)

            if len(eon_negative_a) > 0:
                self.normalize_eon_chart_data(
                    negative_a_energy, eon_negative_a)

    def collect_chart_data(self, a, a_energy, eon_a, sensor, eon_report, eon_a_total, eon_report_time, eon_report_value, eon_sensor, friendly_name, total_friendly_name):
        eon_a_value = round(a['value'], 5)
        eon_a_time = datetime.datetime.strptime(
            a['time'], '%Y-%m-%dT%H:%M:%S').astimezone(tz=datetime.timezone.utc)
        extra_parameter = " AND JSON_CONTAINS(sa.shared_attrs, '\"" + eon_a_time.strftime(
            '%Y-%m-%d %H:%M:%S') + "\"', '$.last_changed')"
        eon_a[eon_a_time] = eon_a_value

        extra_parameter = " AND JSON_CONTAINS(sa.shared_attrs, '\"" + eon_a_time.strftime(
            '%Y-%m-%d %H:%M:%S') + "\"', '$.last_changed')"
        total_rows = self.get_states(sensor, extra_parameter)
        eon_sum_value = eon_report_value + eon_a_value
        eon_sum_value = round(eon_sum_value, 5)
        eon_report[eon_report_time] = eon_sum_value
        eon_a_total[eon_a_time] = eon_sum_value
        if len(total_rows) == 0 and eon_sum_value > 0:
            self.set_state(eon_sensor, state=eon_sum_value, unit_of_measurement='kWh', attributes={"state_class": "total_increasing", "last_changed": eon_a_time.strftime(
                '%Y-%m-%d %H:%M:%S'), "unit_of_measurement": 'kWh', "friendly_name": total_friendly_name, "device_class": "energy"})
            self.log(
                f"{eon_sensor}: eon_sum_value is {str(eon_sum_value)}, eon_time: {eon_a_time.strftime('%Y-%m-%d %H:%M:%S')}", level="INFO")

        a_rows = self.get_states(a_energy, extra_parameter)
        if len(a_rows) == 0:
            self.log(
                f"{a_energy}: eon_a_value is {str(eon_sum_value)}, eon_time: {eon_a_time.strftime('%Y-%m-%d %H:%M:%S')}", level="INFO")
            self.set_state(a_energy, state=eon_a_value, unit_of_measurement='kWh', attributes={
                           "friendly_name": friendly_name, "last_changed": eon_a_time.strftime('%Y-%m-%d %H:%M:%S'), "unit_of_measurement": 'kWh', "device_class": "power"})

        return eon_sum_value

    def get_report_data(self, profile_data_url, session):
        report_id = Config.CONFIG['report_id_180_280']
        jsonResponse = self.get_data(
            profile_data_url, session, report_id, 10, None, None)
        self.log(f"report_id_180_280: {jsonResponse}", level="DEBUG", ascii_encode=False)
        sensor_1_8_0_sensor = Config.CONFIG['1_8_0_sensor']
        sensor_2_8_0_sensor = Config.CONFIG['2_8_0_sensor']

        eon_1_8_0_report = {}
        self.log(jsonResponse[0]['data'], level="DEBUG", ascii_encode=False)
        for eon_1_8_0_data in jsonResponse[0]['data']:
            self.collect_daily_data(
                eon_1_8_0_data, sensor_1_8_0_sensor, eon_1_8_0_report, "EON consumption energy total")

        if len(eon_1_8_0_report) > 0:
            eon_1_8_0_report = {key: val for key,
                                val in eon_1_8_0_report.items() if val != 0}
            self.normalize_eon_chart_data(
                sensor_1_8_0_sensor, eon_1_8_0_report)

        eon_2_8_0_report = {}
        self.log(jsonResponse[1]['data'], level="DEBUG", ascii_encode=False)
        for eon_2_8_0_data in jsonResponse[1]['data']:
            self.collect_daily_data(
                eon_2_8_0_data, sensor_2_8_0_sensor, eon_2_8_0_report, "EON export energy total")

        if len(eon_2_8_0_report) > 0:
            eon_2_8_0_report = {key: val for key,
                                val in eon_2_8_0_report.items() if val != 0}
            self.normalize_eon_chart_data(
                sensor_2_8_0_sensor, eon_2_8_0_report)

        return eon_1_8_0_report, eon_2_8_0_report

    def collect_daily_data(self, eon_data, eon_sensor, eon_report, friendly_name):
        eon_value = round(eon_data['value'], 5)
        eon_time = datetime.datetime.strptime(
            eon_data['time'], '%Y-%m-%dT%H:%M:%S').astimezone(tz=datetime.timezone.utc)
        extra_parameter = " AND JSON_CONTAINS(sa.shared_attrs, '\"" + eon_time.strftime(
            '%Y-%m-%d %H:%M:%S') + "\"', '$.last_changed')"
        rows = self.get_states(eon_sensor, extra_parameter)
        eon_report[eon_time] = eon_value
        if len(rows) == 0 and eon_value > 0:
            self.set_state(eon_sensor, state=eon_value, unit_of_measurement='kWh', attributes={"state_class": "total_increasing", "last_changed": eon_time.strftime(
                '%Y-%m-%d %H:%M:%S'), "unit_of_measurement": 'kWh', "friendly_name": friendly_name, "device_class": "energy"})
            self.log(
                f"{eon_sensor}: eon_value is {str(eon_value)}, eon_time: {eon_time.strftime('%Y-%m-%d %H:%M:%S')}", level="INFO")

    def get_data(self, profile_data_url, session, report_id, per_page_number, since, until):

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

        self.log(f"get_eon_params: {params}", level="INFO")
        data_content = session.get(profile_data_url, params=params, verify=True)
        jsonResponse = data_content.json()
        return jsonResponse

    def login(self, account_url, username, password):
        session = requests.Session()
        content = session.get(account_url, verify=True)
        index_content = BeautifulSoup(content.content, "html.parser")
        request_verification_token = self.get_verificationtoken(index_content)

        payload = {
            "UserName": username,
            "Password": password,
            "__RequestVerificationToken": request_verification_token
        }

        header = {"Content-Type": "application/x-www-form-urlencoded"}
        content = session.post(account_url, data=payload,
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
                sql = """UPDATE states SET last_changed = %s, last_updated = %s, state = %s WHERE state_id = %s"""
                eon_formatted_date = eon_time.strftime('%Y-%m-%d %H:%M:%S')
                input = (eon_formatted_date, eon_formatted_date,
                         str(eon_value), state_id)
                cursor.execute(sql, input)
                connection.commit()
            with connection.cursor() as cursor:
                sql = """UPDATE events SET time_fired = %s WHERE event_id = %s"""
                eon_formatted_date = eon_time.strftime('%Y-%m-%d %H:%M:%S')
                input = (eon_formatted_date, event_id)
                cursor.execute(sql, input)
                connection.commit()
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
                sql = ("SELECT state_id, entity_id, state, event_id FROM states s "
                       "JOIN state_attributes sa on s.attributes_id = sa.attributes_id "
                       "WHERE entity_id = %s ")
                if extra_parameter:
                    sql += extra_parameter
                cursor.execute(sql, (eon_type))
                rows = cursor.fetchall()
                self.log(f"rows - get_states {rows}.", level="DEBUG")
        except Exception as err:
            self.log(f"Error - get_states: {err}", level="ERROR")
        finally:
            connection.close()
            return rows