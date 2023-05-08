import logging
from unittest import IsolatedAsyncioTestCase
from unittest.mock import Mock, MagicMock, AsyncMock
from datetime import datetime, timedelta

from . import Monitor
from server.query import serialize
from common import *
from server.utils import config


log = logging.getLogger('TEST')


class Test_Monitor(IsolatedAsyncioTestCase):
    monitor = Monitor('testuser')
    monitor.db_conn = Mock()
    monitor.db_conn.create_cookies_filename = AsyncMock(return_value='testcookiefile.json')
    monitor.db_conn.setdefault_cookie_file = AsyncMock(return_value=({}, 'testcookiefile.json'))
    monitor.db_conn.save_dashboard = AsyncMock()
    monitor.db_conn.save_cookies = AsyncMock()
    monitor.db_conn.get_dashboard_data = AsyncMock(return_value={})
    monitor.db_conn.reload_cookies = AsyncMock()

    def setUp(self) -> None:
        self.monitor.queries.clear()
        self.monitor.warnings.clear()
        super().setUp()
    
    async def add_query(self, d:dict, exp=True) -> str:
        s, msg = await self.monitor.add_query(d)
        self.assertEqual(s, exp, msg)
        return msg

    async def edit_query(self, d:dict, exp=True) -> str:
        s, msg = await self.monitor.edit_query(d)
        self.assertEqual(s, exp, msg)
        return msg

    def get_public_functions(self):
        return [func for func in dir(Monitor) if callable(getattr(Monitor, func)) and not func.startswith("_")]
                
    async def test_unit_parse_eta_1(self):
        '''ETA parse dow & time_span'''
        parsed = await self.monitor._parse_eta('saturday,16-18')
        expected = {'dow': [5], 'time_span':[((16, 0), (18, 0))], 'dt':[], 'dt_span':[], 'dow_span':[], 'raw':'saturday,16-18'}
        self.assertDictEqual(parsed, expected)
        self.assertEqual(self.monitor.warnings, set())
    
    async def test_unit_parse_eta_2(self):
        '''ETA parse 2x dow, dt'''
        parsed = await self.monitor._parse_eta('monday,wednesday,14/11/2023')
        expected = {'dow': [0, 2], 'time_span':[], 'dt':[(14,11,2023)], 'dt_span':[], 'dow_span':[], 'raw':'monday,wednesday,14/11/2023'}
        self.assertDictEqual(parsed, expected)
        self.assertEqual(self.monitor.warnings, set())
    
    async def test_unit_parse_eta_3(self):
        '''ETA parse dt_span, dow_span'''
        parsed = await self.monitor._parse_eta('3/9/2023-14/11/2023,monday-friday')
        self.assertEqual(self.monitor.warnings, set())
        self.assertEqual(parsed['dt_span'], [(datetime(2023,9,3), datetime(2023,11,14))])
        self.assertEqual(parsed['dow_span'], [(0,4)])

    async def test_unit_parse_eta_4(self):
        '''ETA parse 2x dow, dt, time_span'''
        parsed = await self.monitor._parse_eta('saturday,3/9/2023,20-23,monday')
        self.assertEqual(self.monitor.warnings, set())
        self.assertEqual(parsed['dow'], [5, 0])
        self.assertEqual(parsed['dt'], [(3,9,2023)])
    
    async def test_unit_parse_eta_5(self):
        '''ETA parse 2x dt_span 2x time_span'''
        parsed = await self.monitor._parse_eta('01/02/2020-02/03/2020,20-23:15,10:24-12,03/05/2021-5/6/2021')
        self.assertEqual(self.monitor.warnings, set())
        self.assertEqual(parsed['dt_span'], [((datetime(2020,2,1)),(datetime(2020,3,2))), ((datetime(2021,5,3)),(datetime(2021,6,5)))])
        self.assertEqual(parsed['time_span'], [((20,0),(23,15)), ((10,24), (12,0))])

    async def test_unit_parse_eta_6(self):
        '''ETA parse when empty'''
        parsed = await self.monitor._parse_eta('')
        self.assertEqual(self.monitor.warnings, set())
        self.assertEqual(parsed, {'dow':[], 'dt':[], 'dow_span':[], 'dt_span':[], 'time_span':[], 'raw':''})
    
    async def test_unit_parse_eta_invalid_1(self):
        '''ETA fail parse dow'''
        parsed = await self.monitor._parse_eta('20-23:15,10:24-12,sarday')
        self.assertEqual(self.monitor.warnings, {'invalid ETA rules: sarday'})
        self.assertEqual(parsed, {'dow':[], 'dt':[], 'dow_span':[], 'dt_span':[], 'time_span':[((20,0),(23,15)), ((10,24), (12,0))], 'raw': '20-23:15,10:24-12,sarday'})
    
    async def test_unit_parse_eta_invalid_2(self):
        '''ETA fail parse time_span'''
        parsed = await self.monitor._parse_eta('24-26:15')
        self.assertEqual(self.monitor.warnings, {'invalid ETA rules: 24-26:15'})
        self.assertEqual(parsed, {'dow':[], 'dt':[], 'dow_span':[], 'dt_span':[], 'time_span':[], 'raw': '24-26:15'})

    async def test_unit_parse_eta_invalid_3(self):
        '''ETA fail parse dt'''
        parsed = await self.monitor._parse_eta('2023/03/12')
        self.assertEqual(self.monitor.warnings, {'invalid ETA rules: 2023/03/12'})
        self.assertEqual(parsed, {'dow':[], 'dt':[], 'dow_span':[], 'dt_span':[], 'time_span':[], 'raw': '2023/03/12'})
    
    async def test_unit_parse_eta_invalid_5(self):
        '''ETA fail parse dt_span'''
        parsed = await self.monitor._parse_eta('03/12/2023-31/13/2023')
        self.assertEqual(self.monitor.warnings, {'invalid ETA rules: 03/12/2023-31/13/2023'})
        self.assertEqual(parsed, {'dow':[], 'dt':[], 'dow_span':[], 'dt_span':[], 'time_span':[], 'raw': '03/12/2023-31/13/2023'})

    async def test_unit_parse_eta_invalid_6(self):
        '''ETA fail parse not string'''
        parsed = await self.monitor._parse_eta(7)
        self.assertEqual(len(self.monitor.warnings), 0)
        self.assertEqual(parsed, {'dow':[], 'dt':[], 'dow_span':[], 'dt_span':[], 'time_span':[], 'raw': 7})

    async def test_unit_eta_condition_1(self):
        eta = {'dow': [1], 'time_span':[((15, 0), (16, 0))], 'dt':[(25,4,2023)], 'dt_span':[], 'dow_span':[]}
        c = self.monitor._eta_condition(eta, datetime(2023, 4, 25, 15, 34))
        self.assertTrue(c)
    
    async def test_unit_eta_condition_2(self):
        eta = {'dow': [], 'time_span':[], 'dt':[], 'dt_span':[], 'dow_span':[]}
        c = self.monitor._eta_condition(eta, datetime(2023, 4, 25, 15, 34))
        self.assertTrue(c)
    
    async def test_unit_eta_condition_3(self):
        eta = {'dow': [1], 'time_span':[], 'dt':[], 'dt_span':[(datetime(2023, 4, 20), datetime(2023, 4, 24))], 'dow_span':[]}
        c = self.monitor._eta_condition(eta, datetime(2023, 4, 25, 15, 34))
        self.assertFalse(c)
    
    async def test_unit_eta_condition_4(self):
        eta = {'dow': [], 'time_span':[], 'dt':[], 'dt_span':[(datetime(2023, 4, 25), datetime(2023, 4, 25))], 'dow_span':[]}
        c = self.monitor._eta_condition(eta, datetime(2023, 4, 25, 15, 34))
        self.assertTrue(c)
    
    async def test_unit_eta_condition_5(self):
        eta = {'dow': [1], 'time_span':[], 'dt':[], 'dt_span':[], 'dow_span':[(1,2)]}
        c = self.monitor._eta_condition(eta, datetime(2023, 4, 25, 15, 34))
        self.assertTrue(c)

    async def test_integration_eta_1_serialize(self):
        '''Check if serialized eta is equal to the input string'''
        d = dict(
            eta = {'dow': [1], 'time_span':[((16,0), (18,0))], 'dt':[], 'dt_span':[], 'dow_span':[], 'raw': 'tuesday,16-18'},
            last_run = datetime(2023,4,15),
            last_match_datetime = datetime(2023,4,15),
            query = Mock()
        )
        s = serialize(d)
        self.assertEqual(s['eta'], 'tuesday,16-18')
        self.assertIsNotNone(d.get('query'))
    
    async def test_integration_eta_2_validate(self):
        '''Provide proper ETA to query validation'''
        d = dict(
            url = 'localhost_2',
            interval = '90',
            sequence = 'test',
            eta = 'saturday,20:30-23',
            cooldown = '0',
        )
        expected = {'dow': [5], 'time_span':[((20,30),(23,0))], 'dt':[], 'dt_span':[], 'dow_span':[], 'raw':'saturday,20:30-23'}
        vd, s = await self.monitor._validate_query(d)
        self.assertTrue(s)
        self.assertEqual(self.monitor.warnings, set())
        self.assertEqual(vd['eta'], expected)
        self.assertEqual(vd['cooldown'], 90)
    
    async def test_integration_eta_3_validate(self):
        '''Provide invalid ETA to query validation'''
        d = dict(
            url = 'localhost_3',
            interval = '90',
            sequence = 'test',
            eta = 'mushiday',
        )
        expected = {'dow':[], 'dt':[], 'dow_span':[], 'dt_span':[], 'time_span':[], 'raw':'mushiday'}
        vd, s = await self.monitor._validate_query(d)
        self.assertIn('invalid ETA rules: mushiday', self.monitor.warnings)
        self.assertTrue(s)
        self.assertEqual(vd['eta'], expected)
    
    async def test_integration_eta_4_validate(self):
        '''Provide empty ETA to query validation'''
        d = dict(
            url = 'localhost_4',
            interval = '90',
            sequence = 'test',
            eta = '',
        )
        expected = {'dow':[], 'dt':[], 'dow_span':[], 'dt_span':[], 'time_span':[], 'raw':''}
        vd, s = await self.monitor._validate_query(d)
        self.assertEqual(self.monitor.warnings, set())
        self.assertTrue(s)
        self.assertEqual(vd['eta'], expected)

    async def test_integration_eta_5_validate(self):
        '''Provide NoneType ETA to query validation'''
        d = dict(
            url = 'localhost_5',
            interval = '90',
            sequence = 'test',
            eta = None,
        )
        expected = {'dow':[], 'dt':[], 'dow_span':[], 'dt_span':[], 'time_span':[], 'raw':''}
        vd, s = await self.monitor._validate_query(d)
        self.assertEqual(self.monitor.warnings, set())
        self.assertTrue(s)
        self.assertEqual(vd['eta'], expected)
    
    async def test_integration_eta_6_validate_condition_serialize(self):
        '''Provide proper ETA to validation, make condition and serialize'''
        d = dict(
            url = 'localhost_6',
            interval = '90',
            sequence = 'test',
            eta = 'saturday,20:30-23',
        )
        expected = {'dow': [5], 'time_span':[((20,30),(23,0))], 'dt':[], 'dt_span':[], 'dow_span':[], 'raw':'saturday,20:30-23'}
        vd, s = await self.monitor._validate_query(d)
        self.assertEqual(self.monitor.warnings, set())
        self.assertTrue(s)
        self.assertEqual(vd['eta'], expected)
        eta_condition = self.monitor._eta_condition(vd['eta'], datetime(2023,4,29,21,30))
        self.assertTrue(eta_condition)
        vd['query'] = Mock()
        self.assertIsInstance(serialize(vd)['eta'], str)

    async def get_query_by_alias(self, alias) -> dict:
        try:
            uid = [k for k, v in self.monitor.queries.items() if v['alias']==alias][0]
            return self.monitor.queries[uid]
        except IndexError:
            return {}

    async def test_unit_add_query_1(self):
        '''Add query with required parameters'''
        d = dict(url='localhost_1', interval=15, sequence='test_1', alias='add_1', cooldown=5)
        msg = await self.add_query(d)
        self.assertEqual(msg, 'Query added successfully')
        q = await self.get_query_by_alias('add_1')
        self.assertEqual(q['url'], 'localhost_1')
        self.assertEqual(q['interval'], 15)
        self.assertEqual(q['sequence'], 'test_1')
        self.assertEqual(q['found'], False)
        self.assertEqual(q['last_match_datetime'], self.monitor.DEFAULT_DATE)
        self.assertEqual(q['status'], -1)
        self.assertEqual(q['cooldown'], 15)
        self.assertEqual(q['eta'], {'dow':[], 'dt':[], 'dow_span':[], 'dt_span':[], 'time_span':[], 'raw':''})

    async def test_unit_add_query_2(self):
        '''Add query with some extra parameters'''
        d = dict(url='localhost_2', interval=15, sequence='test_2', alias='add_2',
                    randomize=24, mode='not-exists', target_url='localhost_2a', is_recurring=True, cooldown='3d')
        await self.add_query(d)
        q = await self.get_query_by_alias('add_2')
        self.assertEqual(q['randomize'], 24)
        self.assertEqual(q['mode'], 'not-exists')
        self.assertEqual(q['target_url'], 'localhost_2a')
        self.assertEqual(q['cookies_filename'], 'testcookiefile.json')
        self.assertEqual(q['is_recurring'], True)
        self.assertEqual(q['cooldown'], 4320)
    
    async def test_unit_add_query_3(self):
        '''Add query with invalid extra parameters'''
        d = dict(url='localhost_4', interval=1, sequence='test_4', alias='add_4',
            randomize='2b', cycles_limit='ab', min_matches=0, found='br', extra=True, eta='sorday,12-13,35-54')
        msg = await self.add_query(d)
        self.assertTrue(all(i in msg for i in {'Query added successfully with warnings', 'interval too low (min:5)', 'invalid ETA rules: sorday, 35-54'}))
        q = await self.get_query_by_alias('add_4')
        self.assertEqual(q['randomize'], 0)
        self.assertEqual(q['cycles_limit'], 0)
        self.assertEqual(q['min_matches'], 1)
        self.assertEqual(q['found'], False)
        self.assertNotIn('extra', q.keys())
        self.assertEqual(q['eta'], {'dow':[], 'dt':[], 'dow_span':[], 'dt_span':[], 'time_span':[((12,0), (13,0))], 'raw':'sorday,12-13,35-54'})
        self.assertEqual(q['cooldown'], self.monitor.MIN_INTERVAL)

    async def test_unit_add_query_invalid_1(self):
        '''Fail to add query without required parameters'''
        await self.add_query(dict(interval=15, sequence='test_3'), exp=False)
        await self.add_query(dict(url='localhost_11', sequence='test_3'), exp=False)
        await self.add_query(dict(url='', interval=15, sequence='test'), exp=False)

    async def test_unit_add_query_invalid_2(self):
        '''Fail to add query with duplicate alias (provided or created)'''
        d = dict(url='localhost_3', interval=15, sequence='test_3', alias='add_3')
        await self.add_query(d)
        d = dict(url='localhost_3b', interval=10, sequence='test_3b', alias='add_3')
        msg = await self.add_query(d, exp=False)
        self.assertIn('duplicate', msg)
        d = dict(url='add_3', interval=15, sequence='test_3')
        msg = await self.add_query(d, exp=False)
        self.assertIn('duplicate', msg)

    async def test_unit_parse_interval_1(self):
        '''Check if interval is parsed correctly to minutes'''
        min_interval = int(config['min_query_interval'])
        self.assertEqual(await self.monitor._parse_interval('2.8h'), 168)
        self.assertEqual(await self.monitor._parse_interval('3.5d'), 5040)
        self.assertEqual(await self.monitor._parse_interval('20.8'), 20)
        self.assertEqual(await self.monitor._parse_interval('6'), 6)
        self.assertEqual(await self.monitor._parse_interval('0'), min_interval)
        self.assertEqual(self.monitor.warnings, {f'interval too low (min:{min_interval})'})
        try: await self.monitor._parse_interval('5bc')
        except ValueError: pass
        else: self.assertTrue(False, "Expected to fail on not numeric string")

    async def test_unit_create_uid(self):
        '''Check if uid is generated each time'''
        s = set()
        for _ in range(10):
            u = await self.monitor._create_uid()
            self.assertFalse(u in s, 'Failed to create uid')
            s.add(u)
        self.assertTrue(True)

    async def test_unit_validate_min_matches(self):
        '''Check if min value for min_maches is 1'''
        self.assertEqual(await self.monitor._validate_min_matches('-1'), 1)
        self.assertEqual(await self.monitor._validate_min_matches('0'), 1)
        self.assertEqual(await self.monitor._validate_min_matches('3'), 3)

    async def test_unit_edit_query_1(self):
        '''check if query edit is handled properly'''
        await self.add_query(dict(url='localhost_3e', interval=15, sequence='test_3', alias='edit_1'))
        q = await self.get_query_by_alias('edit_1')
        c_pre = self.monitor.db_conn.setdefault_cookie_file.call_count
        s, msg = await self.monitor.edit_query(dict(uid=q['uid'], alias='edit_1b', min_matches=3))
        c_post = self.monitor.db_conn.setdefault_cookie_file.call_count
        q_e = self.monitor.queries[q['uid']]
        q_e['uid']='edit_1b'; q_e['min_matches']=3
        self.assertTrue(s, msg)
        self.assertDictEqual(q, q_e)
        self.assertEqual(q['query'].min_matches, 3, 'new Query object was not created')
        self.assertEqual(c_post-c_pre, 1, 'setdefault_cookie_file was not called')

    async def test_unit_edit_query_invalid_1(self):
        '''check if query edit is handled properly with invalid parameter'''
        await self.add_query(dict(url='localhost_3e', interval=15, sequence='test_3', alias='edit_1i'))
        q = await self.get_query_by_alias('edit_1i')
        await self.monitor.edit_query(dict(uid=q['uid'], interval='abc', extra='test'))
        self.assertEqual(q['interval'], 15)
        self.assertNotIn('extra', q.keys())

    async def test_unit_edit_query_invalid_2(self):
        '''check if edit query is failed when query does not exist'''
        s, msg = await self.monitor.edit_query(dict(uid='xxx', url='localhost', interval='15', sequence='test'))
        self.assertFalse(s, msg)
        self.assertIn('Query does not exist', msg)

    async def test_unit_restore_query_1(self):
        '''check if restore query works as expected'''
        await self.monitor.restore_query(dict(url='localhost_1r', interval=15, sequence='test_3', alias='restore_1'))
        q = await self.get_query_by_alias('restore_1')
        self.assertEqual(q['sequence'], 'test_3')
    
    async def test_unit_restore_query_invalid_1(self):
        '''check if restore query works as expected'''
        await self.monitor.restore_query(dict(url='', interval=15, sequence='test_3', alias='restore_1i'))
        q = await self.get_query_by_alias('restore_1i')
        self.assertDictEqual(q, {})

    async def test_unit_scan_one_1(self):
        '''perform one scan'''
        await self.add_query(dict(url='localhost_3s', interval=15, sequence='test_3', alias='scan_1'))
        uid = [k for k, v in self.monitor.queries.items() if v['alias']=='scan_1'][0]
        self.monitor.queries[uid]['query'].run = Mock(return_value=(True, 0))
        res = self.monitor._scan_one(self.monitor.queries[uid])
        self.assertEqual(res[uid]['cycles'], 1)
        self.assertEqual(res[uid]['found'], True)
        self.assertEqual(res[uid]['status'], 0)
        self.assertEqual(res[uid]['is_new'], True)

    async def test_unit_scan_one_2(self):
        '''ommit scan if already found and not recurring'''
        await self.add_query(dict(url='localhost_3s', interval=15, sequence='test_3', alias='scan_1'))
        q = await self.get_query_by_alias('scan_1')
        uid = q['uid']
        self.monitor.queries[uid]['query'].run = Mock(return_value=(True, 0))
        q = self.monitor._scan_one(q)
        self.assertEqual(q[uid]['cycles'], 1)
        q[uid]['last_run'] = self.monitor.DEFAULT_DATE
        q = self.monitor._scan_one(q[uid])
        self.assertEqual(q[uid]['cycles'], 1)

    async def test_unit_scan_one_3(self):
        '''perform scan if already found but is recurring'''
        await self.add_query(dict(url='localhost_3s', interval=15, sequence='test_3', alias='scan_1', is_recurring=True))
        q = await self.get_query_by_alias('scan_1')
        uid = q['uid']
        self.monitor.queries[uid]['query'].run = Mock(return_value=(True, 0))
        q = self.monitor._scan_one(q)
        self.assertEqual(q[uid]['cycles'], 1)
        q[uid]['last_run'] = self.monitor.DEFAULT_DATE
        q = self.monitor._scan_one(q[uid])
        self.assertEqual(q[uid]['cycles'], 2)

    async def test_unit_scan_one_4(self):
        '''perform immediate re-scan if last query returned status: Connection Lost'''
        await self.add_query(dict(url='localhost_3s', interval=15, sequence='test_3', alias='scan_1', is_recurring=True))
        q = await self.get_query_by_alias('scan_1')
        uid = q['uid']
        self.monitor.queries[uid]['query'].run = Mock(return_value=(False, 2))
        q = self.monitor._scan_one(q)
        self.assertEqual(q[uid]['cycles'], 0)
        self.monitor.queries[uid]['query'].run = Mock(return_value=(False, 0))
        q = self.monitor._scan_one(q[uid])
        self.assertEqual(q[uid]['cycles'], 1)

    async def test_unit_scan_one_5(self):
        '''ommit immediate re-scan if last query returned status: Permission Denied'''
        await self.add_query(dict(url='localhost_3s', interval=15, sequence='test_3', alias='scan_1', is_recurring=True))
        q = await self.get_query_by_alias('scan_1')
        uid = q['uid']
        self.monitor.queries[uid]['query'].run = Mock(return_value=(False, 1))
        q = self.monitor._scan_one(q)
        self.assertEqual(q[uid]['cycles'], 1)
        q = self.monitor._scan_one(q[uid])
        self.assertEqual(q[uid]['cycles'], 1)

    async def test_unit_scan_one_6(self):
        '''ommit scan if cycles_limit == -1'''
        await self.add_query(dict(url='localhost_3s', interval=15, sequence='test_3', alias='scan_1', cycles_limit=-1))
        q = await self.get_query_by_alias('scan_1')
        uid = q['uid']
        self.monitor.queries[uid]['query'].run = Mock(return_value=(False, 0))
        q = self.monitor._scan_one(q)
        self.assertEqual(q[uid]['cycles'], 0)

    async def test_unit_scan_one_7(self):
        '''ommit scan if eta does not match'''
        await self.add_query(dict(url='localhost_3s', interval=15, sequence='test_3', alias='scan_1'))
        q = await self.get_query_by_alias('scan_1')
        uid = q['uid']
        self.monitor.queries[uid]['query'].run = Mock(return_value=(False, 0))
        q = self.monitor._scan_one(q)
        self.assertEqual(q[uid]['cycles'], 1)
        await self.edit_query(dict(uid=uid, eta='01-02-2020', last_match_datetime=self.monitor.DEFAULT_DATE))
        q = self.monitor._scan_one(q[uid])
        self.assertEqual(q[uid]['cycles'], 1)

    async def test_unit_scan_one_8(self):
        '''ommit scan if insufficient time diff'''
        msg = await self.add_query(dict(url='localhost_3s', interval=15, sequence='test_3', alias='scan_8'))
        uid = [k for k, v in self.monitor.queries.items() if v['alias']=='scan_8'][0]
        res = self.monitor._scan_one(self.monitor.queries[uid])
        self.assertEqual(res[uid]['cycles'], 1)
        self.assertEqual(res[uid]['found'], False)
        self.assertEqual(res[uid]['status'], 0)
        self.assertEqual(res[uid]['is_new'], True)
        res = self.monitor._scan_one(self.monitor.queries[uid])
        self.assertEqual(res[uid]['cycles'], 1)
        self.assertEqual(res[uid]['is_new'], False)


    async def test_should_run_cooldown(self):
        '''Check if cooldown is respected'''
        eta = dict(dow=[], time_span=[], dt_span=[], dow_span=[], dt=[], raw=[])
        res = self.monitor._should_run(dict(status=0, cycles_limit=0, eta=eta, found=True, 
                is_recurring=True, cycles=1, last_run=datetime.now()-timedelta(minutes=10), interval=5, 
                cooldown=50, randomize=0))
        self.assertFalse(res)
        res = self.monitor._should_run(dict(status=0, cycles_limit=0, eta=eta, found=True, 
                is_recurring=True, cycles=1, last_run=datetime.now()-timedelta(minutes=50), interval=5, 
                cooldown=50, randomize=0))
        self.assertTrue(res)

    async def test_shoud_run_1(self):
        '''Check if should_run works as expected'''
        eta = dict(dow=[], time_span=[], dt_span=[], dow_span=[], dt=[], raw=[])
        res = self.monitor._should_run(dict(status=2, cycles_limit=0, eta=eta, found=False, 
                is_recurring=False, cycles=0, last_run=datetime.now(), interval=50, 
                cooldown=0, randomize=0))
        self.assertTrue(res, 'Query should run immediately the first time or if connection was lost')

        res = self.monitor._should_run(dict(status=0, cycles_limit=-3, eta=eta, found=False, 
                is_recurring=False, cycles=0, last_run=datetime.now()-timedelta(10), interval=4, 
                cooldown=0, randomize=0))
        self.assertFalse(res, 'Query with cycles_limit < 0 should always be ommited')

        res = self.monitor._should_run(dict(status=0, cycles_limit=0, eta=eta, found=True, 
                is_recurring=True, cycles=0, last_run=datetime.now()-timedelta(10), interval=4, 
                cooldown=0, randomize=0))
        self.assertTrue(res, 'Recurring Query should run after is found')

        res = self.monitor._should_run(dict(status=0, cycles_limit=0, eta=eta, found=True, 
                is_recurring=False, cycles=0, last_run=datetime.now()-timedelta(10), interval=4, 
                cooldown=0, randomize=0))
        self.assertFalse(res)

        d = (datetime.today()+timedelta(1)).weekday()
        eta = dict(dow=[d], time_span=[], dt_span=[], dow_span=[], dt=[], raw=[])
        res = self.monitor._should_run(dict(status=0, cycles_limit=0, eta=eta, found=False, 
                is_recurring=False, cycles=0, last_run=datetime.now()-timedelta(10), interval=4, 
                cooldown=0, randomize=0))
        self.assertFalse(res, 'Query should be skipped if ETA does no match')

        d = datetime.today().weekday()
        eta = dict(dow=[d], time_span=[], dt_span=[], dow_span=[], dt=[], raw=[])
        res = self.monitor._should_run(dict(status=0, cycles_limit=0, eta=eta, found=False, 
                is_recurring=False, cycles=0, last_run=datetime.now()-timedelta(10), interval=4, 
                cooldown=0, randomize=0))
        self.assertTrue(res, d)


    async def test_integration_warnings_flush(self):
        '''Assert that monitor.warnings are cleared after calling any public func'''
        public_funcs = self.get_public_functions()

        msg = await self.add_query(dict(url='localhost_3s', sequence='test', 
                            interval=15, alias='scan_8', eta='sorday'), exp=True)
        self.assertIn('sorday', msg)
        self.assertEqual(self.monitor.warnings, set())
        public_funcs.remove('add_query')

        q = await self.get_query_by_alias('scan_8')
        uid = q['uid']
        msg = await self.edit_query({'uid':uid, 'interval':0}, exp=True)
        self.assertIn('interval', msg)
        self.assertEqual(self.monitor.warnings, set())
        public_funcs.remove('edit_query')

        s, msg = await self.monitor.restore_query(dict(url='localhost_1r', interval=15, sequence='test_3', alias='restore_1'))
        self.assertEqual(msg, 'Query restored: restore_1')
        self.assertEqual(self.monitor.warnings, set())
        public_funcs.remove('restore_query')

        s, msg = await self.monitor.delete_query('abc')
        self.assertEqual(msg, 'Query with uid: abc does not exist')
        self.assertEqual(self.monitor.warnings, set())
        public_funcs.remove('delete_query')

        s, msg = await self.monitor.close_session('abc')
        self.assertEqual(self.monitor.warnings, set())
        public_funcs.remove('close_session')

        s, msg = await self.monitor.clean_queries()
        self.assertEqual(self.monitor.warnings, set())
        public_funcs.remove('clean_queries')

        s, msg = await self.monitor.save()
        self.assertEqual(self.monitor.warnings, set())
        public_funcs.remove('save')

        s, msg = await self.monitor.scan()
        self.assertEqual(self.monitor.warnings, set())
        public_funcs.remove('scan')

        s, msg = await self.monitor.populate()
        self.assertEqual(self.monitor.warnings, set())
        public_funcs.remove('populate')

        s, msg = await self.monitor.get_sound_file('notification.wav')
        self.assertEqual(self.monitor.warnings, set())
        public_funcs.remove('get_sound_file')

        s, msg = await self.monitor.reload_cookies({})
        self.assertEqual(self.monitor.warnings, set())
        public_funcs.remove('reload_cookies')

        self.assertEqual(public_funcs, list(), 'Not all public functions were checked')


    async def test_unit_delete_query_1(self):
        '''delete existing query'''
        await self.add_query(dict(url='localhost_3s', sequence='test', 
                            interval=15, alias='scan_8'), exp=True)
        q = await self.get_query_by_alias('scan_8')
        uid = q['uid']
        s, msg = await self.monitor.delete_query(uid)
        self.assertTrue(s, msg)
        self.assertNotIn(uid, self.monitor.queries.keys())
        
    async def test_unit_delete_query_2(self):
        '''try delete non-existing query'''
        await self.add_query(dict(url='localhost_3s', sequence='test', 
                            interval=15, alias='scan_8'), exp=True)
        s, msg = await self.monitor.delete_query('abc')
        self.assertFalse(s, msg)

    async def test_unit_clean_queries(self):
        '''remove completed queries'''
        await self.add_query(dict(url='localhost_3s', sequence='test', 
                            interval=15, alias='a'), exp=True)
        await self.add_query(dict(url='localhost_3s', sequence='test', 
                            interval=15, alias='b', found=True), exp=True)
        await self.add_query(dict(url='localhost_3s', sequence='test', 
                            interval=15, alias='c', found=True, is_recurring=True), exp=True)
        await self.monitor.clean_queries()
        aliases = [v['alias'] for v in self.monitor.queries.values()]
        self.assertIn('a', aliases)
        self.assertIn('c', aliases)
        self.assertNotIn ('b', aliases)

    async def test_unit_save(self):
        '''save dashboard'''
        await self.add_query(dict(url='localhost_3s', sequence='test', 
                            interval=15, alias='a_saved'), exp=True)
        s, msg = await self.monitor.save()
        self.assertTrue(s, msg)
        self.assertIn('Saved user data', msg)

    async def test_unit_save_fail(self):
        '''handle error during saving'''
        await self.add_query(dict(url='localhost_3s', sequence='test', 
                            interval=15, alias='a_saved'), exp=True)
        self.monitor.db_conn.save_dashboard = Mock(side_effect=OSError)
        s, msg = await self.monitor.save()
        self.assertFalse(s, msg)
        self.assertIn('Error', msg)
