from aiohttp import web
import asyncio
from datetime import datetime
import logging
import traceback
from common.utils import boolinize
from server.utils import singleton, gen_token
from server import config
from server.db_conn import db_connection
from server.monitor import Monitor
import server.query


LOGGER = logging.getLogger('UserManager')


@singleton
class UserManager:
    '''Singleton that handles users sessions'''

    def __init__(self):
        self.db_conn = db_connection()  # TODO replace with an authentication service
        self.sessions = dict()


    async def run(self):
        '''Allows operations on users such as autosave or logout'''
        i = float(config['user_manager_interval'])*60
        while True:
            for user, data in self.sessions.items():
                # TODO
                LOGGER.info(f"[{user}] last_active: {data['last_active']}")
            await asyncio.sleep(i)


    async def register_new_user(self, username:str, password:str):
        await self.db_conn.create_new_user(username, password)


    async def auth_user(self, username, token) -> bool:
        '''use session token to verify user request'''
        try:
            auth = self.sessions[username]['token'] == token
            self.sessions[username]['last_active'] = datetime.now()
        except KeyError:
            auth = False
        return auth


    async def login(self, username:str, password:str):
        '''Run UserManager on first user login'''
        asyncio.ensure_future(self.run(), loop=asyncio.get_event_loop())
        self.login = self.__login
        return await self.login(username, password)

  
    async def __login(self, username:str, password:str):
        '''Handle whole login process'''
        token = ''
        auth_success:bool = await self.db_conn.auth_user_credentials(username, password)
        if auth_success:
            if not self.sessions.get(username, False):
                token = gen_token()
                self.sessions[username] = dict(monitor=Monitor(username), last_active=datetime.now(), token=token)
                self.sessions[username]['settings'] = await self.db_conn.load_settings(username)
                LOGGER.info(f"[{username}] authenticated user")
                await self.populate_monitor(username)
            else:
                # Restore session for once-logged user
                token = self.sessions[username]['token']
                LOGGER.info(f'[{username}] restored session')
        else:
            LOGGER.warning(f"[{username}] denied access - invalid credentials")
        return auth_success, token


    async def populate_monitor(self, username:str):
        s, msg = await self.sessions[username]['monitor'].populate()
        return s, msg


    async def reload_cookies(self, username:str, cookies:dict):
        return await self.sessions[username]['monitor'].reload_cookies(cookies)


    async def save_dashboard(self, username):
        s, msg = await self.sessions[username]['monitor'].save()
        return s, msg


    async def remove_completed_queries(self, username):
        LOGGER.info(f'Removing queries for user: {username}')
        await self.sessions[username]['monitor'].clean_queries()

    
    async def delete_query(self, username, uid) -> tuple[bool, str]:
        try:
            res, msg = await self.sessions[username]['monitor'].delete_query(uid)
            return res, msg
        except KeyError:
            return False, 'Requested query does not exist'


    async def get_query(self, username, uid) -> dict:
        try:
            msg = self.sessions[username]['monitor'].queries[uid]
            res = True
        except KeyError:
            msg = dict(msg='Requested query does not exist')
            res = False
        return res, msg

    async def get_all_queries(self, username) -> dict:
        res = self.sessions[username]['monitor'].queries
        LOGGER.debug(f'[{username}] returning all {len(res)} queries')
        return res

    async def edit_query(self, username, data):
        res, msg = await self.sessions[username]['monitor'].edit_query(data)
        if res:
            LOGGER.info(f"[{username}] edited Query: {data['alias']}")
        else:
            LOGGER.warning(f"[{username}] failed to edit Query: {data['alias']}. Reason: {msg}")
        return res, msg

    async def reload_config(self, data):
        LOGGER.info(f"[{data['username']}] scheduled Config reload")
        config.refresh()
        for user in self.sessions.values():
            for qp in user['monitor'].queries.values():
                qp['query'].do_dump_page_content = boolinize(config['dump_page_content'])
        server.query.captcha_kw = set(config['captcha_kw'].lower().split(';'))

    async def get_sound_file(self, username, sound):
        f, fname = await self.sessions[username]['monitor'].get_sound_file(sound)
        return f, fname

    async def add_query(self, username, data) -> tuple[bool, dict]:
        res, msg = await self.sessions[username]['monitor'].add_query(data)
        if res:
            LOGGER.info(f"[{data['username']}] added Query {data['url']}")
        return res, msg



user_manager = UserManager()
async def _get_auth(data:dict) -> tuple:
    try:
        username = data['username']
        auth = await user_manager.auth_user(username, data['token'])
        return username, auth
    except KeyError:
        return 'Unknown User', False

def require_login(func):
    async def wrapper(*args, **kw):
        data = await args[0].json()
        username, authenticated = await _get_auth(data)
        if authenticated:
            LOGGER.debug(f"[{username}] responding to request {func.__name__} with args: {data}")
            return await func(*args, **kw)
        else:
            LOGGER.debug(f"[{username}] Access Denied")
            return web.json_response(dict(success=False, msg='Access Denied'))
    return wrapper

