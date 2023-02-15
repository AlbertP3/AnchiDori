import asyncio
from common import *
from aiohttp import web
from routes import routes
from users import UserManager
from server.utils import config, register_log
from common.utils import boolinize
import ssl


user_manager = UserManager()

def get_ssl_context():
    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    pub = 'src/server/secrets/domain_srv.crt'
    priv = 'src/server/secrets/domain_srv.key'
    ssl_context.load_cert_chain(pub, priv)
    return ssl_context

async def shutdown_server(app):
    for username, session_params in user_manager.sessions.items():
        for uid, q_v in session_params['monitor'].queries.items():
            await q_v['query'].close_session()
        register_log(f"Session for user {username} was closed successfuly")
    register_log('Server shutdown')
            
if __name__ == '__main__':
    app = web.Application()
    app.add_routes(routes)
    app.on_shutdown.append(shutdown_server)
    ssl_context = get_ssl_context() if boolinize(config['secure']) else None
    register_log(f'Started aiohttp server @ {config["server"]}:{config["port"]}')
    web.run_app(app, host=config['server'], port=int(config['port']), ssl_context=ssl_context)
