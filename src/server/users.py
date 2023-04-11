from aiohttp import web
from datetime import datetime
from common.utils import boolinize
from server.utils import singleton, register_log, config, gen_token
from server.query import serialize
from server.db_conn import db_connection
from server.monitor import Monitor
import query



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
        '''Hanle whole login process'''
        token = ''
        auth_success:bool = await self.db_conn.auth_user_credentials(username, password)
        if auth_success:
            if not self.sessions.get(username, False):
                token = gen_token()
                self.sessions[username] = dict(monitor=Monitor(username), last_active=datetime.now(), token=token)
                register_log(f"[{username}] authenticated user")
                await self.populate_monitor(username)
            else:
                # Restore session for once-logged user
                token = self.sessions[username]['token']
                register_log(f'[{username}] restored session')
        else:
            register_log(f"[{username}] denied access - invalid credentials", 'WARNING')
        return auth_success, token


    async def populate_monitor(self, username:str):
        '''Populate Monitor of the user with queries from the db'''
        queries = await self.db_conn.get_dashboard_data(username)
        aliases = set()
        for q in queries.values():
            res, msg = await self.sessions[username]['monitor'].restore_query(q)
            if res: aliases.add(q['alias'])
            else: register_log(f"[{username}] Query restore failed: {msg}")
        added_q = self.sessions[username]['monitor'].queries
        exp_len = len(queries.values())
        s = 'INFO' if len(added_q)==exp_len else 'ERROR'
        register_log(f"[{username}] restored {len(added_q)}/{exp_len} Queries: {', '.join(aliases)}", s)

    async def reload_cookies(self, username:str, cookies:dict):
        await self.db_conn.reload_cookies(username, cookies)


    async def save_dashboard(self, username):
        await self.db_conn.save_dashboard(username, self.sessions[username]['monitor'].queries)
        saved_cookies = await self.db_conn.save_cookies(username, self.sessions[username]['monitor'].queries)
        register_log(f"[{username}] saved cookies: {', '.join(saved_cookies)}")


    async def remove_completed_queries(self, username):
        register_log(f'Removing queries for user: {username}')
        await self.sessions[username]['monitor'].clean_queries()


    async def get_query(self, username, uid) -> dict:
        try:
            res = serialize(self.sessions[username]['monitor'].queries[uid])
            res['success'] = True
        except IndexError:
            res = dict(msg='Requested query does not exist', success=False)
        return res

    async def get_all_queries(self, username) -> dict:
        res = self.sessions[username]['monitor'].queries
        register_log(f'[{username}] returning all {len(res)} queries')
        return res

    async def edit_query(self, username, data):
        res, msg = await self.sessions[username]['monitor'].edit_query(data)
        if res:
            register_log(f"[{username}] edited Query: {data['alias']}")
        else:
            register_log(f"[{username}] failed to edit Query: {data['alias']}. Reason: {msg}", 'ERROR')
        return res, msg

    async def reload_config(self, data):
        register_log(f"[{data['username']}] scheduled Config reload")
        config.refresh()
        for user in self.sessions.values():
            for qp in user['monitor'].queries.values():
                qp['query'].do_dump_page_content = boolinize(config['dump_page_content'])
        query.captcha_kw = set(config['captcha_kw'].lower().split(';'))



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
            register_log(f"[{username}] responding to request {func.__name__} with args: {data}")
            return await func(*args, **kw)
        else:
            register_log(f"[{username}] Access Denied", 'WARNING')
            return web.json_response(dict(success=False, msg='Access Denied'))
    return wrapper

