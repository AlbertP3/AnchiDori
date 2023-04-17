from string import Template
import json
import os
import pandas as pd
import re
from datetime import datetime
from urllib.parse import urlparse
from random import random

from common import *
from common.utils import boolinize
from server.utils import config, register_log, singleton
from query import serialize

DATA_PATH = os.path.realpath(os.path.dirname(os.path.abspath(__file__))+'../../../data')

@singleton
class db_connection:
    def __init__(self):
        self.PATH_DB = Template(DATA_PATH+'/$usr/db.csv')
        self.PATH_COOKIES = Template(DATA_PATH+'/$usr/cookies/$filename')
        self.PATH_SOUNDS = Template(DATA_PATH+'/$usr/sounds/$filename')
        self.allowed_chars = 'qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM_1234567890'


    async def create_new_user(self, username, password):
        pass


    async def auth_user_credentials(self, username, password):
        # TODO
        return username == 'psyduck' and password == 'zxc'


    async def get_dashboard_data(self, username) -> dict[str, dict]:
        '''returns dict[uid:dict[query_data]]'''
        res:dict = pd.read_csv(self.PATH_DB.substitute(usr=username)).set_index('uid').to_dict(orient='index')
        for k in res.keys():
            res[k]['uid'] = k
            res[k]['last_run'] = datetime.strptime(res[k]['last_run'], config['date_fmt'])
            try:
                res[k]['eta'] = datetime.strptime(res[k]['eta'], config['date_fmt'])
            except (TypeError, ValueError):
                res[k]['eta'] = None
        return res


    async def save_dashboard(self, username, data:dict):
        # remove Query objects from data
        d = {k:serialize(v) for k, v in data.items()}
        saved_queries = set()
        for uid in d.keys():
            if boolinize(d[uid]['is_recurring']):
                d[uid]['found'] = False 
            saved_queries.add(d[uid]['alias'])
        df = pd.DataFrame.from_records(list(d.values()))
        df.to_csv(self.PATH_DB.substitute(usr=username), index=False)
        register_log(f"[{username}] updated database: {', '.join(saved_queries)}")


    async def save_cookies(self, username, queries) -> set:
        saved_cookies = set()
        for k, v in queries.items():
            success = await self.try_save_cookies_json(username, v['cookies_filename'], v['query'].cookies)
            if success:
                saved_cookies.add(v['cookies_filename'])
        return saved_cookies


    async def reload_cookies(self, username, cookies:dict):
        # cookies: dict[cookies_filename : dict[cookie_name : value]]
        for cf, cookies in cookies.items():
            file_exists = os.path.isfile(self.PATH_COOKIES.substitute(usr=username, filename=f'{cf}'))
            if file_exists:
                success = await self.try_save_cookies_json(username, f'{cf}', cookies)
                if success:
                    register_log(f"[{username}] reloaded {len(cookies)} cookies for {cf}")


    async def setdefault_cookie_file(self, username, filename:str) -> tuple[dict, str]:
        if filename in {None, ''}:
            return {}, filename
        try:
            with open(self.PATH_COOKIES.substitute(usr=username, filename=filename), 'r') as file:
                data = json.load(file)
        except FileNotFoundError:
            filename = await self.create_cookies_file(username, filename)
            data = dict()
        return data, filename


    async def try_save_cookies_json(self, username, file_name, data:dict):
        try:
            with open(self.PATH_COOKIES.substitute(usr=username, filename=file_name), 'w') as file:
                json.dump(data, file, indent=4)
            res = True
        except FileNotFoundError:
            res = False
        return res


    async def create_cookies_file(self, username, filename:str):
        filename = str(filename)
        if filename.endswith('.json'): filename = filename[:-5]

        if filename.startswith('http'):
            stem = urlparse(filename).hostname or 'cookie'
            if stem.startswith('www'): stem=''.join(re.split(rf'[^{self.allowed_chars}]+', stem[4:]))
        elif filename:
            stem = ''.join(re.split(rf'[^{self.allowed_chars}]+', filename))
        else:
            stem = f"cookie_{int(random()*10000)}"

        temp_stem = stem
        while f'{temp_stem}.json' in os.listdir(self.PATH_COOKIES.substitute(usr=username, filename='')):
            temp_stem = f"{stem}_{int(random()*1000)}"
        cookie_filename = f"{temp_stem}.json"

        with open(self.PATH_COOKIES.substitute(usr=username, filename=cookie_filename), 'w') as file:
            json.dump(dict(), file, indent=4)
        register_log(f"[{username}] created Cookie file {cookie_filename}")
        return cookie_filename
            

    async def load_notification_file(self, username:str, filename:str) -> tuple[bytes, str]:
        try:
            sound = open(self.PATH_SOUNDS.substitute(usr=username, filename=filename), 'rb').read()
            fname = filename
            register_log(f"[{username}] loaded notification sound: {filename}")
        except FileNotFoundError:
            # TODO fetch default sound from the universal data source instead of users
            sound = open(self.PATH_SOUNDS.substitute(usr=username, filename=config['default_sound']), 'rb').read()
            fname = config['default_sound']
            register_log(f"[{username}] failed loading notification sound: {filename}. Recoursing to default: {config['default_sound']}")
        return sound, fname
        