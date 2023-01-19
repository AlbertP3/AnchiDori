from aiohttp import web
from common import register_log
from datetime import datetime
from monitor import Monitor
from users import UserManager

user_manager = UserManager()
routes = [
    web.get('/get_dashboard', lambda req: get_dashboard(req)),
    web.get('/auth', lambda req: login_user(req)),
    web.post('/add_query', lambda req: add_query_to_dashboard(req)),
    web.get('/verify_session', lambda req: verify_session(req)),
    web.post('/save', lambda req: save_queries(req)),
    web.post('/clean', lambda req: clean_completed(req)),
    web.get('/get_query', lambda req: get_query(req)),
    web.get('/edit_query', lambda req: edit_query(req)),
    web.post('/refresh_data', lambda req: refresh_data(req)),
]

async def get_auth(data:dict) -> tuple[str, bool]:
    username = data['username']
    password = data.get('password')
    auth = await user_manager.auth_user(username, password) if password else False
    return username, auth


async def get_dashboard(request):
    data = await request.json()
    username, auth = await get_auth(data)
    if auth:
        resp = await user_manager.sessions[username]['monitor'].scan()
        return web.json_response(resp)
    else:
        register_log(f'Access Denied for User: {username}')
        return web.Response(status=403)


async def add_query_to_dashboard(request):
    data = await request.json()
    username, auth = await get_auth(data)
    if auth:
        res = await user_manager.sessions[username]['monitor'].add_query(data)
        return web.json_response(dict(success=res))
    else:
        register_log(f'Access Denied for User: {username}')
        return web.Response(status=403)


async def login_user(request:web.Request):
    data = await request.json()
    username, password = data['username'], data['password']
    auth_success = await user_manager.login(username, password)
    res = dict(
        username = username,
        auth_success = auth_success
    )
    return web.json_response(res)


async def verify_session(request:web.Request):
    data = await request.json()
    username, auth = await get_auth(data)
    msg = 'User authenticated' if auth else 'Invalid session credentials'
    register_log(f'Verification for session of user {username} -> {"Accepted" if auth else "Denied"}')
    return web.json_response(dict(success=auth, msg=msg))


async def save_queries(request:web.Request):
    data = await request.json()
    username, auth = await get_auth(data)
    if auth:
        await user_manager.save_dashboard(username)
        return web.json_response(dict(success=auth, msg='Saved queries to database'))
    else:
        return web.json_response(dict(success=auth, msg='Access Denied'))


async def clean_completed(request:web.Request):
    data = await request.json()
    username, auth = await get_auth(data)
    if auth:
        await user_manager.remove_completed_queries(username)
        return web.json_response(dict(success=auth, msg='Completed Queries were removed'))
    return web.json_response(dict(success=auth, msg='Access Denied'))
    

async def get_query(request:web.Request):
    data = await request.json()
    username, auth = await get_auth(data)
    if auth:
        res = await user_manager.get_query(username, data['alias'])
        return web.json_response(res)
    return web.json_response(dict(success=auth, msg='Access Denied'))
    
    
async def edit_query(request:web.Request):
    data = await request.json()
    username, auth = await get_auth(data)
    if auth:
        await user_manager.edit_query(username, data)
        return web.json_response(dict(success=auth, msg='Query successfuly edited'))
    return web.json_response(dict(success=auth, msg='Access Denied'))


async def refresh_data(request:web.Request):
    data = await request.json()
    username, auth = await get_auth(data)
    if auth:
        await user_manager.populate_monitor(username)
        return web.json_response(dict(success=auth, msg='Data successfuly refreshed'))
    return web.json_response(dict(success=auth, msg='Access Denied'))
