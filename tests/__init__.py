# Save original classes
import server.query
Query = server.query.Query
import server.monitor
Monitor = server.monitor.Monitor

class fake_query:
    def __init__(self, *args, **kwargs) -> None:
        self.url = kwargs.get('url', 'empty-url')
        self.re_compilers = kwargs.get('sequence', 'empty-compilers')
        self.min_matches = kwargs.get('min_matches', 1)
    def run(self):
        return False, 0
    def dump_page_content(self):
        pass
    async def close_session(self):
        pass
server.query.Query = fake_query

class fake_monitor:
    def __init__(self, username) -> None:
        self.username = username
        self.queries = dict()
    async def add_query(self, d):
        return True, 'Query added successfully'
    async def edit_query(self, d):
        return True, 'Query edited successfully'
    async def restore_query(self, d):
        return True, f'Query restored: {d["alias"]}'
    async def scan(self):
        return dict(), 'Scanned Queries'
    async def clean_queries(self):
        return True, ''
    async def close_session(self):
        return True, ''
    async def save(self):
        return True, ''
    async def delete_query(self, uid):
        return True, 'Query Deleted'
    async def populate(self):
        return True, 'OK'
    async def reload_cookies(self, data):
        return True, 'OK'
    async def get_sound_file(self, sound):
        return '', 'soundfile.mp3'
server.monitor.Monitor = fake_monitor
server.monitor.Query = fake_query