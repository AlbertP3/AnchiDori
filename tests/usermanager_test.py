from unittest import IsolatedAsyncioTestCase
from unittest.mock import Mock, MagicMock, AsyncMock
from datetime import datetime
from aiohttp import web

from . import fake_query
import server.query
server.query.Query = fake_query

from . import fake_monitor
from server.users import require_login
from common import *
from server.users import UserManager
from server.utils import config


login_count = 0


@require_login
async def _require_login(d:dict):
    d['login'] = 'conducted'
    global login_count
    login_count+=1
    return d

class fake_webrequest(dict):
    def __init__(self, data:dict):
        self.data = data
    async def json(self):
        return self.data



class Test_UserManager(IsolatedAsyncioTestCase):
    usermanager = UserManager()
    usermanager.db_conn.auth_user_credentials = AsyncMock(return_value=True)
    usermanager.db_conn.reload_cookies = AsyncMock()
    usermanager.db_conn.load_notification_file = AsyncMock(return_value=(str(), 'soundfile.mp3'))
    usermanager.db_conn.create_new_user = AsyncMock()

    def setUp(self) -> None:
        self.usermanager.sessions.clear()
        self.usermanager.db_conn.get_dashboard_data = AsyncMock(return_value=dict())
        return super().setUp()


    async def test_register_new_user(self):
        '''handle adding new user'''
        # TODO
    

    async def test_regirest_new_user_duplicate_name(self):
        '''abort creating new user if the username is already taken'''
        # TODO


    async def test_auth_user_1(self):
        '''auth user'''
        self.usermanager.sessions['testuser'] = dict(token='abc')
        auth = await self.usermanager.auth_user('testuser', 'abc')
        self.assertTrue(auth)
        auth = await self.usermanager.auth_user('testuser', 'cde')
        self.assertFalse(auth)
        auth = await self.usermanager.auth_user('testu', 'abc')
        self.assertFalse(auth)


    async def test_login_user_1(self):
        '''login user'''
        auth, token = await self.usermanager.login('testuser', 'qwerty123')
        self.assertTrue(auth)
        auth, token_1 = await self.usermanager.login('testuser', 'qwerty123')
        self.assertTrue(auth)
        self.assertEqual(token, token_1)
        self.assertTrue(await self.usermanager.auth_user('testuser', token))
        self.usermanager.db_conn.auth_user_credentials = AsyncMock(return_value=False)
        auth, token_2 = await self.usermanager.login('testuser', 'lkj456')
        self.assertFalse(auth)
        self.assertEqual(token_2, '')
        self.usermanager.db_conn.auth_user_credentials = AsyncMock(return_value=True)
        auth, token_2 = await self.usermanager.login('user', 'qwerty123')
        self.assertTrue(auth)
        self.assertNotEqual(token_2, token)


    async def test_populate_monitor_1(self):
        '''handle populate monitor'''
        fm = fake_monitor('testuser')
        fm.queries['abcuid'] = dict(alias='test')
        fm.queries['defuid'] = dict(alias='test')
        self.usermanager.sessions['testuser'] = dict(monitor=fm)
        data = dict(abc=dict(alias='a'), de=dict(alias='b'))
        self.usermanager.db_conn.get_dashboard_data = AsyncMock(return_value=data)
        s, msg = await self.usermanager.populate_monitor('testuser')
        self.assertTrue(s)


    async def test_populate_monitor_2(self):
        '''handle populate monitor - empty'''
        fm = fake_monitor('testuser')
        self.usermanager.sessions['testuser'] = dict(monitor=fm)
        self.usermanager.db_conn.get_dashboard_data = AsyncMock(return_value=dict())
        s, msg = await self.usermanager.populate_monitor('testuser')
        self.assertTrue(s)


    async def test_reload_cookies(self):
        '''reload cookies'''
        fm = fake_monitor('testuser')
        fm.queries['abcuid'] = dict(alias='test')
        self.usermanager.sessions['testuser'] = dict(monitor=fm)
        s, msg = await self.usermanager.reload_cookies('testuser', {})
        self.assertTrue(s, msg)

    
    async def test_save_dashboard(self):
        '''test saving dashboard'''
        fm = fake_monitor('testuser')
        fm.queries['abcuid'] = dict(alias='test')
        self.usermanager.sessions['testuser'] = dict(monitor=fm)
        s, msg = await self.usermanager.save_dashboard('testuser')
        self.assertTrue(s, msg)


    async def test_remove_completed_queries(self):
        '''check if handled properly'''
        fm = fake_monitor('testuser')
        fm.queries['abcuid'] = dict(alias='test')
        self.usermanager.sessions['testuser'] = dict(monitor=fm)
        await self.usermanager.remove_completed_queries('testuser')
    

    async def test_delete_query(self):
        '''check if handled properly''' 
        fm = fake_monitor('testuser')
        fm.queries['abcuid'] = dict(alias='test')
        self.usermanager.sessions['testuser'] = dict(monitor=fm)
        res, msg = await self.usermanager.delete_query('testuser', 'abcuid')
        self.assertTrue(res, msg)


    async def test_get_query_1(self):
        '''check if handled properly''' 
        fm = fake_monitor('testuser')
        fm.queries['abcuid'] = dict(alias='test')
        self.usermanager.sessions['testuser'] = dict(monitor=fm)
        res = await self.usermanager.get_query('testuser', 'abcuid')
        self.assertEqual(res['success'], True)
        self.assertEqual(res['alias'], 'test')
    

    async def test_get_query_2(self):
        '''check if handled properly - query does not exist''' 
        fm = fake_monitor('testuser')
        fm.queries['abcuid'] = dict(alias='test')
        self.usermanager.sessions['testuser'] = dict(monitor=fm)
        res = await self.usermanager.get_query('testuser', '__')
        self.assertEqual(res['success'], False)


    async def test_get_all_queries(self):
        '''get all queries'''
        self.usermanager.sessions['testuser'] = dict(monitor=fake_monitor('testuser'))
        res = await self.usermanager.get_all_queries('testuser')
        self.assertEqual(res, {})


    async def test_edit_query_1(self):
        '''check if handled properly'''
        fm = fake_monitor('test_user')
        fm.edit_query = AsyncMock(return_value=(True, 'success'))
        self.usermanager.sessions['test_user'] = dict(monitor=fm)
        res, msg = await self.usermanager.edit_query('test_user', dict(alias='test_alias'))
        self.assertTrue(res, msg)


    async def test_edit_query_2(self):
        '''check if handled properly - query does not exist'''
        fm = fake_monitor('test_user')
        fm.edit_query = AsyncMock(return_value=(False, 'error'))
        self.usermanager.sessions['test_user'] = dict(monitor=fm)
        res, msg = await self.usermanager.edit_query('test_user', dict(alias='test_alias'))
        self.assertFalse(res, msg)


    async def test_get_sound_file_1(self):
        '''check if handled properly'''
        fm = fake_monitor('testuser')
        self.usermanager.sessions['testuser'] = dict(monitor=fm)
        f, fname = await self.usermanager.get_sound_file('testuser', 'sound.mp3')
        self.assertEqual(f, str())
        self.assertEqual(fname, 'soundfile.mp3')


    async def test_reload_config(self):
        '''check if reloading config updates all parameters'''
        server.query.captcha_kw = MagicMock()
        dpc = config['dump_page_content']
        config['dump_page_content'] = '___'
        self.usermanager.sessions['testuser1'] = dict(monitor=fake_monitor('testuser1'), token='1', last_active=datetime.now())
        self.usermanager.sessions['testuser2'] = dict(monitor=fake_monitor('testuser2'), token='1', last_active=datetime.now())
        await self.usermanager.reload_config(dict(username='testuser'))
        self.assertIsInstance(server.query.captcha_kw, set)
        self.assertEqual(dpc, config['dump_page_content'])


    async def test_require_login_1(self):
        '''handle login user'''
        exp_login_count = login_count
        self.usermanager.sessions['testuser'] = dict(monitor=fake_monitor('test_user'), token='test_token', last_active=datetime(2023,1,1))
        
        # Invalid token
        res:web.Response = await _require_login(fake_webrequest(dict(username='test_user', token='wrong_token')))
        self.assertIsInstance(res, web.Response)
        res = res.body.decode()
        self.assertEqual(res, '{"success": false, "msg": "Access Denied"}')
        self.assertEqual(login_count, exp_login_count, 'Protected function was called despite failed login')
        self.assertEqual(self.usermanager.sessions['testuser']['last_active'], datetime(2023,1,1))
        
        # Correct login
        res = await _require_login(fake_webrequest(dict(username='testuser', token='test_token')))
        exp_login_count+=1
        self.assertIsInstance(res, dict)
        self.assertEqual(res['login'], 'conducted')
        self.assertEqual(login_count, exp_login_count)
        self.assertEqual(self.usermanager.sessions['testuser']['last_active'].minute, datetime.today().minute)
        self.assertEqual(self.usermanager.sessions['testuser']['last_active'].hour, datetime.today().hour)
        
        # Unknown User
        res:web.Response = await _require_login(fake_webrequest(dict(username='no_user', token='test_token')))
        self.assertIsInstance(res, web.Response)
        res = res.body.decode()
        self.assertEqual(res, '{"success": false, "msg": "Access Denied"}')
        self.assertEqual(login_count, exp_login_count, 'Protected function was called despite failed login')
