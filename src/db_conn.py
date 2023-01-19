from string import Template
from common import *
import json
import os
import pandas as pd


@singleton
class db_connection:
    def __init__(self):
        self.PATH_DB = Template('./data/$usr/db.csv')
        self.PATH_COOKIES = Template('./data/$usr/cookies/$filename')


    async def auth_user_credentials(self, username, password):
        # TODO
        return username == 'sztywny' and password == '1'


    async def get_dashboard_data(self, username) -> dict[str, dict]:
        '''returns dict[url:dict[query_data]]'''
        res = pd.read_csv(self.PATH_DB.substitute(usr=username)).set_index('url').to_dict(orient='index')
        for k in res.keys():
            res[k]['url'] = k
        register_log(f"Loaded Dashboard Data for user: {username}, queries: {len(res)}")
        return res


    async def save_dashboard(self, username, data:dict):
        # remove Query objects from data
        d = {k:{k_s: v_s for k_s, v_s in v.items() if k_s!='query'} for k, v in data.items()}
        df = pd.DataFrame.from_records(list(d.values()))
        df.to_csv(self.PATH_DB.substitute(usr=username), index=False)
        register_log(f'Database for user {username} updated')


    async def save_cookies(self, username, queries):
        for k, v in queries.items():
            if v['cookies_filename'] and v['query'].cookies:
                await self.try_save_json(username, v['cookies_filename'], v['query'].cookies)
                register_log(f"Cookies updated for query: {k}")


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


    async def try_save_json(self, username, file_name, data:dict):
        try:
            with open(self.PATH_COOKIES.substitute(usr=username, filename=file_name), 'w') as file:
                json.dump(data, file, indent=4)
        except FileNotFoundError:
            pass

