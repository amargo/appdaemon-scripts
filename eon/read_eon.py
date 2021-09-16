import hassapi as hass
import json
import requests
from bs4 import BeautifulSoup
import datetime
import time
import pytz
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
        sensor_1_8_0_sensor = self.args['1_8_0_sensor']
        sensor_2_8_0_sensor = self.args['2_8_0_sensor']
        positive_a_energy = self.args['positive_a_energy']
        negative_a_energy = self.args['negative_a_energy']
        timezone = pytz.timezone("Europe/Budapest")

        for eon_daily_time, eon_daily_value in eon_1_8_0_report.items():
            eon_positive_a = {}
            eon_positive_a_total = {}

            eon_daily_time_tmp = eon_daily_time.astimezone(tz=timezone)
            final_since_time = eon_daily_time_tmp + datetime.timedelta(minutes=14)
            final_until_time = final_since_time + datetime.timedelta(hours=23) + datetime.timedelta(minutes=32)
            jsonResponse = self.get_data(profile_data_url, session, self.args['chart_id'], 200, final_since_time, final_until_time)

            eon_sum_value = eon_daily_value
            for positive_a in jsonResponse[0]['data']:
                eon_sum_value = self.collect_chart_data(positive_a, positive_a_energy, eon_positive_a, sensor_1_8_0_sensor, eon_1_8_0_report, eon_positive_a_total, eon_daily_time, eon_sum_value, sensor_1_8_0_sensor, "EON +A energy power", "EON consumption energy total")
        
            if len(eon_positive_a_total) > 0:
                time.sleep(5)
                eon_positive_a_total = {key:val for key, val in eon_positive_a_total.items() if val != 0}
                self.normalize_eon_chart_data(sensor_1_8_0_sensor, eon_positive_a_total)

            if len(eon_positive_a) > 0:
                time.sleep(5)
                self.normalize_eon_chart_data(positive_a_energy, eon_positive_a)


        for eon_daily_time, eon_daily_value in eon_2_8_0_report.items():
            eon_negative_a = {}
            eon_negative_a_total = {}
            eon_daily_time_tmp = eon_daily_time.astimezone(tz=timezone)
            final_since_time = eon_daily_time_tmp + datetime.timedelta(minutes=14)
            final_until_time = final_since_time + datetime.timedelta(hours=23) + datetime.timedelta(minutes=32)
            jsonResponse = self.get_data(profile_data_url, session, self.args['chart_id'], 200, final_since_time, final_until_time)

            eon_sum_value = eon_daily_value
            for negative_a in jsonResponse[1]['data']:
                eon_sum_value = self.collect_chart_data(negative_a, negative_a_energy, eon_negative_a, sensor_2_8_0_sensor, eon_2_8_0_report, eon_negative_a_total, eon_daily_time, eon_sum_value, sensor_2_8_0_sensor, "EON -A energy power", "EON export energy total")

            if len(eon_negative_a_total) > 0:
                time.sleep(5)
                eon_negative_a_total = {key:val for key, val in eon_negative_a_total.items() if val != 0}
                self.normalize_eon_chart_data(sensor_2_8_0_sensor, eon_negative_a_total)

            if len(eon_negative_a) > 0:
                time.sleep(5)
                self.normalize_eon_chart_data('sensor.eon_negative_a_energy_power', eon_negative_a)

    def collect_chart_data(self, a, a_energy, eon_a, sensor, eon_report, eon_a_total, eon_report_time, eon_report_value, eon_sensor, friendly_name, total_friendly_name):
        eon_a_value = round(a['value'], 5)
        eon_a_time = datetime.datetime.strptime(a['time'], '%Y-%m-%dT%H:%M:%S').astimezone(tz=datetime.timezone.utc)
        extra_parameter = " AND JSON_CONTAINS(attributes, '\"" + eon_a_time.strftime('%Y-%m-%d %H:%M:%S') + "\"', '$.last_changed')"
        eon_a[eon_a_time] = eon_a_value

        extra_parameter = " AND JSON_CONTAINS(attributes, '\"" + eon_a_time.strftime('%Y-%m-%d %H:%M:%S') + "\"', '$.last_changed')"
        total_rows = self.get_states(sensor, extra_parameter)
        eon_sum_value = eon_report_value + eon_a_value
        eon_sum_value = round(eon_sum_value, 5)
        eon_report[eon_report_time] = eon_sum_value
        eon_a_total[eon_a_time] = eon_sum_value
        if len(total_rows) == 0 and eon_sum_value > 0:
            self.set_state(eon_sensor, state = eon_sum_value, unit_of_measurement = 'kWh', attributes = { "state_class": "total_increasing", "last_reset": self.args['last_reset'], "last_changed": eon_a_time.strftime('%Y-%m-%d %H:%M:%S'), "unit_of_measurement": 'kWh', "friendly_name": total_friendly_name, "device_class": "energy"})
        
        a_rows = self.get_states(a_energy, extra_parameter)            
        if len(a_rows) == 0:
            self.set_state(a_energy, state = eon_a_value, unit_of_measurement = 'kWh', attributes = { "friendly_name": friendly_name, "last_changed": eon_a_time.strftime('%Y-%m-%d %H:%M:%S'), "unit_of_measurement": 'kWh', "device_class": "power"})   
        
        return eon_sum_value
        

    def get_report_data(self, profile_data_url, session):
        jsonResponse = self.get_data(profile_data_url, session, self.args['report_id'], 4, None, None)
        sensor_1_8_0_sensor = self.args['1_8_0_sensor']
        sensor_2_8_0_sensor = self.args['2_8_0_sensor']
        try:
            eon_1_8_0_report = {}
            self.log(jsonResponse[0]['data'])
            for eon_1_8_0_data in jsonResponse[0]['data']:
                self.collect_daily_data(eon_1_8_0_data, sensor_1_8_0_sensor, eon_1_8_0_report, "EON consumption energy total")

            if len(eon_1_8_0_report) > 0:
                eon_1_8_0_report = {key:val for key, val in eon_1_8_0_report.items() if val != 0}
                self.normalize_eon_chart_data(sensor_1_8_0_sensor, eon_1_8_0_report)

            eon_2_8_0_report = {}
            self.log(jsonResponse[1]['data'])
            for eon_2_8_0_data in jsonResponse[1]['data']:
                self.collect_daily_data(eon_2_8_0_data, sensor_2_8_0_sensor, eon_2_8_0_report, "EON export energy total")

            if len(eon_2_8_0_report) > 0:
                eon_2_8_0_report = {key:val for key, val in eon_2_8_0_report.items() if val != 0}
                self.normalize_eon_chart_data(sensor_2_8_0_sensor, eon_2_8_0_report)
        except Exception as ex:
            print(datetime.datetime.now(), "Error get_report_data {0}.".format(str(ex)))

        return eon_1_8_0_report, eon_2_8_0_report


    def collect_daily_data(self, eon_data, eon_sensor, eon_report, friendly_name):
        eon_value = round(eon_data['value'], 5)
        eon_time = datetime.datetime.strptime(eon_data['time'], '%Y-%m-%dT%H:%M:%S').astimezone(tz=datetime.timezone.utc)
        extra_parameter = " AND JSON_CONTAINS(attributes, '\"" + eon_time.strftime('%Y-%m-%d %H:%M:%S') + "\"', '$.last_changed')"
        rows = self.get_states(eon_sensor, extra_parameter)
        eon_report[eon_time] = eon_value
        if len(rows) == 0 and eon_value > 0:
            self.set_state(eon_sensor, state = eon_value, unit_of_measurement = 'kWh', attributes = { "state_class": "total_increasing", "last_reset": self.args['last_reset'], "last_changed": eon_time.strftime('%Y-%m-%d %H:%M:%S'), "unit_of_measurement": 'kWh', "friendly_name": friendly_name, "device_class": "energy"})
            print(eon_sensor + ": value is " + str(eon_value) + ", eon_time: " + eon_time.strftime('%Y-%m-%d %H:%M:%S'))

    def get_value_from_datetime_dict(self, dict, findable_date):
        for k,v in dict.items():
            if k.date() == findable_date.date():
                return k, v
        return None, None

    def get_data(self, profile_data_url, session, id, per_page_number, since, until):
        hyphen = self.args['hyphen']
        offset = int(self.args['offset'])
        if not since:
            since = (datetime.datetime.now() + datetime.timedelta(days=-1 + offset)).strftime('%Y-%m-%d')
        if not until:            
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