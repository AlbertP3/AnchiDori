from collections import ChainMap
import traceback
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
        # Verify Parameters
        s, msg = parse_serialized(d)
        if not s: return False, msg
        is_valid, msg = await self.validate_params(d)
        if not is_valid: return False, msg
        # Create Query
        cookies, d['cookies_filename'] = await self.db_conn.setdefault_cookie_file(username=self.username, filename=d['cookies_filename'])
        d['query'] = Query(url=d['url'], sequence=d['sequence'], cookies=cookies, min_matches=d['min_matches'], mode=d['mode'])
        self.queries[d['uid']] = d
        return True, msg

    async def validate_params(self, d:dict) -> tuple[bool, str]:
        '''Validate Query dict parameters in-place, set defaults where needed'''
        # Verify required parameters
        if any(d.get(k) in {None, ''} for k in {'url', 'sequence', 'interval'}):
            return False, 'Query missing required parameters'
        d.setdefault('alias', d['url'])
        # Preclude duplicating aliases
        if d['alias'] in self.aliases:
            return False, f"Query not added due to duplicate alias: {d['alias']}"
        self.aliases.add(d['alias'])
        # Set defaults where not provided
        d.setdefault('uid', self.create_unique_uid())
        d.setdefault('cookies_filename', None)
        d.setdefault('randomize', 0)
        d.setdefault('eta', None)
        d.setdefault('mode', 'exists')
        d.setdefault('cycles_limit', 0)
        d.setdefault('cycles', 0)
        d.setdefault('last_run', self.DEFAULT_DATE)
        d.setdefault('found', False)
        d.setdefault('is_recurring', False)
        d.setdefault('target_url', d['url'])
        d.setdefault('alert_sound', None)
        d.setdefault('last_match_datetime', self.DEFAULT_DATE)
        d.setdefault('is_new', False)
        d.setdefault('min_matches', 1)
        d.setdefault('status', -1)
        return True, "Query added successfully"

    def create_unique_uid(self):
        return int(monotonic()*1000)

    async def edit_query(self, d:dict) -> tuple[bool, str]:
        try:
            uid = d['uid']
            # Verify parameters
            if uid not in self.queries.keys(): res, msg = False, 'Query does not exist'
            s, msg = parse_serialized(d)
            if not s: return False, msg
            # Update and recreate the Query
            await self.close_session(uid)
            self.queries[uid].update(d)
            cookies, self.queries[uid]['cookies_filename'] = await self.db_conn.setdefault_cookie_file(
                                                                username=self.username, 
                                                                filename=self.queries[uid]['cookies_filename'])
            self.queries[uid]['query'] = Query(url=self.queries[uid]['url'], 
                                                sequence=self.queries[uid]['sequence'], 
                                                cookies=cookies, 
                                                min_matches=self.queries[uid]['min_matches'], 
                                                mode=self.queries[uid]['mode'])
            res, msg = True, 'Query edited successfuly'
        except Exception as e:
            register_log(traceback.format_exc(), 'ERROR')
            res, msg = False, e.__class__.__name__
        return res, msg

    async def restore_query(self, d:dict):
        s, msg = parse_serialized(d)
        if not s: return False, msg
        cookies, d['cookies_filename'] = await self.db_conn.setdefault_cookie_file(username=self.username, filename=d['cookies_filename'])
        d['query'] = Query(url=d['url'], sequence=d['sequence'], cookies=cookies, min_matches=d['min_matches'], mode=d['mode'])
        self.queries[d['uid']] = d
        return True, f'Query restored: {d["alias"]}'

    async def scan(self) -> dict:
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
        if q['status'] != 0 and q['cycles_limit']>=0:
            main_c = True
        else:
            r = get_randomization(q['interval'], q['randomize'], q['eta'])
            main_c = (not q['found'] or q['is_recurring']) and \
                    (q['cycles'] < q['cycles_limit'] if q['cycles_limit'] != 0 else True) and \
                    q['last_run'] + timedelta(minutes=q['interval']+r) <= datetime.now() 
        if main_c:
            start = monotonic()
            prev_found = q['found']
            q['found'], q['status'] = q['query'].run()
            q['last_match_datetime'] = self.get_last_match_datetime(prev_found, q['found'], q['last_match_datetime'], q['is_recurring'])
            q['last_run'] = datetime.now()
            q['cycles']+=1
            q['is_new'] = True
            self.queries_run_counter+=1
            register_log(f"[{self.username}] ran query: {q['alias']} in {1000*(monotonic()-start):.0f}ms Found: {q['found']}, Status: {q['status']}")
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

