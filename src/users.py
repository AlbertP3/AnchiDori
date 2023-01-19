from datetime import datetime
from cryptography.fernet import Fernet
from common import *
from db_conn import db_connection
from monitor import Monitor


@singleton
class UserManager:
    '''Singleton that handles user sessions'''

    def __init__(self):
        self.db_conn = db_connection()
        self.sessions = dict()


    async def register_new_user(self, username:str, password:str):
        ...


    async def auth_user(self, username, password):
        try:
            auth = self.sessions[username]['password'] == password
            self.sessions[username]['last_active'] = datetime.now()
        except KeyError:
            auth = False
        return auth

    async def login(self, username:str, password:str):
        '''Hanle whole login process'''
        auth_success:bool = await self.db_conn.auth_user_credentials(username, password)
        if auth_success:
            register_log(f"Authenticated user: {username}")
            self.sessions[username] = dict(monitor=Monitor(username), last_active=datetime.now(), password=password)
            await self.populate_monitor(username)
        else:
            register_log(f"Denied access for user: {username} - invalid credentials")
        return auth_success


    async def populate_monitor(self, username:str):
        '''Populate Monitor of the user with queries from the db'''
        queries = await self.db_conn.get_dashboard_data(username)
        for q in queries.values():
            try:
                # try loading the cookies
                await self.sessions[username]['monitor'].add_query(q)
            except TypeError:
                register_log(f'TypeError occured while adding query: {q}')


    async def save_dashboard(self, username):
        await self.db_conn.save_dashboard(username, self.sessions[username]['monitor'].queries)
        await self.db_conn.save_cookies(username, self.sessions[username]['monitor'].queries)


    async def remove_completed_queries(self, username):
        register_log(f'Removing queries for user: {username}')
        await self.sessions[username]['monitor'].clean_queries()


    async def get_query(self, username, alias) -> dict:
        query = {k:v for k, v in self.sessions[username]['monitor'].queries.items() if v['alias'] == alias}
        try:
            url = list(query.keys())[0]
            res = serialize(query[url])
            res['success'] = True
        except IndexError:
            res = dict(msg='Requested query does not exist', success=False)
        register_log(res)
        return res


    async def edit_query(self, username, data):
        self.sessions[username]['monitor'].add_query(data)
