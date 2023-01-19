import asyncio
from common import *
from aiohttp import web
import asyncio
from routes import routes
from users import UserManager


config = Config()
user_manager = UserManager()

async def init_server():
    app = web.Application()
    runner = web.AppRunner(app)
    app.router.add_routes(routes)
    await runner.setup()
    site = web.TCPSite(runner, config['server'], int(config['port']))
    await site.start()
    register_log(f'Started aiohttp server @ {config["server"]}:{config["port"]}')

async def shutdown_server():
    for username, session_params in user_manager.sessions.items():
        for url, q_v in session_params['monitor'].queries.items():
            await q_v['query'].close_session()
        register_log(f"Session for user {username} was closed successfuly")
            
if __name__ == '__main__':
    try:
        loop = asyncio.new_event_loop()
        srv_task = loop.create_task(init_server())
        loop.run_forever()
    except KeyboardInterrupt:
        asyncio.run(shutdown_server())
        register_log('Server shutdown...')


