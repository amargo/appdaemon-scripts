import hassapi as hass
import json
import requests
from bs4 import BeautifulSoup
import datetime
import time
import pymysql.cursors

class Eon(hass.Hass):
    def initialize(self):
        every_hour = self.args['every_hour']
        # time = datetime.time(0, 0, 0)
        self.run_every(self.read_data, "now", every_hour * (60*60))
        # self.run_minutely(self.read_data, time)

    def get_verificationtoken(self, content):
        try:
            self.log("get verification token from E.ON portal")
            toke = content.find('input', {'name': '__RequestVerificationToken'})
            return toke.get('value')
        except Exception as ex:
            self.log("Unable to get verification token." + str(ex) + ", content: " + str(content))


    def read_data(self, kwargs):
        account_url = self.args['eon_url'] + "/Account/Login"
        profile_data_url = self.args['eon_url'] + "/ProfileData/ProfileData"
        username = self.args['username']
        password = self.args['password']
        messages = []

        self.log("Starting E.ON reader")
        # self.set_namespace("hass")

        try:
            session = self.login(account_url, username, password)
            eon_1_8_0_report, eon_2_8_0_report = self.get_report_data(profile_data_url, session)
            self.get_chart_data(profile_data_url, session, eon_1_8_0_report, eon_2_8_0_report)

        except Exception as ex:
            self.log(datetime.datetime.now(), "Error retrive data from {0}.".format(str(ex)))

    def get_chart_data(self, profile_data_url, session, eon_1_8_0_report, eon_2_8_0_report):
        jsonResponse = self.get_data(profile_data_url, session, self.args['chart_id'], 2000)
        sensor_1_8_0_sensor = self.args['1_8_0_sensor']
        sensor_2_8_0_sensor = self.args['2_8_0_sensor']
        # self.log("eon_positive_a_energy_power len: %s", len(jsonResponse[0]['data']))
        # self.log("eon_negative_a_energy_power len: %s", len(jsonResponse[1]['data']))
        eon_positive_a = {}
        eon_positive_a_total = {}
        for positive_a in jsonResponse[0]['data']:
            eon_positive_a_value = round(positive_a['value'], 5)
            eon_positive_a_time = datetime.datetime.strptime(positive_a['time'], '%Y-%m-%dT%H:%M:%S')
            extra_parameter = " AND JSON_CONTAINS(attributes, '\"" + eon_positive_a_time.strftime('%Y-%m-%d %H:%M:%S') + "\"', '$.last_changed')"
            rows = self.get_states('sensor.eon_positive_a_energy_power', extra_parameter)
            eon_positive_a[eon_positive_a_time] = eon_positive_a_value
            eon_1_8_0_report_time, eon_1_8_0_report_value = self.get_value_from_datetime_dict(eon_1_8_0_report, eon_positive_a_time)
            if eon_1_8_0_report_value is not None:
                extra_parameter = " AND JSON_CONTAINS(attributes, '\"" + eon_positive_a_time.strftime('%Y-%m-%d %H:%M:%S') + "\"', '$.last_changed')"
                rows = self.get_states(sensor_1_8_0_sensor, extra_parameter)
                eon_positive_a_total_value = eon_1_8_0_report_value + eon_positive_a_value
                eon_positive_a_total_value = round(eon_positive_a_total_value, 5)
                eon_1_8_0_report[eon_1_8_0_report_time] = eon_positive_a_total_value
                eon_positive_a_total[eon_positive_a_time] = eon_positive_a_total_value
                if len(rows) == 0 and eon_positive_a_total_value > 0:
                    self.set_state(sensor_1_8_0_sensor, state = eon_positive_a_total_value, unit_of_measurement = 'kWh', attributes = { "state_class": "measurement", "last_reset": self.args['last_reset'], "last_changed": eon_positive_a_time, "unit_of_measurement": 'kWh', "friendly_name": "EON import energy total", "device_class": "energy"})
                    # self.log("sensor.eon_1_8_0_energy_total: %s - %s", eon_positive_a_time, eon_positive_a_total_value)
            if len(rows) == 0:
                self.set_state("sensor.eon_positive_a_energy_power", state = eon_positive_a_value, unit_of_measurement = 'kWh', attributes = { "friendly_name": "EON +A energy power", "last_changed": eon_positive_a_time, "unit_of_measurement": 'kWh', "device_class": "power"})

        if len(eon_positive_a_total) > 0:
            time.sleep(5)
            eon_positive_a_total = {key:val for key, val in eon_positive_a_total.items() if val != 0}
            self.normalize_eon_chart_data(sensor_1_8_0_sensor, eon_positive_a_total)

        if len(eon_positive_a) > 0:
            time.sleep(5)
            self.normalize_eon_chart_data('sensor.eon_positive_a_energy_power', eon_positive_a)

        eon_negative_a = {}
        eon_negative_a_total = {}
        for negative_a in jsonResponse[1]['data']:
            eon_negative_a_value = round(negative_a['value'], 5)
            eon_negative_a_time = datetime.datetime.strptime(negative_a['time'], '%Y-%m-%dT%H:%M:%S')
            extra_parameter = " AND JSON_CONTAINS(attributes, '\"" + eon_negative_a_time.strftime('%Y-%m-%d %H:%M:%S') + "\"', '$.last_changed')"
            rows = self.get_states('sensor.eon_negative_a_energy_power', extra_parameter)
            eon_negative_a[eon_negative_a_time] = eon_negative_a_value
            eon_2_8_0_report_time, eon_2_8_0_report_value = self.get_value_from_datetime_dict(eon_2_8_0_report, eon_negative_a_time)
            if eon_2_8_0_report_value is not None:
                extra_parameter = " AND JSON_CONTAINS(attributes, '\"" + eon_negative_a_time.strftime('%Y-%m-%d %H:%M:%S') + "\"', '$.last_changed')"
                rows = self.get_states(sensor_2_8_0_sensor, extra_parameter)
                eon_negative_a_total_value = eon_2_8_0_report_value + eon_negative_a_value
                eon_negative_a_total_value = round(eon_negative_a_total_value, 5)
                eon_2_8_0_report[eon_2_8_0_report_time] = eon_negative_a_total_value
                eon_negative_a_total[eon_negative_a_time] = eon_negative_a_total_value
                if len(rows) == 0 and eon_negative_a_total_value > 0:
                    self.set_state(sensor_2_8_0_sensor, state = eon_negative_a_total_value, unit_of_measurement = 'kWh', attributes = { "state_class": "measurement", "last_reset": self.args['last_reset'], "last_changed": eon_negative_a_time, "unit_of_measurement": 'kWh', "friendly_name": "EON export energy total", "device_class": "energy"})
                    # self.log("sensor.eon_2_8_0_energy_total: %s - %s", eon_negative_a_time, eon_negative_a_total_value)
            if len(rows) == 0:
                self.set_state("sensor.eon_negative_a_energy_power", state = eon_negative_a_value, unit_of_measurement = 'kWh', attributes = { "friendly_name": "EON -A energy power", "last_changed": eon_negative_a_time, "unit_of_measurement": 'kWh', "device_class": "power"})

        if len(eon_negative_a_total) > 0:
            time.sleep(5)
            eon_negative_a_total = {key:val for key, val in eon_negative_a_total.items() if val != 0}
            self.normalize_eon_chart_data(sensor_2_8_0_sensor, eon_negative_a_total)

        if len(eon_negative_a) > 0:
            time.sleep(5)
            self.normalize_eon_chart_data('sensor.eon_negative_a_energy_power', eon_negative_a)


    def get_report_data(self, profile_data_url, session):
        jsonResponse = self.get_data(profile_data_url, session, self.args['report_id'], 2)
        sensor_1_8_0_sensor = self.args['1_8_0_sensor']
        sensor_2_8_0_sensor = self.args['2_8_0_sensor']
        try:
            eon_1_8_0 = {}
            eon_1_8_0_report = {}
            self.log(jsonResponse[0]['data'])
            for eon_1_8_0_data in jsonResponse[0]['data']:
                eon_1_8_0_value = round(eon_1_8_0_data['value'], 2)
                eon_1_8_0_time = datetime.datetime.strptime(eon_1_8_0_data['time'], '%Y-%m-%dT%H:%M:%S')
                extra_parameter = " AND JSON_CONTAINS(attributes, '\"" + eon_1_8_0_time.strftime('%Y-%m-%d %H:%M:%S') + "\"', '$.last_changed')"
                rows = self.get_states(sensor_1_8_0_sensor, extra_parameter)
                eon_1_8_0_report[eon_1_8_0_time] = eon_1_8_0_value
                if len(rows) == 0 and eon_1_8_0_value > 0:
                    self.set_state(sensor_1_8_0_sensor, state = eon_1_8_0_value, unit_of_measurement = 'kWh', attributes = { "state_class": "measurement", "last_reset": self.args['last_reset'], "last_changed": eon_1_8_0_time, "unit_of_measurement": 'kWh', "friendly_name": "EON import energy total", "device_class": "energy"})

            if len(eon_1_8_0_report) > 0:
                eon_1_8_0_report = {key:val for key, val in eon_1_8_0_report.items() if val != 0}
                self.normalize_eon_chart_data(sensor_1_8_0_sensor, eon_1_8_0_report)

            eon_2_8_0 = {}
            eon_2_8_0_report = {}
            self.log(jsonResponse[1]['data'])
            for eon_2_8_0_data in jsonResponse[1]['data']:
                eon_2_8_0_value = round(eon_2_8_0_data['value'], 2)
                eon_2_8_0_time = datetime.datetime.strptime(eon_2_8_0_data['time'], '%Y-%m-%dT%H:%M:%S')
                extra_parameter = " AND JSON_CONTAINS(attributes, '\"" + eon_1_8_0_time.strftime('%Y-%m-%d %H:%M:%S') + "\"', '$.last_changed')"
                rows = self.get_states(sensor_2_8_0_sensor, extra_parameter)
                eon_2_8_0_report[eon_2_8_0_time] = eon_2_8_0_value
                if len(rows) == 0 and eon_2_8_0_value > 0:
                    self.set_state(sensor_2_8_0_sensor, state = eon_2_8_0_value, unit_of_measurement = 'kWh', attributes = { "state_class": "measurement", "last_reset": self.args['last_reset'], "last_changed": eon_2_8_0_time, "unit_of_measurement": 'kWh', "friendly_name": "EON export energy total", "device_class": "energy"})

            if len(eon_2_8_0_report) > 0:
                eon_2_8_0_report = {key:val for key, val in eon_2_8_0_report.items() if val != 0}
                self.normalize_eon_chart_data(sensor_2_8_0_sensor, eon_2_8_0_report)
        except Exception as ex:
            print(datetime.datetime.now(), "Error get_report_data {0}.".format(str(ex)))

        return eon_1_8_0_report, eon_2_8_0_report

    def get_value_from_datetime_dict(self, dict, findable_date):
        for k,v in dict.items():
            if k.date() == findable_date.date():
                return k, v
        return None, None

    def get_data(self, profile_data_url, session, id, per_page_number):
        hyphen = self.args['hyphen']
        offset = int(self.args['offset'])
        since = (datetime.datetime.now() + datetime.timedelta(days=-1 + offset)).strftime('%Y-%m-%d')
        until = (datetime.datetime.now() + datetime.timedelta(days=offset)).strftime('%Y-%m-%dT23:00:00.000Z')
        params = {
                "page": 1,
                "perPage": per_page_number,
                "reportId": id,
                "since": since,
                "until": until,
                "-": hyphen
            }
        data_content = session.get(profile_data_url, params=params)
        jsonResponse = data_content.json()
        return jsonResponse

    def login(self, account_url, username, password):
        session = requests.Session()
        content = session.get(account_url)
        index_content = BeautifulSoup(content.content, "html.parser")
        request_verification_token = self.get_verificationtoken(index_content)

        payload = {
                "UserName": username,
                "Password": password,
                "__RequestVerificationToken": request_verification_token
            }

        header = {"Content-Type": "application/x-www-form-urlencoded"}
        content = session.post(account_url, data=payload, headers=header)
        return session


    def normalize_eon_chart_data(self, eon_type, data):
        self.log("normalize_eon_chart_data - %s, %s", eon_type, data)
        try:
            for eon_time, eon_value in data.items():
                extra_parameter = " AND JSON_CONTAINS(attributes, '\"" + eon_time.strftime('%Y-%m-%d %H:%M:%S') + "\"', '$.last_changed')"
                rows = self.get_states(eon_type, extra_parameter)
                for row in rows:
                    event_id = row['event_id']
                    state = row['state']
                    state_id = row['state_id']
                    self.set_timestamp_and_state(eon_type, eon_time, eon_value, state_id, event_id)

        except Exception as ex:
            print(datetime.datetime.now(), "Error normalize_eon_chart_data {0}.".format(str(ex)))
        finally:
            print("END - normalize_eon_chart_data")


    def is_number(self, s):
        try:
            float(s)
            return True
        except ValueError:
            return False

    def set_timestamp_and_state(self, eon_type, eon_time, eon_value, state_id, event_id):
        # self.log("%s - set_timestamp: %s - %s", eon_type, eon_time, state_id)
        connection = pymysql.connect(host=self.args['host'],
                                    user=self.args['username_db'],
                                    password=self.args['password_db'],
                                    db=self.args['database'],
                                    charset='utf8mb4',
                                    cursorclass=pymysql.cursors.DictCursor)
        try:
            with connection.cursor() as cursor:
                sql = """UPDATE states SET last_changed = %s, last_updated = %s, created = %s, state = %s WHERE state_id = %s"""
                eon_formatted_date = eon_time.strftime('%Y-%m-%d %H:%M:%S')
                input = (eon_formatted_date, eon_formatted_date, eon_formatted_date, str(eon_value), state_id)
                cursor.execute(sql, input)
                connection.commit()
            with connection.cursor() as cursor:
                sql = """UPDATE events SET time_fired = %s, created = %s WHERE event_id = %s"""
                eon_formatted_date = eon_time.strftime('%Y-%m-%d %H:%M:%S')
                input = (eon_formatted_date, eon_formatted_date, event_id)
                cursor.execute(sql, input)
                connection.commit()
        except Exception as ex:
            self.log("ERROR - set_timestamp - %s", state_id)
            self.log(datetime.datetime.now(), "Error set_timestamp {0}.".format(str(ex)))
        finally:
            connection.close()


    def get_states(self, eon_type, extra_parameter):
        offset = int(self.args['offset'])
        # Connect to the database
        # self.log("Connect to the database - get_states - %s", extra_parameter)
        connection = pymysql.connect(host=self.args['host'],
                                    user=self.args['username_db'],
                                    password=self.args['password_db'],
                                    db=self.args['database'],
                                    charset='utf8mb4',
                                    cursorclass=pymysql.cursors.DictCursor)
        try:
            # eon_formatted_date = (datetime.datetime.now() + datetime.timedelta(days=-1 + offset)).strftime('%Y-%m-%d %H:%M:%S')
            with connection.cursor() as cursor:
                # Read a single record
                sql = """SELECT state_id, entity_id, state, created, event_id FROM states WHERE entity_id = %s"""
                if extra_parameter:
                    sql += extra_parameter
                cursor.execute(sql, (eon_type))
                rows = cursor.fetchall()
        finally:
            connection.close()
            return rows