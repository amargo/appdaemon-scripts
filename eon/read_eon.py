import hassapi as hass
import json
import requests
from bs4 import BeautifulSoup
from datetime

class Eon(hass.Hass):
    def initialize(self):
        every_hour = self.args['every_hour']
        runtime = datetime.time(every_hour, 0, 0)
        self.run_hourly(self.read_data, runtime)
        # self.run_minutely(self.read_data, runtime)

    def get_verificationtoken(self, content):
        try:
            toke = content.find('input', {'name': '__RequestVerificationToken'})
            return toke.get('value')
        except Exception as ex:
            self.log("Unable to get verification token." + str(ex) + ", content: " + str(content))

    def read_data(self, kwargs):
        account_url = self.args['eon_url'] + "/Account/Login"
        profile_data_url = self.args['eon_url'] + "/ProfileData/ProfileData"
        username = self.args['username']
        password = self.args['password']

        try:
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

            report_id = self.args['report_id']
            hyphen = self.args['hyphen']
            offset = int(self.args['offset'])
            since = (datetime.datetime.now() + datetime.timedelta(days=-1 + offset)).strftime('%Y-%m-%d')
            until = (datetime.datetime.now() + datetime.timedelta(days=offset)).strftime('%Y-%m-%dT23:00:00.000Z')

            params = {
                "page": 1,
                "perPage": 2,
                "reportId": report_id,
                "since": since,
                "until": until,
                "-": hyphen
            }
            data_content = session.get(profile_data_url, params=params)
            jsonResponse = data_content.json()

            self.set_state("state.eon_1_8_0", state = round(jsonResponse[0]['data'][0]['value'], 2), attributes = { "friendly_name": "EON import", "unit_of_measurement": 'kWh', "device_class": "power"})
            self.set_state("state.eon_2_8_0", state = round(jsonResponse[1]['data'][0]['value'], 2), attributes = { "friendly_name": "EON export", "unit_of_measurement": 'kWh', "device_class": "power"})
        except Exception as ex:
            self.log(datetime.now(), "Error retrive data from {0}.".format(str(ex)))
