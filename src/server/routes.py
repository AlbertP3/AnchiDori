from aiohttp import web
from server.utils import register_log
from query import serialize
from users import user_manager, require_login

routes = [
    web.post('/get_dashboard', lambda req: get_dashboard(req)),
    web.post('/auth', lambda req: login_user(req)),
    web.post('/add_query', lambda req: add_query_to_dashboard(req)),
    web.post('/verify_session', lambda req: verify_session(req)),
    web.post('/save', lambda req: save_queries(req)),
    web.post('/clean', lambda req: clean_completed(req)),
    web.post('/get_query', lambda req: get_query(req)),
    web.post('/edit_query', lambda req: edit_query(req)),
    web.post('/refresh_data', lambda req: refresh_data(req)),
    web.post('/get_all_queries', lambda req: get_all_queries(req)),
    web.get('/ping', lambda req: ping(req)),
    web.post('/reload_config', lambda req: reload_config(req)),
]



@require_login
async def get_dashboard(request:web.Request):
    data = await request.json()
    resp = await user_manager.sessions[data['username']]['monitor'].scan()
    return web.json_response(resp)


@require_login
async def add_query_to_dashboard(request:web.Request):
    data = await request.json()
    res = await user_manager.sessions[data['username']]['monitor'].add_query(data)
    if res:
        register_log(f"[{data['username']}] added Query {data['alias']}")
    else:
        register_log(f"[{data['username']}] failed adding Query {data['alias']}", 'ERROR')
    return web.json_response(dict(success=res))


async def login_user(request:web.Request):
    data = await request.json()
    username, password = data['username'], data['password']
    auth_success, token = await user_manager.login(username, password)
    res = dict(
        username = username,
        token = token,
        auth_success = auth_success
    )
    return web.json_response(res)


@require_login
async def verify_session(request:web.Request):
    data = await request.json()
    register_log(f'Verification for session of user {data["username"]} -> "Accepted"')
    return web.json_response(dict(success=True, msg='User authenticated'))


@require_login
async def save_queries(request:web.Request):
    data = await request.json()
    await user_manager.save_dashboard(data['username'])
    return web.json_response(dict(success=True, msg='Saved queries to database'))


@require_login
async def clean_completed(request:web.Request):
    data = await request.json()
    await user_manager.remove_completed_queries(data['username'])
    return web.json_response(dict(success=True, msg='Completed Queries were removed'))
    

@require_login
async def get_query(request:web.Request):
    data = await request.json()
    res = await user_manager.get_query(data['username'], data['uid'])
    return web.json_response(res)
    
    
@require_login
async def get_all_queries(request:web.Request):
    data = await request.json()
    res = await user_manager.get_all_queries(data['username'])
    res = {k:serialize(v) for k, v in res.items()}
    return web.json_response(res)


@require_login
async def edit_query(request:web.Request):
    data = await request.json()
    s, msg = await user_manager.edit_query(data['username'], data)
    return web.json_response(dict(success=s, msg=msg))


@require_login
async def refresh_data(request:web.Request):
    # Update cookies files and reload queries from source
    data = await request.json()
    await user_manager.reload_cookies(data['username'], data['cookies'])
    # await user_manager.populate_monitor(username)
    return web.json_response(dict(success=True, msg='Data successfuly refreshed'))


@require_login
async def reload_config(request:web.Request):
    data = await request.json()
    if data['passphrase'] == 'n9FQm0zcv$@SA':
        res = await user_manager.reload_config(data)
        res = dict(success=True, msg='Servers config file reloaded')
    else:
        res = dict(success=False, msg='Access Denied')
    return web.json_response(res)
    

async def ping(request:web.Request):
    register_log(f'Received ping')
    return web.json_response(dict(success=True))
