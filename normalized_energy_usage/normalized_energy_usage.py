import hassapi as hass
import datetime
import time
import pymysql.cursors

class NormalizedEnergyUsage(hass.Hass):
    def initialize(self):
        every_hour = self.args['every_hour']
        # time = datetime.time(0, 0, 0)
        self.run_every(self.setup, "now", every_hour * (60*60))


    def setup(self, kwargs):
        self.log("Normalizing energy usage")
        try:
            self.normalize_data(self.args["1_8_0_sensor"])
            self.normalize_data(self.args["2_8_0_sensor"])

        except Exception as ex:
            self.log(datetime.datetime.now(), "Error retrive data from {0}.".format(str(ex)))
        finally:
            self.log("END - Normalizing energy usage")


    def normalize_data(self, eon_type):
        try:
            rows = self.get_states(eon_type)
            for row in rows:
                fixed_state = round(float(row['fixed_state']), 2)
                if fixed_state > row['state']:
                    sum_state = fixed_state - row['state']
                    row['state'] = fixed_state
                    row['sum_state'] = row['sum_state'] + sum_state
                    self.set_sum_and_state(eon_type, row['statistic_id'], row['sum_state'], row['state'])

        except Exception as ex:
            self.log(datetime.datetime.now(), "Error {0}.".format(str(ex)))
        finally:
            self.log("END - normalize_data")


    def set_sum_and_state(self, eon_type, statistic_id, sum_state, state):
        self.log("%s - set_sum_and_state: %s - %s - %s", eon_type, statistic_id, sum_state, state)
        # Connect to the database
        connection = pymysql.connect(host=self.args['host'],
                                    user=self.args['username'],
                                    password=self.args['password'],
                                    db=self.args['database'],
                                    charset='utf8mb4',
                                    cursorclass=pymysql.cursors.DictCursor)
        try:
            with connection.cursor() as cursor:
                sql = """UPDATE statistics SET sum = %s, state = %s WHERE id = %s"""
                input = (sum_state, state, statistic_id)
                cursor.execute(sql, input)
                connection.commit()
        except Exception as ex:
            self.log("ERROR - set_timestamp")
            self.log(datetime.datetime.now(), "Error {0}.".format(str(ex)))
        finally:
            connection.close()


    def get_states(self, eon_type):
        offset = int(self.args['offset'])
        # Connect to the database
        connection = pymysql.connect(host=self.args['host'],
                                    user=self.args['username'],
                                    password=self.args['password'],
                                    db=self.args['database'],
                                    charset='utf8mb4',
                                    cursorclass=pymysql.cursors.DictCursor)

        offset_date = (datetime.datetime.now() + datetime.timedelta(days=-1 + offset)).strftime('%Y-%m-%d %H:%M:%S')

        try:
            with connection.cursor() as cursor:
                # Read a single record
                sql = ( "SELECT s.id as statistic_id, s.created as created, s.`start` as start_date, s.state as state, s.sum as sum_state, sm.statistic_id as statistic_id, fixed.state as fixed_state FROM statistics s "
                        "join statistics_meta sm on s.metadata_id = sm.id "
                        "join states fixed on fixed.entity_id = sm.statistic_id AND fixed.created = s.`start` "
                        "WHERE sm.statistic_id = %s "
                        "AND s.`start` > %s"
                        "ORDER BY `start`;")

                cursor.execute(sql, (eon_type, offset_date))
                rows = cursor.fetchall()
        except Exception as ex:
            self.log(datetime.datetime.now(), "Error {0}.".format(str(ex)))
        finally:
            connection.close()
            return rows