import hassapi as hass
import datetime
import time
import pymysql.cursors

class NormalizedEnergyUsage(hass.Hass):
    def initialize(self):
        every_hour = self.args['every_hour']

        self.log(f"START - every {every_hour} hour(s)", level="INFO")
        self.run_every(self.setup, "now", every_hour * (60*60))
        
        if 'run_daily_at' in self.config:
            runtime = datetime.datetime.strptime(self.config['run_daily_at'], '%H:%M').time()
        else:
            runtime = datetime.time(7,40, 0)
            
        self.log(f"START - daily at {runtime}", level="INFO")
        self.run_daily(self.setup, runtime)        


    def setup(self, kwargs):
        self.log("Normalizing energy usage", level="INFO")
        numdays = self.args["numdays"]
        base = datetime.datetime.today()
        date_list = [base - datetime.timedelta(days=x) for x in range(numdays)]
        date_list.reverse()

        for idx, date in enumerate(date_list):
            if idx != len(date_list) -1:
                self.fix_statistics_data(self.args["1_8_0_sensor"], date.date())
                self.fix_statistics_data(self.args["2_8_0_sensor"], date.date())
            self.normalize_data(self.args["1_8_0_sensor"], date.date())
            self.normalize_data(self.args["2_8_0_sensor"], date.date())


    def fix_statistics_data(self, eon_type, date):
        rows = self.get_statistics_by_date(eon_type, date)
        metadata = self.get_metadata_id(eon_type)
        metadata_id = metadata["id"]

        number_of_hours = 24
        if date == (datetime.datetime.today() - datetime.timedelta(days=1)).date():
            number_of_hours = 20

        hours = [number_of_hour["start_date"].hour for number_of_hour in rows]
        missing_hours = [x for x in range(0, number_of_hours) if not x in hours]
        for missing_stat in missing_hours:
            start_datetime = datetime.datetime.combine(date, datetime.datetime.min.time())
            start_datetime = start_datetime + datetime.timedelta(hours=missing_stat)
            self.log(f"Generate missing datetime: {str(start_datetime)}", level="INFO")
            existing_datetime = self.get_statistics_by_datetime(eon_type, start_datetime)
            if len(existing_datetime) == 0:
                self.set_dummy_value_to_statistics(metadata_id, start_datetime)


    def get_statistics_by_datetime(self, eon_type, date):
        connection = pymysql.connect(host=self.args['host'],
                                    user=self.args['username'],
                                    password=self.args['password'],
                                    db=self.args['database'],
                                    charset='utf8mb4',
                                    cursorclass=pymysql.cursors.DictCursor)


        date_tmp = date.strftime('%Y-%m-%d %H:%M:%S')
        try:
            with connection.cursor() as cursor:
                sql = ( "SELECT s.`start` as start_date FROM statistics s "
                        "JOIN statistics_meta sm on s.metadata_id = sm.id "
                        "WHERE sm.statistic_id = %s "
                        "AND s.`start` = %s "
                        "ORDER BY DATE(s.`start`);")

                cursor.execute(sql, (eon_type, date_tmp))
                rows = cursor.fetchall()
        except Exception as err:
            self.log(f"get_statistics_by_date: {err}")
        finally:
            connection.close()
            return rows


    def get_statistics_by_date(self, eon_type, date):
        connection = pymysql.connect(host=self.args['host'],
                                    user=self.args['username'],
                                    password=self.args['password'],
                                    db=self.args['database'],
                                    charset='utf8mb4',
                                    cursorclass=pymysql.cursors.DictCursor)

        try:
            with connection.cursor() as cursor:
                sql = ( "SELECT s.`start` as start_date FROM statistics s "
                        "JOIN statistics_meta sm on s.metadata_id = sm.id "
                        "WHERE sm.statistic_id = %s "
                        "AND DATE(s.`start`) = %s "
                        "ORDER BY DATE(s.`start`);")

                cursor.execute(sql, (eon_type, date.strftime('%Y-%m-%d 00:00:00')))
                rows = cursor.fetchall()
        except Exception as err:
            self.log(f"get_statistics_by_date: {err}", level="ERROR")
        finally:
            connection.close()
            return rows

    def get_metadata_id(self, eon_type):
        connection = pymysql.connect(host=self.args['host'],
                                    user=self.args['username'],
                                    password=self.args['password'],
                                    db=self.args['database'],
                                    charset='utf8mb4',
                                    cursorclass=pymysql.cursors.DictCursor)

        try:
            with connection.cursor() as cursor:
                sql = ( "SELECT id, statistic_id, source, unit_of_measurement FROM statistics_meta "
                        "WHERE statistic_id = %s;")

                cursor.execute(sql, eon_type)
                row = cursor.fetchone()
        except Exception as err:
            self.log(f"get_metadata_id: {err}", level="ERROR")
        finally:
            connection.close()
            return row

    def set_dummy_value_to_statistics(self, metadata_id, start_datetime):
        connection = pymysql.connect(host=self.args['host'],
                                    user=self.args['username'],
                                    password=self.args['password'],
                                    db=self.args['database'],
                                    charset='utf8mb4',
                                    cursorclass=pymysql.cursors.DictCursor)

        current_date = datetime.datetime.now().date()
        start_date = start_datetime.date()
        if (current_date == start_date):
            return

        created_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        start_date = start_datetime.strftime('%Y-%m-%d %H:%M:%S')
        last_reset = "2020-11-11 11:25:00"

        try:
            with connection.cursor() as cursor:
                sql = ( "INSERT INTO statistics "
                        "(created, metadata_id, `start`, last_reset) "
                        "VALUES(%s, %s, %s, %s);")

                cursor.execute(sql, (created_date, int(metadata_id), start_date, last_reset))
                connection.commit()
        except Exception as err:
            self.log(f"set_dummy_value_to_statistics: {err}", level="ERROR")
        finally:
            connection.close()

    def normalize_data(self, eon_type, date):
        rows = self.get_states(eon_type, date)
        first_state = self.get_first_state(eon_type)
        first_state_value = round(float(first_state['state']), 3)

        for idx, row in enumerate(rows):
            fixed_state = round(float(row['fixed_state']), 3)
            row['state'] = fixed_state
            sum_state = fixed_state - first_state_value
            row['sum_state'] = round(sum_state, 3)
            self.set_sum_and_state(eon_type, row['statistic_id'], row['sum_state'], fixed_state, row['start_date'])


    def get_first_state(self, eon_type):
        connection = pymysql.connect(host=self.args['host'],
                                    user=self.args['username'],
                                    password=self.args['password'],
                                    db=self.args['database'],
                                    charset='utf8mb4',
                                    cursorclass=pymysql.cursors.DictCursor)

        try:
            with connection.cursor() as cursor:
                sql = ( "SELECT s.state, s.sum as sum_state FROM statistics s "
                        "JOIN statistics_meta sm on s.metadata_id = sm.id "
                        "WHERE sm.statistic_id = %s "
                        "AND s.state IS NOT NULL "
                        "ORDER BY s.state;")
                input = (eon_type)
                cursor.execute(sql, input)
                row = cursor.fetchone()
        except Exception as err:
            self.log(f"ERROR - get_first_state: {err}", level="ERROR")
        finally:
            connection.close()
            return row


    def set_sum_and_state(self, eon_type, statistic_id, sum_state, state, start_date):
        connection = pymysql.connect(host=self.args['host'],
                                    user=self.args['username'],
                                    password=self.args['password'],
                                    db=self.args['database'],
                                    charset='utf8mb4',
                                    cursorclass=pymysql.cursors.DictCursor)
        try:
            self.log(f"{eon_type} - {statistic_id} set_sum_and_state: {str(sum_state)} - {str(state)} - {start_date.strftime('%Y-%m-%d %H:%M')}", level="INFO")
            with connection.cursor() as cursor:
                sql = """UPDATE statistics SET sum = %s, state = %s WHERE id = %s"""
                input = (sum_state, state, statistic_id)
                cursor.execute(sql, input)
                connection.commit()
        except Exception as err:
            self.log(f"ERROR - set_sum_and_state: {err}", level="ERROR")
        finally:
            connection.close()


    def get_states(self, eon_type, date):
        self.log("START - get_states")
        # Connect to the database
        connection = pymysql.connect(host=self.args['host'],
                                    user=self.args['username'],
                                    password=self.args['password'],
                                    db=self.args['database'],
                                    charset='utf8mb4',
                                    cursorclass=pymysql.cursors.DictCursor)

        final_since_time = datetime.datetime.combine(date, datetime.datetime.min.time()) - datetime.timedelta(hours=4)
        final_since = final_since_time.strftime('%Y-%m-%d %H:%M:%S')
        final_until_time = final_since_time + datetime.timedelta(hours=25) + datetime.timedelta(minutes=59)
        final_until = final_until_time.strftime('%Y-%m-%d %H:%M:%S')

        try:
            with connection.cursor() as cursor:
                sql = ( "SELECT s.id as statistic_id, s.created as created, s.`start` as start_date, s.state as state, s.sum as sum_state, sm.statistic_id as statistic_id, fixed.state as fixed_state FROM statistics s "
                        "join statistics_meta sm on s.metadata_id = sm.id "
                        "join states fixed on fixed.entity_id = sm.statistic_id AND fixed.last_changed = DATE_ADD(s.`start`, INTERVAL 1 DAY_HOUR) "
                        "WHERE sm.statistic_id = %s "
                        "AND s.`start` between %s and %s "
                        "ORDER BY `start`;")

                cursor.execute(sql, (eon_type, final_since, final_until))
                rows = cursor.fetchall()
        except Exception as err:
            self.log(f"ERROR - get_states: {err}", level="ERROR")
        finally:
            connection.close()
            return rows