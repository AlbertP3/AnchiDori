from string import Template
from random import randint
from uuid import uuid1
import logging
import os
import pandas as pd
from copy import deepcopy
from subprocess import Popen
from unittest import IsolatedAsyncioTestCase
from unittest.mock import Mock, MagicMock, AsyncMock
from datetime import datetime
from server.utils import config, safe_strptime
from common.utils import boolinize

import server.db_conn
CWD = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.realpath(f'{CWD}/data')

log = logging.getLogger('TEST')


class Test_dbconn(IsolatedAsyncioTestCase):
    testuser = 'testuser'
    dbc = server.db_conn.db_connection()
    dbc.PATH_DB = Template(DATA_PATH+'/$usr/db.csv')
    dbc.PATH_COOKIES = Template(DATA_PATH+'/$usr/cookies/$filename')
    dbc.PATH_SOUNDS = Template(DATA_PATH+'/$usr/sounds/$filename')

    def setUp(self) -> None:
        super().setUp()

    
    async def save_data(self, username, d:dict):
        '''Prepare data and save dashboard'''
        d = deepcopy(d)
        for uid in d.keys():
            d[uid]['eta'] = {'raw': d[uid]['eta']}
            d[uid]['last_run'] = safe_strptime(d[uid]['last_run'])
            d[uid]['last_match_datetime'] = safe_strptime(d[uid]['last_match_datetime'])
        await self.dbc.save_dashboard(username, d)

    
    async def test_create_new_user(self):
        '''Create new user or deny if username already taken'''
        # TODO
    
    async def test_auth_user_credentials(self):
        '''Test if user credentials are properly validated'''
        # TODO


    async def test_get_dashboard_1(self):
        '''Assert data is loaded properly'''
        data = await self.dbc.get_dashboard_data(self.testuser)
        self.assertIsInstance(data, dict)
        self.assertEqual([1265023673, 397998615, 618922513, 619005125], list(data.keys()), 'not all data was loaded')
        self.assertTrue((all(isinstance(x, (int,str,float)) for x in y.values()) for y in data.values()), 'forbidden types detected')


    async def test_save_dashboard_1(self):
        '''Assert data is saved properly'''
        uid = 619005125
        data = await self.dbc.get_dashboard_data(self.testuser)
        new_time = datetime.today().strftime(config['date_fmt'])
        data[uid]['last_run'] = new_time
        reversed_found = not boolinize(data[uid]['found'])
        data[uid]['found'] = reversed_found
        await self.save_data(self.testuser, data)

        data = await self.dbc.get_dashboard_data(self.testuser)
        self.assertEqual(data[uid]['last_run'], new_time)
        self.assertEqual(data[uid]['found'], reversed_found)


    async def test_parse_data_for_saving(self):
        d = await self.dbc._parse_data_for_saving(
            {6663241: dict(
                last_run = datetime(2023,3,14,15,5,23),
                last_match_datetime = datetime(1970,1,1,0,0,0),
                eta = {'raw': 'saturday;17-19:20'}
        )})
        self.assertEqual(d[6663241]['last_run'], '2023-03-14 15:05:23')
        self.assertEqual(d[6663241]['last_match_datetime'], '1970-01-01 00:00:00')
        self.assertEqual(d[6663241]['eta'], 'saturday;17-19:20')
        d = await self.dbc._parse_data_for_saving(
            {6663241: dict(
                last_run = '2023-03-14 15:05:23',
                last_match_datetime = '1970-01-01 00:00:00',
                eta = {}
        )})
        self.assertEqual(d[6663241]['last_run'], '2023-03-14 15:05:23')
        self.assertEqual(d[6663241]['last_match_datetime'], '1970-01-01 00:00:00')
        self.assertEqual(d[6663241]['eta'], '')

    async def test_save_dashboard_3(self):
        '''Assert target_url is not overwritten if empty'''
        data = await self.dbc.get_dashboard_data(self.testuser)
        await self.save_data(self.testuser, data)
        data = await self.dbc.get_dashboard_data(self.testuser)
        self.assertEqual(data[1265023673]['target_url'], None)
        self.assertEqual(data[397998615]['eta'], 'saturday,20-22')
        self.assertIsNotNone(data[619005125]['target_url'])


    async def test_reload_cookies_1(self):
        '''Assert loads file '''
        r1, r2 = randint(1, 100), str(uuid1())
        cookies = {'c1.json': dict(a=r1, b=r2)}
        await self.dbc.reload_cookies(self.testuser, cookies)
        res = pd.read_json(f"{DATA_PATH}/{self.testuser}/cookies/c1.json", typ='series').to_dict()
        self.assertEqual(res, cookies['c1.json'])
        self.assertIn('[testuser] reloaded 2 cookies for c1.json', rf"{open('logs/tests.log').readlines()}")


    async def test_try_save_cookies_1(self):
        '''Assert creates new file if not exists'''
        fn = str(uuid1())+'.json'
        d = dict(c=randint(0,100))
        await self.dbc.try_save_cookies_json(self.testuser, file_name=fn, data=d)
        res = pd.read_json(f"{DATA_PATH}/{self.testuser}/cookies/{fn}", typ='series').to_dict()
        self.assertEqual(res, d)
        Popen(f"rm {DATA_PATH}/{self.testuser}/cookies/{fn}", shell=True)


    async def test_setdefault_cookie_file_1(self):
        '''load existing file'''    
        res, filename = await self.dbc.setdefault_cookie_file(self.testuser, 'c1.json')
        data = pd.read_json(f"{DATA_PATH}/{self.testuser}/cookies/c1.json", typ='series').to_dict()
        self.assertEqual(filename, 'c1.json')
        self.assertEqual(res, data)


    async def test_setdefault_cookie_file_2(self):
        '''return if filename is empty'''
        res, filename = await self.dbc.setdefault_cookie_file(self.testuser, '')
        self.assertEqual(res, {})
        self.assertEqual(filename, '')


    async def test_setdefault_cookie_file_3(self):
        '''load new file'''
        fn = str(uuid1())+'.json'
        res, filename = await self.dbc.setdefault_cookie_file(self.testuser, f'{fn}')
        data = pd.read_json(f"{DATA_PATH}/{self.testuser}/cookies/{filename}", typ='series').to_dict()
        self.assertTrue(res==data=={})
        Popen(f"rm {DATA_PATH}/{self.testuser}/cookies/{filename}", shell=True)


    async def test_create_cookie_file_2(self):
        '''Create new cookie file if name is duplicate'''
        cf = await self.dbc.create_cookies_file(self.testuser, 'c1.json')
        self.assertNotEqual(cf, 'c1.json')
        Popen(f"rm {DATA_PATH}/{self.testuser}/cookies/{cf}", shell=True)


    async def test_create_cookies_filename(self):
        '''Assert filenames are created unique'''
        f = await self.dbc.create_cookies_filename('c2.json', self.testuser)
        self.assertEqual(f, 'c2.json')
        f = await self.dbc.create_cookies_filename('http://example.com/something', self.testuser)
        self.assertEqual(f, 'httpexamplecomsomething.json')
        f = await self.dbc.create_cookies_filename('', self.testuser)
        self.assertEqual(f, 'cookie.json')
        f = await self.dbc.create_cookies_filename('($@!', self.testuser)
        self.assertEqual(f, 'cookie.json')


    async def test_load_notification_file_1(self):
        '''Load sound file'''
        s, fname = await self.dbc.load_notification_file(self.testuser, 'notification.mp3')
        self.assertIsInstance(s, bytes, type(s))
        self.assertEqual(fname, 'notification.mp3')


    async def test_load_notification_file_2(self):
        '''Load default sound file'''
        s, fname = await self.dbc.load_notification_file(self.testuser, 'non.wav')
        self.assertIsInstance(s, bytes, type(s))
        self.assertEqual(fname, config['default_sound'])
