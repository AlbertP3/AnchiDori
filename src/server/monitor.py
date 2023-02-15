from collections import ChainMap
from concurrent.futures import ThreadPoolExecutor
from query import Query
from datetime import datetime, timedelta
from time import monotonic
from server.utils import config, register_log, get_randomization
from query import parse_serialized, serialize
from common.utils import boolinize
from db_conn import db_connection



class Monitor:
    '''Used for scheduling and monitoring execution of Queries'''

    def __init__(self, username):
        self.username = username
        self.queries = dict()
        self.aliases = set()
        self.db_conn = db_connection()
        self.DEFAULT_DATE = datetime(1970,1,1)
        self.queries_run_counter = 0

    async def add_query(self, d:dict):
        if d['alias'] in self.aliases:
            register_log(f"Query not added due to duplicate alias:{d['alias']}", 'WARNING')
            return False
        d['uid'] = d.get('uid', self.create_unique_uid())
        await self.close_session(d['uid'])
        d['found'], d['eta'], d['last_run'], d['is_recurring'], d['last_match_datetime'] = await self.validate_query(
                                                                d.get('found',False), d['eta'], d.get('last_run'), 
                                                                d['is_recurring'], d.get('last_match_datetime'))
        cookies, d['cookies_filename'] = await self.db_conn.try_get_cookies_json_else_create_new(username=self.username, filename=d['cookies_filename'])
        d = parse_serialized(d)
        d['query'] = Query(url=d['url'], sequence=d['sequence'], cookies=cookies, min_matches=d['min_matches'], mode=d['mode'])
        self.queries[d['uid']] = d
        return True

    async def validate_query(self, found, eta, last_run, is_recurring, last_match_datetime):
        if isinstance(found, str): found = boolinize(found.lower())
        if isinstance(is_recurring, str): is_recurring = boolinize(is_recurring.lower())
        if isinstance(eta, str): 
            try: eta = datetime.strptime(eta, config['date_fmt'])
            except ValueError: eta = None
        if not isinstance(last_run, datetime):
            try: last_run = datetime.strptime(last_run, config['date_fmt'])
            except (ValueError, TypeError): last_run = self.DEFAULT_DATE
        if not isinstance(last_match_datetime, datetime):
            try: last_match_datetime = datetime.strptime(last_match_datetime, config['date_fmt'])
            except (ValueError, TypeError): last_match_datetime = self.DEFAULT_DATE
        return found, eta, last_run, is_recurring, last_match_datetime

    def create_unique_uid(self):
        return int(monotonic()*1000)

    async def scan(self):
        '''Uses ThreadPoolExecutor to perform a run of scheduled queries and return results'''
        start_all = monotonic()
        self.queries_run_counter = 0
        with ThreadPoolExecutor() as executor:
            _res = executor.map(self._scan_one, self.queries.values())
        self.queries = dict(ChainMap(*reversed(list(_res))))  # merge list of dicts into a single dict, retaining order
        res = dict()
        for k, q in self.queries.items():
            res[k] = serialize(q)
        if self.queries_run_counter>1: 
            register_log(f"[{self.username}] scanned {self.queries_run_counter} queries in {(monotonic()-start_all)*1000:.0f}ms")
        return res

    def _scan_one(self, q):
        '''Runs a request for 1 query if conditions are met. Returns dict[uid:query_params]'''
        r = get_randomization(q['interval'], q['randomize'], q['eta'])
        cycles_condition = q['cycles'] < q['cycles_limit'] if q['cycles_limit'] != 0 else True
        if (not q['found'] or q['is_recurring']) and cycles_condition and q['last_run'] + timedelta(minutes=q['interval']+r) <= datetime.now():
            start = monotonic()
            prev_found = q['found']
            q['found'], q['message'] = q['query'].run()
            q['last_match_datetime'] = self.get_last_match_datetime(prev_found, q['found'], q['last_match_datetime'], q['is_recurring'])
            q['last_run'] = datetime.now()
            q['cycles']+=1
            q['is_new'] = True
            self.queries_run_counter+=1
            register_log(f"[{self.username}] ran query: {q['alias']} in {1000*(monotonic()-start):.0f}ms found: {q['found']}")
        else: 
            q['is_new'] = False
        return {q['uid']:q}

    def get_last_match_datetime(self, prev_found, found, last_match_datetime, recurring):
            if found or (recurring and not prev_found):
                return datetime.now()
            else:
                return last_match_datetime

    async def clean_queries(self):
        new_queries = dict()
        removed_queries = set()
        for k, v in self.queries.items():
            if not v['found'] or v['is_recurring']: 
                # Avoid RuntimeError: dictionary changed size during iteration
                new_queries[k] = v
            else:
                await self.close_session(k)
                removed_queries.add(v['alias'])
        register_log(f"[{self.username}] removed queries: {', '.join(removed_queries)}")
        self.queries = new_queries


    async def close_session(self, uid):
        try:
            await self.queries[uid]['query'].close_session()
            return True
        except KeyError:
            return False

