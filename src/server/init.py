import asyncio
from common import *
from aiohttp import web
from routes import routes
import logging
from users import UserManager
from server import CWD
from server.utils import config
from common.utils import boolinize
import ssl


user_manager = UserManager()
LOGGER = logging.getLogger('Server')

def get_ssl_context():
    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    pub = f'{CWD}/secrets/domain_srv.crt'
    priv = f'{CWD}/secrets/domain_srv.key'
    ssl_context.load_cert_chain(pub, priv)
    return ssl_context

async def shutdown_server(app):
    for username, session_params in user_manager.sessions.items():
        for uid, q_v in session_params['monitor'].queries.items():
            await q_v['query'].close_session()
        LOGGER.info(f"Session for user {username} closed successfuly")
    LOGGER.info('Server shutdown')
            
if __name__ == '__main__':
    app = web.Application()
    app.add_routes(routes)
    app.on_shutdown.append(shutdown_server)
    ssl_context = get_ssl_context() if boolinize(config['secure']) else None
    LOGGER.info(f'Started aiohttp server @ {config["server"]}:{config["port"]}')
    web.run_app(app, host=config['server'], port=int(config['port']), ssl_context=ssl_context)
