from string import Template
import traceback
import json
import os
import pandas as pd
import re
import numpy as np
from copy import deepcopy
from urllib.parse import urlparse
from random import random
import logging

from common import *
from common.utils import boolinize
from server.utils import safe_date_fmt
from server import config, CWD

DATA_PATH = os.path.realpath(f'{CWD}/../../data')
LOGGER = logging.getLogger('Db_conn')


class db_connection:
    def __init__(self):
        self.PATH_DB = Template(DATA_PATH+'/$usr/db.csv')
        self.PATH_COOKIES = Template(DATA_PATH+'/$usr/cookies/$filename')
        self.PATH_SOUNDS = Template(DATA_PATH+'/$usr/sounds/$filename')
        self.PATH_SETTINGS = Template(DATA_PATH+'/$usr/settings.json')
        self.allowed_chars = 'qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM_1234567890'


    async def create_new_user(self, username, password):
        pass


    async def auth_user_credentials(self, username, password):
        # TODO
        return username == 'psyduck' and password == 'zxc'


    async def get_dashboard_data(self, username) -> dict[str, dict]:
        '''returns dict[uid:dict[query_data]]'''
        res:pd.DataFrame = pd.read_csv(self.PATH_DB.substitute(usr=username)).set_index('uid')
        res.replace({np.nan:None}, inplace=True)
        res = res.to_dict(orient='index')
        for k in res.keys():
            res[k]['uid'] = k
        return res


    async def save_dashboard(self, username, data:dict):
        d = await self._parse_data_for_saving(data)
        saved_queries = set()
        for uid in d.keys():
            saved_queries.add(d[uid]['alias'])
        df = pd.DataFrame.from_records(list(d.values()))
        df.to_csv(self.PATH_DB.substitute(usr=username), index=False)
        LOGGER.info(f"[{username}] updated database: {', '.join(saved_queries)}")

    async def _parse_data_for_saving(self, data) -> dict:
        '''Create parsed deepcopy of data, ready to be saved'''
        d = deepcopy(data)
        for uid in d.keys():
            d[uid]['last_run'] = safe_date_fmt(d[uid]['last_run'])
            d[uid]['last_match_datetime'] = safe_date_fmt(d[uid]['last_match_datetime'])
            d[uid]['eta'] = d[uid]['eta'].get('raw', '')
            try: 
                del d[uid]['query']
            except KeyError: 
                pass
        return d
    
    async def load_settings(self, username):
        return json.load(open(self.PATH_SETTINGS.substitute(usr=username), 'r'))

    async def save_settings(self, username, data:dict):
        try:
            json.dump(data, open(self.PATH_SETTINGS.substitute(usr=username), 'w'), indent=4)
            return True
        except Exception:
            LOGGER.error(traceback.format_exc())
            return False

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
            file_exists = os.path.isfile(self.PATH_COOKIES.substitute(usr=username, filename=str(cf)))
            if file_exists:
                success = await self.try_save_cookies_json(username, str(cf), cookies)
                if success:
                    LOGGER.info(f"[{username}] reloaded {len(cookies)} cookies for {cf}")


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
        except (FileNotFoundError, IsADirectoryError):
            LOGGER.error(traceback.format_exc())
            res = False
        return res


    async def create_cookies_file(self, username, filename:str):
        cookie_filename = await self.create_cookies_filename(filename, username)
        with open(self.PATH_COOKIES.substitute(usr=username, filename=cookie_filename), 'w') as file:
            json.dump(dict(), file, indent=4)
        LOGGER.info(f"[{username}] created Cookie file {cookie_filename}")
        return cookie_filename


    async def create_cookies_filename(self, filename, username) -> str:
        '''create a new, unique file name consisting only of allowed chars'''
        filename = str(filename).strip()
        stem = None
        if filename.endswith('.json'): filename = filename[:-5]

        if filename.startswith('http'):
            stem = urlparse(filename).hostname or 'cookie'
            if stem.startswith('www'): stem = stem[4:]
            stem = await self.to_plain_text(filename)
        elif filename:
            stem = await self.to_plain_text(filename)
        stem = stem or "cookie"
        while f'{stem}.json' in os.listdir(self.PATH_COOKIES.substitute(usr=username, filename='')):
            stem = f"{stem}_{int(random()*1000)}"
        return f"{stem}.json" 


    async def to_plain_text(self, text:str):
        return ''.join(re.split(rf'[^{self.allowed_chars}]+', text))


    async def load_notification_file(self, username:str, filename:str) -> tuple[bytes, str]:
        try:
            sound = open(self.PATH_SOUNDS.substitute(usr=username, filename=filename), 'rb').read()
            fname = filename
            LOGGER.info(f"[{username}] loaded notification sound: {filename}")
        except FileNotFoundError:
            # TODO fetch default sound from the universal data source instead of users
            sound = open(self.PATH_SOUNDS.substitute(usr=username, filename=config['default_sound']), 'rb').read()
            fname = config['default_sound']
            LOGGER.info(f"[{username}] failed loading notification sound: {filename}. Recoursing to default: {config['default_sound']}")
        return sound, fname
        