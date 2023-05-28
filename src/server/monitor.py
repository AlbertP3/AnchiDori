from collections import ChainMap
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from time import monotonic
import re
from uuid import uuid4
import logging
from server.utils import get_randomization, safe_strptime, timer, config, warn_set
from server.query import Query
from server.db_conn import db_connection
from common.utils import boolinize

LOGGER = logging.getLogger('Monitor')

class Monitor:
    '''Used for scheduling and monitoring execution of Queries'''

    def __init__(self, username):
        self.username = username
        self.queries = dict()
        self.db_conn = db_connection()
        self.DEFAULT_DATE = datetime(1970,1,1)
        self.MIN_INTERVAL = int(config['min_query_interval'])
        self.queries_run_counter = 0
        self._create_eta_dict()
        self.warnings = warn_set()
        
    def _create_eta_dict(self):
        '''create mapping {eta_parameter: tuple(regex_pattern, parsing_function)}'''
        dow = {'monday': 0,'tuesday': 1,'wednesday': 2,'thursday': 3,'friday': 4,'saturday': 5,'sunday': 6}
        dowj = '|'.join(dow.keys())
        dt = r"([0-2]?[0-9]|3[0-1])/([0-1]?[0-2]|0?[0-9])/[0-9]{4}"
        t = r"([0-1]?[0-9]|2[0-3])(:[0-5][0-9])?"
        self.eta_re = dict(
            dow       = (re.compile(f'^({dowj})$'),          lambda d: dow[d]                                                                       ),
            time_span = (re.compile(f'^{t}-{t}$'),           lambda d: tuple(tuple(int(c) for c in (t+':00').split(':')[:2]) for t in d.split('-')) ),
            dt_span   = (re.compile(f'^{dt}-{dt}$'),         lambda d: self._create_dt_span(d)                                                      ),
            dow_span  = (re.compile(f'^({dowj})-({dowj})$'), lambda d: tuple(dow[t] for t in d.split('-'))                                          ),
            dt        = (re.compile(f'^{dt}$'),              lambda d: tuple(int(c) for c in d.split('/'))                                          ),
        )

    def _create_dt_span(self, d:str) -> tuple:
        return tuple(datetime(**{k:int(v) for k,v in zip(['day', 'month', 'year'], t.split('/'))}) for t in d.split('-'))

    def _res_msg(self, base:str='', w_prefix:str=' with warnings: '):
        w = f"{w_prefix}{', '.join(self.warnings)}" if self.warnings else ''
        self.warnings.clear()
        return base + w

    async def add_query(self, d:dict) -> tuple[bool, str]:
        d, is_valid = await self._validate_query(d)
        if not is_valid: return False, self._res_msg('Query validation failed', 'with errors: ')
        cookies, d['cookies_filename'] = await self.db_conn.setdefault_cookie_file(username=self.username, filename=d['cookies_filename'])
        d['query'] = Query(url=d['url'], sequence=d['sequence'], cookies=cookies, min_matches=d['min_matches'], mode=d['mode'])
        self.queries[d['uid']] = d
        LOGGER.debug(f'[{self.username}] added Query: {self.queries[d["uid"]]}')
        return True, self._res_msg('Query added successfully')

    @timer
    async def _validate_query(self, d:dict) -> tuple[dict, bool]:
        '''return validated Query - remove unwanted data, check if required paramerters were provided,
           ensure parameters types and set defaults if missing '''

        # Preclude any unexpected parameters
        vd = dict()

        # Validate required parameters
        vd['url'] = await self._valpar(d, 'url',         exp_inst=str,   d_val=None)
        if not vd['url']: 
            self.warnings.add('Query missing required parameter: url')
            return vd, False
        vd['sequence'] = await self._valpar(d, 'sequence',    exp_inst=str,   d_val=None)
        if not vd['sequence']: 
            self.warnings.add('Query missing required parameter: sequence')
            return vd, False
        vd['interval'] = await self._valpar(d, 'interval',    exp_inst=int,   v_func=self._parse_interval, i=d.get('interval'))
        if not vd['interval']: 
            self.warnings.add('Query missing required parameter: interval')
            return vd, False

        # Verify unique alias
        vd['uid'] = await self._valpar(d, 'uid', exp_inst=str, d_func=self._create_uid)
        vd['alias'] = await self._valpar(d, 'alias', exp_inst=str, d_val=d['url'])
        if vd['alias'] in {v['alias'] for k,v in self.queries.items() if k!=vd['uid']}:
            self.warnings.add(f"Query not added due to duplicate alias: {vd['alias']}")
            return vd, False

        # Parse ETA
        vd['eta'] = await self._parse_eta(d.get('eta'))
        vd['cooldown'] = await self._parse_cooldown(d.get('cooldown', '0'), vd['interval'])
        
        # Setdefault other parameters
        vd['randomize'] =           await self._valpar(d, 'randomize',             exp_inst=int,               d_val=0                                   )
        vd['mode'] =                await self._valpar(d, 'mode',                  exp_inst=str,               d_val='exists'                            )
        vd['cycles_limit'] =        await self._valpar(d, 'cycles_limit',          exp_inst=int,               d_val=0                                   )
        vd['is_recurring'] =        await self._valpar(d, 'is_recurring',          exp_inst=boolinize,         d_val=False                               )
        vd['target_url'] =          await self._valpar(d, 'target_url',            exp_inst=str,               d_val=''                                  )
        vd['alert_sound'] =         await self._valpar(d, 'alert_sound',           exp_inst=str,               d_val=config['default_sound']             )
        vd['min_matches'] =         await self._valpar(d, 'min_matches',           exp_inst=int,               d_val=1, v_func=self._validate_min_matches)
        vd['cycles'] =              await self._valpar(d, 'cycles',                exp_inst=int,               d_val=0                                   )
        vd['last_run'] =            await self._valpar(d, 'last_run',              exp_inst=safe_strptime,     d_val=self.DEFAULT_DATE                   )
        vd['found'] =               await self._valpar(d, 'found',                 exp_inst=boolinize,         d_val=False                               )
        vd['last_match_datetime'] = await self._valpar(d, 'last_match_datetime',   exp_inst=safe_strptime,     d_val=self.DEFAULT_DATE                   )
        vd['is_new'] =              await self._valpar(d, 'is_new',                exp_inst=boolinize,         d_val=False                               )
        vd['status'] =              await self._valpar(d, 'status',                exp_inst=int,               d_val=-1                                  )
        vd['cookies_filename'] =    await self._valpar(d, 'cookies_filename',      exp_inst=str,               d_val=None,                                
                                                                                  d_func=self.db_conn.create_cookies_filename,                          
                                                                                  filename=vd['alias'], username=self.username                           )
        return vd, True

    async def _valpar(self, d, k, exp_inst:type=str, d_val=None, d_func=None, v_func=None, **kwargs):
        '''return validated Query parameter'''
        old = d.get(k)
        try:
            new_value = exp_inst(d[k]) if not v_func else await v_func(d[k])
            if exp_inst == str and not new_value.strip(): raise ValueError
        except (KeyError, TypeError, ValueError):
            try:
                new_value = await d_func(**kwargs) if d_func else d_val
                LOGGER.debug(f"[{self.username}] replaced invalid parameter '{k}' {old} --> {new_value}")
            except (TypeError, ValueError, AttributeError):
                LOGGER.debug(f"[{self.username}] failed to validate parameter: {k}")
                return d_val
        return new_value

    async def _parse_interval(self, i:str) -> int:
        res = await self._parse_time(str(i))
        if res < self.MIN_INTERVAL:
            res = self.MIN_INTERVAL 
            self.warnings.add(f'interval too low (min:{self.MIN_INTERVAL})')
        return res

    async def _parse_cooldown(self, c:str, i:int):
        c = await self._parse_time(str(c))
        return max(c, i)
    
    async def _parse_time(self, t:str) -> int:
        '''returns number of minutes from time-like string'''
        if t.endswith('h'):
            res = float(t[:-1])*60
        elif t.endswith('d'):
            res = float(t[:-1])*60*24
        else:
            res = float(t)
        return int(res)

    async def _create_uid(self) -> str:
        return str(uuid4())  

    async def _validate_min_matches(self, min_matches:str):
        return max(int(min_matches), 1)

    async def _parse_eta(self, eta) -> dict:
        '''create eta dict from string'''
        w = list()
        eta = eta.get('raw', '') if isinstance(eta, dict) else eta
        d = {'dow':[], 'dt':[], 'dow_span':[], 'dt_span':[], 'time_span':[], 'raw': eta or ''}
        if not eta or not isinstance(eta, str): return d
        for p in eta.lower().split(','):
            for k, v in self.eta_re.items():
                if v[0].search(p):
                    try:
                        d[k].append(v[1](p))
                    except (TypeError, IndexError, KeyError, AttributeError):
                        LOGGER.debug(f"[{self.username}] Invalid value for eta parser {k}: {p}")
                        w.append(p)
                    break
            else:
                LOGGER.debug(f"[{self.username}] ETA rule not found for {p}")
                w.append(p)
        w = f"invalid ETA rules: {', '.join(w)}" if w else ''
        self.warnings.add(w)
        return d

    async def edit_query(self, d:dict) -> bool:
        '''update existing query with new parameters (with validation)'''
        try:
            uid = d['uid']
            if uid not in self.queries.keys(): return False, 'Query does not exist'
            d = {**self.queries[uid], **d}
            d, s = await self._validate_query(d)
            if not s: return False, self._res_msg('Query edit failed', ' with errors: ')
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
            res, msg = True, self._res_msg('Query edited successfully')
        except Exception as e:
            LOGGER.error(traceback.format_exc())
            res, msg = False, e.__class__.__name__
        return res, msg

    async def restore_query(self, d:dict) -> tuple[bool, str]:
        d, s = await self._validate_query(d)
        if not s: return False, self._res_msg('Query restore failed', ' with errors: ')
        cookies, d['cookies_filename'] = await self.db_conn.setdefault_cookie_file(username=self.username, filename=d['cookies_filename'])
        d['query'] = Query(url=d['url'], sequence=d['sequence'], cookies=cookies, min_matches=d['min_matches'], mode=d['mode'])
        self.queries[d['uid']] = d
        return True, self._res_msg(f'Query restored: {d["alias"]}')

    async def scan(self) -> tuple[dict, str]:
        '''Uses ThreadPoolExecutor to perform a run of scheduled queries and return results'''
        start_all = monotonic()
        self.queries_run_counter = 0
        with ThreadPoolExecutor() as executor:
            _res = executor.map(self._scan_one, self.queries.values())
        self.queries = dict(ChainMap(*reversed(list(_res))))  # merge list of dicts into a single dict, retaining order
        if self.queries_run_counter>1: 
            LOGGER.info(f"[{self.username}] scanned {self.queries_run_counter} queries in {(monotonic()-start_all)*1000:.0f}ms")
        return self.queries, self._res_msg('Scanned Queries')

    def _scan_one(self, q) -> dict:
        '''Runs a request for 1 query if conditions are met. Returns dict[uid:query_params]'''
        if self._should_run(q):
            start = monotonic()
            prev_found = q['found']
            q['found'], q['status'] = q['query'].run()
            q['last_match_datetime'] = self._get_last_match_datetime(prev_found, q['found'], q['last_match_datetime'], q['is_recurring'])
            q['last_run'] = datetime.now()
            if q['status'] in {0, 1}:
                q['cycles']+=1
            q['is_new'] = True
            self.queries_run_counter+=1
            LOGGER.info(f"[{self.username}] ran query: {q['alias']} in {1000*(monotonic()-start):.0f}ms Found: {q['found']}, Status: {q['status']}")
        else: 
            q['is_new'] = False
        return {q['uid']:q}

    def _should_run(self, q:dict):
        if q['status'] in {-1, 2} and q['cycles_limit']>=0:
            res = True
        else:
            eta_c = self._eta_condition(q['eta'])
            res = eta_c and (not q['found'] or q['is_recurring']) and \
                (q['cycles'] < q['cycles_limit'] if q['cycles_limit'] != 0 else True) and \
                q['last_run'] + timedelta(minutes=q['cooldown'] if q['found'] \
                else (q['interval']+get_randomization(q['interval'], q['randomize']))) <= datetime.now() 
        return res

    def _get_last_match_datetime(self, prev_found, found, last_match_datetime, recurring):
            if found or (recurring and not prev_found):
                return datetime.now()
            else:
                return last_match_datetime

    def _eta_condition(self, eta:dict, n:datetime=None) -> bool:
        dow, time_span, dt, dt_span, dow_span = [True]*5
        n = n or datetime.now()

        for d in eta['dow']:
            dow = n.weekday() == d
            if dow: break
        if not dow: return False

        for d in eta['time_span']:
            time_span = d[0] <= (n.hour, n.minute) <= d[1]
            if time_span: break
        if not time_span: return False

        for d in eta['dt_span']:
            dt_span = d[0] <= n <= d[1]+timedelta(days=1)
            if dt_span: break
        if not dt_span: return False

        for d in eta['dow_span']:
            dow_span = d[0] <= n.weekday() <= d[1]
            if dow_span: break
        if not dow_span: return False

        for d in eta['dt']:
            dt = d == (n.day, n.month, n.year)
            if dt: break
        if not dt: return False
            
        return True
            
        
    async def clean_queries(self):
        new_queries = dict()
        removed_queries = set()
        for k, v in self.queries.items():
            if not v['found'] or v['is_recurring']: 
                new_queries[k] = v
            else:
                await self.close_session(k)
                removed_queries.add(v['alias'])
        self.queries = new_queries
        msg = f"[{self.username}] removed queries: {', '.join(removed_queries)}"
        LOGGER.info(msg)
        return True, msg

    async def delete_query(self, uid) -> tuple[bool, str]:
        try:
            alias = self.queries[uid]['alias']
            del self.queries[uid]
            LOGGER.info(f"[{self.username}] deleted query '{alias}'")
            return True, f"Query {alias} was removed"
        except KeyError:
            return False, f"Query with uid: {uid} does not exist"

    async def close_session(self, uid) -> tuple[bool, str]:
        try:
            await self.queries[uid]['query'].close_session()
            return True, f"Session closed for Query: {self.queries[uid]['alias']}"
        except KeyError:
            return False, f"Query with uid: {uid} does not exist"

    async def save(self) -> tuple[bool, str]:
        try:
            await self.db_conn.save_dashboard(self.username, self.queries)
            saved_cookies = await self.db_conn.save_cookies(self.username, self.queries)
            LOGGER.info(f"[{self.username}] saved cookies: {', '.join(saved_cookies)}")
            return True, 'Saved user data'
        except Exception as e:
            LOGGER.error(traceback.format_exc())
            return False, 'Failed saving Dashboard with Error: {e}'

    async def get_sound_file(self, sound):
        try:
            f, fname = await self.db_conn.load_notification_file(self.username, sound)
        except Exception as e:
            LOGGER.error(f"[{self.username}] Exception occurred while loading the sound file: {sound}. Exception: {e}")
            f, fname = None, 'err'
        return f, fname

    async def populate(self) -> tuple[bool, str]:
        '''Populate Monitor of the user with queries from the db'''
        queries = await self.db_conn.get_dashboard_data(self.username)
        aliases = list()
        for q in queries.values():
            res, msg = await self.restore_query(q)
            if res: aliases.append(q['alias'])
            else: LOGGER.warning(f"[{self.username}] Query restore failed: {msg}")
        added_q = self.queries
        exp_len = len(queries.values())
        msg = f"[{self.username}] restored {len(added_q)}/{exp_len} Queries: {', '.join(aliases)}"
        if len(added_q)==exp_len: 
            LOGGER.info(msg)
            return True, f"Restored all {len(added_q)} queries"
        else: 
            LOGGER.warning(msg)
            return False, f"Restored only {len(added_q)}/{exp_len} Queries"

    async def reload_cookies(self, cookies) -> tuple[bool, str]:
        '''Update existing files with new data'''
        try:
            await self.db_conn.reload_cookies(self.username, cookies)
            return True, f'Cookies reloaded'
        except Exception as e:
            LOGGER.error(traceback.format_exc())
            return False, f"Error occurred: {e}"