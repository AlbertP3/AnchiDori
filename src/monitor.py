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
    target_url:str = ''



class Monitor:
    '''Used for scheduling and monitoring execution of Queries'''

    def __init__(self, username):
        self.username = username
        self.queries = dict()
        self.aliases = set()
        self.date_fmt = '%Y-%m-%d %H:%M:%S'
        self.db_conn = db_connection()

    async def add_query(self, d:dict):
        if d['alias'] in self.aliases:
            register_log(f"Query not added due to duplicate alias:{d['alias']} Query:{d['url']}")
            return False
        d['found'], d['eta'], d['last_run'], d['is_recurring'] = await self.validate_query(d.get('found',False), 
                                                                d['eta'], d.get('last_run',datetime(1970,1,1)), d['is_recurring'])
        cookies = await self.db_conn.try_get_json(self.username, d['cookies_filename'])
        d['query'] = Query(url=d['url'], sequence=d['sequence'], cookies=cookies)
        self.queries[d['url']] = d
        register_log(f"Query added: {d['url']}: {self.queries[d['url']]}")
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
            r = await get_randomization(q['interval'], q['randomize'], q['eta'])
            if (not q['found'] or q['is_recurring']) and q['cycles'] < q['cycles_limit'] and q['last_run'] + timedelta(minutes=q['interval']+r) <= datetime.now():
                q['found'] = await q['query'].run()
                q['last_run'] = datetime.now()
                q['cycles']+=1
                query_was_run = True
            res[k] = serialize(q)
        perf_time = 1000*(monotonic()-start)
        if query_was_run: register_log(f'Scan took total of {perf_time:.0f}ms and on average {safe_division(perf_time, len(self.queries)):.0f}ms per query')
        return res

    async def clean_queries(self):
        new_queries = dict()
        for k, v in self.queries.items():
            if not v['found']: 
                # Avoid RuntimeError: dictionary changed size during iteration
                new_queries[k] = v
            else:
                register_log(f"Removed query: {k}")
        self.queries = new_queries
