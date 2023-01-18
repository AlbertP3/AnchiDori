from string import Template
from common import *
import csv
import json
import os


@singleton
class db_connection:
    def __init__(self):
        self.PATH_DB = Template('./data/$usr/db.csv')
        self.PATH_COOKIES = Template('./data/$usr/cookies/$filename')


    async def auth_user_credentials(self, username, password):
        # TODO
        return username == 'sztywny' and password == '1'


    async def get_dashboard_data(self, username):
        res = list()
        with open(self.PATH_DB.substitute(usr=username), 'r') as file:
            for lines in csv.reader(file):
                res.append(lines)
        register_log(f"Loaded Dashboard Data for user: {username}, queries: {len(res)}")
        return res


    async def save_dashboard(self, username, queries):
        content = ""
        for k, v in queries.items():
            url = k
            sequence = '|'.join(v.query.sequence)
            interval = str(v.interval)
            randomize = str(v.randomize)
            eta = str(v.eta)
            mode = v.mode
            cycles_limit = str(v.cycles_limit)
            cycles = str(v.cycles)
            last_run = str(v.last_run)
            found = str(v.found)
            is_recurring = str(v.is_recurring)
            cookies_filename = str(v.cookies_filename)
            alias = str(v.alias)
            local_sound = str(v.local_sound)
            record = ','.join([url, sequence, interval, randomize, eta, mode,
                              cycles_limit, cycles, last_run, found, is_recurring, 
                                cookies_filename, alias, local_sound])
            content+=record+'\n'

        with open(self.PATH_DB.substitute(usr=username), 'w') as file:
            file.writelines(content)

        register_log(f'Database for user {username} updated')


    async def try_get_json(self, username, file_name, default=dict()) -> dict:
        if not file_name: return default
        try:
            with open(self.PATH_COOKIES.substitute(usr=username, filename=file_name), 'r') as file:
                data = json.load(file)
        except FileNotFoundError:
            register_log('try_get_json: requested file was not found')
            data = default
        except TypeError:
            register_log('try_get_json: requested file is None')
            data = default
        return data

