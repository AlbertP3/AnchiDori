from aiohttp import web
from datetime import datetime
import logging
from common.utils import boolinize
from server.utils import singleton, gen_token
from server import config
from server.db_conn import db_connection
from server.monitor import Monitor
import query


LOGGER = logging.getLogger('UserManager')


@singleton
class UserManager:
    '''Singleton that handles users sessions'''

    def __init__(self):
        self.db_conn = db_connection()
        self.sessions = dict()


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
        '''Handle whole login process'''
        token = ''
        auth_success:bool = await self.db_conn.auth_user_credentials(username, password)
        if auth_success:
            if not self.sessions.get(username, False):
                token = gen_token()
                self.sessions[username] = dict(monitor=Monitor(username), last_active=datetime.now(), token=token)
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
        '''Populate Monitor of the user with queries from the db'''
        queries = await self.db_conn.get_dashboard_data(username)
        aliases = set()
        for q in queries.values():
            res, msg = await self.sessions[username]['monitor'].restore_query(q)
            if res: aliases.add(q['alias'])
            else: LOGGER.warning(f"[{username}] Query restore failed: {msg}")
        added_q = self.sessions[username]['monitor'].queries
        exp_len = len(queries.values())
        msg = f"[{username}] restored {len(added_q)}/{exp_len} Queries: {', '.join(aliases)}"
        if len(added_q)==exp_len: LOGGER.info(msg)
        else: LOGGER.warning(msg)


    async def reload_cookies(self, username:str, cookies:dict):
        await self.db_conn.reload_cookies(username, cookies)


    async def save_dashboard(self, username):
        await self.db_conn.save_dashboard(username, self.sessions[username]['monitor'].queries)
        saved_cookies = await self.db_conn.save_cookies(username, self.sessions[username]['monitor'].queries)
        LOGGER.info(f"[{username}] saved cookies: {', '.join(saved_cookies)}")
        return True, 'Saved user data'


    async def remove_completed_queries(self, username):
        LOGGER.info(f'Removing queries for user: {username}')
        await self.sessions[username]['monitor'].clean_queries()

    
    async def delete_query(self, username, uid) -> tuple[bool, str]:
        res, msg = await self.sessions[username]['monitor'].delete_query(uid)
        return res, msg


    async def get_query(self, username, uid) -> dict:
        try:
            res = self.sessions[username]['monitor'].queries[uid]
            res['success'] = True
        except IndexError:
            res = dict(msg='Requested query does not exist', success=False)
        return res

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
        query.captcha_kw = set(config['captcha_kw'].lower().split(';'))

    async def get_sound_file(self, username, sound):
        try:
            f, fname = await self.db_conn.load_notification_file(username, sound)
        except Exception as e:
            LOGGER.error(f"[{username}] Exception occurred while loading the sound file: {sound}. Exception: {e}")
            f, fname = None, 'err'
        return f, fname



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

