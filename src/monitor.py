from query import Query
from dataclasses import dataclass
from datetime import datetime, timedelta
from time import monotonic
from common import *
from db_conn import db_connection

config = Config()

@dataclass
class query_parameters:
    query:Query
    interval:float  # in minutes
    randomize:int = 0
    eta:datetime = None
    mode:str = 'exists'
    cycles_limit:int = 99
    cycles:int = 0
    last_run:datetime = datetime(1970, 1, 1)
    found:bool = False
    is_recurring:bool = False
    cookies_filename:dict = None
    alias:str = ''
    local_sound:str = ''

    def serialize(self) -> dict:
        '''Prepare object to be sent as a web response'''
        return dict(
            url = self.__dict__['query'].url,
            sequence = self.__dict__['query'].sequence,
            interval = self.__dict__['interval'],
            randomize = self.__dict__['randomize'],
            eta = str(self.__dict__['eta']),
            mode = self.__dict__['mode'],
            cycles_limit = self.__dict__['cycles_limit'],
            cycles = self.__dict__['cycles'],
            last_run = str(self.__dict__['last_run']),
            found = self.__dict__['found'],
            is_recurring = self.__dict__['is_recurring'],
            cookies_filename = self.__dict__['cookies_filename'],
            alias = self.__dict__['alias'],
            local_sound = self.__dict__['local_sound'],
        )

async def create_query_from_dict(data:dict) -> dict:
    '''Creates a dict of named parameters meant to be used as **input to the add_query function'''
    return dict(
            url=data['url'], 
            sequence=data['sequence'], 
            interval=data['interval'], 
            randomize=data['randomize'], 
            eta=data['eta'], 
            mode=data['mode'], 
            cycles_limit=data['cycles_limit'], 
            cycles=data.get('cycles', 0),
            last_run=data.get('last_run', datetime(1970,1,1)),
            found=data.get('found', False),
            is_recurring=data['is_recurring'], 
            cookies_filename=data['cookies_filename'],
            alias=data['alias'],
            local_sound=data['local_sound'], 
        )
    

class Monitor:
    '''Used for scheduling and monitoring execution of Queries'''

    def __init__(self, username):
        self.username = username
        self.queries = dict()
        self.aliases = set()
        self.date_fmt = config['date_fmt']
        self.db_conn = db_connection()

    async def add_query(self, url, sequence:str, interval, randomize, eta, mode, cycles_limit, 
                        cycles=0, last_run=datetime(1970,1,1), found=False, is_recurring=False, cookies_filename=None, alias=None, local_sound=None):
        alias = alias or url
        if alias in self.aliases:
            register_log(f"Query not added due to duplicate alias:{alias} Query:{url}")
            return False
        found, eta, last_run, is_recurring = await self.validate_query(found, eta, last_run, is_recurring)
        cookies = await self.db_conn.try_get_json(self.username, cookies_filename)
        self.queries[url] = query_parameters(Query(url, sequence, cookies), float(interval), int(randomize), eta, mode, 
                                             int(cycles_limit), int(cycles), last_run, found, is_recurring, cookies_filename, alias, local_sound)
        register_log(f'Query added: {url}: {self.queries[url]}')
        return True

    async def validate_query(self, found, eta, last_run, is_recurring):
        if isinstance(found, str): found = boolinize(found.lower())
        if isinstance(is_recurring, str): is_recurring = boolinize(is_recurring.lower())
        if isinstance(eta, str): 
            try: eta = datetime.strptime(eta, self.date_fmt)
            except ValueError: eta = None
        if isinstance(last_run, str):
            try: last_run = datetime.strptime(last_run, self.date_fmt)
            except ValueError: last_run = datetime(1970,1,1)
        return found, eta, last_run, is_recurring

    async def scan(self):
        '''Performs a run of scheduled queries and returns results'''
        #register_log(f'Running Scan for {len(self.queries)} queries')
        query_was_run = False
        start = monotonic()
        res = dict()
        for k, q in self.queries.items():
            r = await get_randomization(q.interval, q.randomize, q.eta)
            if (not q.found or q.is_recurring) and q.cycles < q.cycles_limit and q.last_run + timedelta(minutes=q.interval+r) <= datetime.now():
                q.found = await q.query.run()
                q.last_run = datetime.now()
                q.cycles+=1
                query_was_run = True
            res[k] = q.serialize()
        perf_time = 1000*(monotonic()-start)
        if query_was_run: register_log(f'Scan took total of {perf_time:.0f}ms and on average {safe_division(perf_time, len(self.queries)):.0f}ms per query')
        return res

    async def clean_queries(self):
        new_queries = dict()
        for k, v in self.queries.items():
            if not v.found: 
                # Avoid RuntimeError: dictionary changed size during iteration
                new_queries[k] = v
            else:
                register_log(f"Removed query: {k}")
        self.queries = new_queries
