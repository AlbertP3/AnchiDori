from datetime import datetime
import requests
from sys import platform
from os import system, path, listdir
from playsound import playsound, PlaysoundException
import asyncio
import aiohttp
import ssl
import logging
from time import monotonic, sleep
from getpass import getpass

from common.utils import QSTAT_CODES, boolinize
from cli import CWD
import common.refresh_cookies as rc
from cli.utils import config, rlinput

LOGGER = logging.getLogger('Client')

class TUI:
    '''Terminal User Interface'''
    async def init(self):
        await self.__init_parameters()
        await self.__init_web_comm()
        LOGGER.info('Started CLI...')
        if boolinize(config['auto_login']):
            await self.login_form()

    async def __init_parameters(self):
        self.loop_stage = 'main'
        self.do_continue = True
        self.refresh_interval = int(config['refresh_seconds'])
        self.clear_cmd = 'clear' if platform == 'linux' else 'cls'
        self.auth_session:dict = dict()
        self.unnotified_new:str = '' # path of sound file for an unnotified queriy
        self.id_for_target_urls = dict()
        self.all_queries_printout:str = ""
        self.seen:set = set()  # tracks target urls

    async def __init_web_comm(self):
        self.port = int(config['port'])
        self.server = config['server']
        if boolinize(config['secure']):
            ssl_context = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH, cafile=config['server_public_key'])
            self.conn = aiohttp.TCPConnector(ssl=ssl_context)
            self.session = aiohttp.ClientSession(connector=self.conn)
            self.address = f"https://{self.server}:{self.port}"
            LOGGER.info(f'Running in HTTPS mode')
        else:
            self.session = aiohttp.ClientSession()
            self.ssl_context = None
            self.address = f"http://{self.server}:{self.port}"
            LOGGER.warning(f'Running in HTTP mode')

    async def loop(self):
        while self.do_continue:
            try:
                if self.loop_stage == 'main':
                    await self.main_menu()
                elif self.loop_stage == 'open_browser':
                    try:
                        await self.open_url_in_browser()
                    except KeyboardInterrupt:
                        pass
            except (KeyboardInterrupt, EOFError):
                await self.session.close()
                if boolinize(config['secure']): self.conn.close()
                LOGGER.info('CLI terminated')
                self.do_continue = False
            except aiohttp.client_exceptions.ClientOSError:
                LOGGER.warning('[Errno 104] Connection reset by peer')
            except aiohttp.client_exceptions.ServerDisconnectedError:
                LOGGER.warning('Server diconnected')

    async def get_request(self, route:str, data:dict) -> dict:
        start_ = monotonic()
        res = dict()
        try:
            res = await self.session.get(f"{self.address}/{route}", json=data)
            res = await res.json()
        except (requests.exceptions.ConnectionError, asyncio.TimeoutError):
            LOGGER.warning('Internet Connection Lost!')
        except aiohttp.client_exceptions.ContentTypeError as e:
            LOGGER.error(e)
        LOGGER.debug(f"[GET] <{route}> in {(monotonic()-start_)*1000:.2f}ms content: {res}")
        return res

    async def post_request(self, route:str, data:dict) -> dict:
        start_ = monotonic()
        res = dict()
        try:
            resp = await self.session.post(f"{self.address}/{route}", json=data)
            res = await resp.json()
        except requests.exceptions.ConnectionError:
            LOGGER.warning('Internet Connection Lost!', 'ERROR')
        except aiohttp.client_exceptions.ContentTypeError as e:
            LOGGER.error(e, 'ERROR')
        LOGGER.debug(f"[POST] <{route}> in {(monotonic()-start_)*1000:.2f}ms content: {res}")
        return res

    async def login_form(self):
        system(self.clear_cmd)
        if boolinize(config['auto_login']):
            usr = config.get('username')   
            passw = config.get('password')
        else:
            usr = input('Username: ')
            passw = getpass(prompt='Password: ')
        res = await self.post_request('auth', data=dict(username=usr, password=passw))
        if boolinize(res.get('auth_success')):
            self.username = res['username']
            self.auth_session = dict(username=self.username, token=res['token'])
            LOGGER.info(f'Logged in as {self.username}')
            await self.unmark_matches_on_init()
            await self.loop()

    async def unmark_matches_on_init(self):
        '''Removes new-match mark from queries that were already matched on login'''
        res = await self.post_request('get_all_queries', data=self.auth_session)
        for v in res.values():
            if boolinize(v['found']):
                self.seen.add(v['target_url'])

    async def main_menu(self):
        system(self.clear_cmd)
        choices = dict()
        i = 1
        print(f"{i}. Scan")
        choices[i] = self.scan_menu
        i+=1
        print(f"{i}. Add Query")
        choices[i] = self.add_query_menu
        i+=1
        print(f"{i}. Edit Query")
        choices[i] = self.edit_query
        i+=1
        print(f"{i}. Reload Cookies")
        choices[i] = self.reload_cookies
        i+=1
#        print(f"{i}. Clear")
#        choices[i] = self.clear_completed
#        i+=1
        print(f"{i}. Save")
        choices[i] = self.save
        i+=1
        print(f"{i}. Login")
        choices[i] = self.login_form
        choice = input('Select: ')
        try:
            await choices[int(choice)]()
        except ValueError:
            # some debug tools
            if choice == 'reload_config':
                await self.reload_config()
            elif choice == 'play':
                await self.play_sound('notification.wav')

    async def save(self):
        resp = await self.post_request('save', data=self.auth_session)
        input(resp.get('msg', 'Error handling request')+'. Press enter to continue...')

    async def clear_completed(self):
        await self.post_request('clean', data=self.auth_session)

    async def scan_menu(self):
        system(self.clear_cmd)
        self.loop_stage = 'open_browser'
        while True:
            try:
                # if no queries were run, endpoint returns an empty dict
                self.scan_res = await self.post_request('get_dashboard', data=self.auth_session)
                system(self.clear_cmd)
                if boolinize(self.scan_res.get('success', True)):
                    print(await self.dashboard_printout(self.scan_res), end='')
                    if self.unnotified_new:
                        await self.play_sound(self.unnotified_new)
                        self.unnotified_new = ''
                    sleep(self.refresh_interval)
                else:
                    print(self.scan_res.get('msg', 'Connection Error'))
                    input('Press any key to continue...')
                    self.loop_stage = 'main'
                    break
            except KeyboardInterrupt:
                break

    async def play_sound(self, filename:str=''):
        # ask server for a new file if not exists in cache
        if not filename in listdir(f"{CWD}/cache"):
            try:
                resp = await self.session.post(f"{self.address}/get_sound", json={'alert_sound': filename, **self.auth_session})
                sound_name = resp.content_disposition.type
                await self.create_sound_file(resp.content, filename=sound_name)
            except (AttributeError, ValueError) as e:
                LOGGER.warning(f"Failed while trying to download file: {filename}. Exception: {e}", 'ERROR')
                return
        else:
            sound_name = filename
        # play the notification
        try:
            LOGGER.info(f"Playing sound: {sound_name}")
            playsound(f'{CWD}/cache/{sound_name}')
        except PlaysoundException as e:
            LOGGER.warning(f"Unable to play sound: {e}", 'ERROR')
        except KeyboardInterrupt:
            pass

    async def create_sound_file(self, streamreader, filename):
        '''Creates a file with notification sound to be played'''
        sound_file = bytearray()
        while True:
            chunk = await streamreader.read(100)
            if not chunk: break
            sound_file+=chunk
        with open(f'{CWD}/cache/{filename}', 'w+b') as f:
            f.write(sound_file)
        LOGGER.debug(f'Notification file created: {filename}')

    async def open_url_in_browser(self):
        self.loop_stage = 'main'
        try:
            id = input('\nID: ')
            target_url = self.id_for_target_urls[int(id)] if id.isnumeric() else [v['target_url'] for v in self.scan_res.values() if v['alias']==id][0]
        except (IndexError, TypeError):
            return
        if target_url:
            system(f"{config['browser']} {target_url}")
            self.seen.add(target_url)
            LOGGER.info(f"Opened in browser url: {target_url}")

    async def add_query_menu(self):
        try:
            system(self.clear_cmd)
            url_ = input('URL: ')
            seq = input('Sequence: ')
            interval = input('Interval (minutes): ')
            cycles_limit = input('*cycles_limit: ') or 0
            randomize = input('*Randomize (0-100): ') or 0
            eta = input('*ETA (d-m-Y H:M:S): ') or '0'
            mode = input('*Mode: ') or 'exists'
            is_recurring = input('*Recurring: ') or False
            alias = input('*Alias: ') or url_
            cookies_basename = input('*Cookies filename: ') or alias
            target_url = input('*Target URL: ') or url_
            alert_sound = input('*Alert Sound: ')
            min_matches = input('*Min Matches: ') or 1
            q = dict(url=url_, sequence=seq, interval=interval, randomize=randomize, eta=eta, 
                     mode=mode, cycles_limit=cycles_limit, is_recurring=is_recurring, 
                     cookies_filename=cookies_basename, alias=alias, alert_sound=alert_sound, 
                     target_url=target_url, min_matches=min_matches)
            q.update(self.auth_session)
            res = await self.post_request('add_query', data=q)
            print(res['msg'])
            input('Press any key to continue...')
        except KeyboardInterrupt:
            pass

    async def dashboard_printout(self, data:dict) -> str:
        i = 1
        output = "         ALIAS         | FOUND | INTERVAL |  CYCLES  |       LAST_RUN       |      STATUS      |\n"
        for uid, v in data.items():
            c = int(v['cycles_limit'])
            if c: continue
            match = await self.get_notification_sign(boolinize(v['found']), v['alert_sound'], v['is_new'], v['target_url'], boolinize(v['is_recurring']))
            msg = QSTAT_CODES[int(v['status'])]
            if c > 0: cycles_indicator = f"{v['cycles']:>3}/{v['cycles_limit']:<4}"
            elif c < 0: cycles_indicator = '  -/-   ' 
            else: cycles_indicator = f"{v['cycles']:^8}"
            output += f"{v['alias'][:22]:^22} | {match:^5} | {v['interval']:^8} | {cycles_indicator:^8} | {v['last_run'][:19]:^20} | {msg:^16} |"+'\n'
            self.id_for_target_urls[i] = v['target_url']; i+=1
        output += 96*'-' + '\nPress Ctrl+c to open in browser' + 26*' ' + f'refresh_rate:{self.refresh_interval}s last_refresh={datetime.now().strftime("%H:%M:%S")}'
        return output

    async def get_notification_sign(self, found:bool, alert_sound:str, is_new:bool, target_url:str, is_recurring):
        match = ' '
        if found:
            if is_new:
                match = '!!!'
                self.unnotified_new = alert_sound
                self.seen.discard(target_url)
            elif target_url not in self.seen:
                match = '!'
            elif not is_recurring:
                match = '+'
        return match
            
    async def edit_query(self):
        '''Enter a new loop for editing the query'''
        try:
            query_data = await self._execute_query_edit()
            if query_data['success']:
                msg = await self.form_edit_query(query_data)
            else:
                msg = query_data['msg']
            print(msg)
            input(f'Press any key to continue...')
        except KeyboardInterrupt:
            pass
    
    async def _execute_query_edit(self):
        uid = None
        query_data = dict(success=False, msg='Query does not exist')  
        all_queries = await self.print_all_queries()
        alias = input("Enter the query's alias: ")
        if alias.isnumeric():
            i, c = int(alias), 0
            for v in all_queries.values():
                if c == i-1:
                    uid = v['uid']
                    break
                c+=1
        else:
            for v in all_queries.values():
                if v['alias'] == alias:
                    uid = v['uid']
                    break
        if uid:
            query_data = await self.load_query_for_edit(uid)
        return query_data

    async def print_all_queries(self) -> dict:
        system(self.clear_cmd)
        res = await self.post_request('get_all_queries', data=self.auth_session)
        output = ' | '.join(v['alias'] for v in res.values()) + '\n' 
        self.all_queries_printout = output
        print(output)
        return res

    async def load_query_for_edit(self, uid) -> dict:
        d = dict(uid=uid)
        d.update(self.auth_session)
        res = await self.post_request('get_query', data=d)
        return res

    async def form_edit_query(self, data):
        cycles_limit = rlinput('cycles_limit: ', prefill=data['cycles_limit']) or 0
        found = rlinput('found: ', prefill=data['found']) or False
        interval = rlinput('interval: ', prefill=data['interval'])
        randomize = rlinput('randomize: ', prefill=data['randomize']) or 0
        url = rlinput('url: ', prefill=data['url'])
        sequence = rlinput('sequence: ', prefill=data['sequence'])
        eta = rlinput('eta: ', prefill=data['eta']) or '0'
        mode = rlinput('mode: ', prefill=data['mode']) or 'exists'
        is_recurring = rlinput('is_recurring: ', prefill=data['is_recurring']) or False
        alias = rlinput('alias: ', prefill=data['alias']) or url
        alert_sound = rlinput('alert_sound: ', prefill=data['alert_sound'])
        target_url = rlinput('target_url: ', prefill=data['target_url']) or url
        min_matches = rlinput('min_matches: ', prefill=data['min_matches']) or 1
        last_run = rlinput('last_run: ', prefill=data['last_run']) or 0
        q = dict(uid=data['uid'], url=url, sequence=sequence, interval=interval, randomize=randomize, eta=eta, 
                    mode=mode, cycles=data['cycles'], cycles_limit=cycles_limit, is_recurring=is_recurring,
                    last_run=last_run, found=found, cookies_filename=data['cookies_filename'], alias=alias, 
                    alert_sound=alert_sound, target_url=target_url, min_matches=min_matches
                 )
        q.update(self.auth_session)
        res = await self.post_request('edit_query', data=q)
        return res['msg']

    async def reload_cookies(self):
        system(self.clear_cmd)
        await self.print_all_queries()
        aliases:list = input("Select for refresh: ").split(' ')
        if aliases == ['*']: aliases = self.all_queries_printout.split(' | ')
        elif aliases == ['']: aliases = list()
        cookies = dict()
        for a in aliases:
            if a not in self.all_queries_printout: continue
            params = await self.load_query_for_edit(a)
            if not boolinize(params['success']): continue
            f = params['cookies_filename'].split('.')[0]
            if not f: continue
            cookies[a] = await self.get_cookies(f)
            print(f"{a} scheduled for reload")
        res = dict(cookies=cookies)
        res.update(self.auth_session)
        resp = await self.post_request('refresh_data', data=res)
        print(resp['msg'])
        input('Press any key...')

    async def get_cookies(self, host:str) -> dict:
        # fetch session cookies from the browser
        # returns a list for specific host with pairs of {name, value}
        f = rc.Firefox()
        new_cookies:dict = f.load(host)
        return new_cookies

    async def reload_config(self):
        data = dict(passphrase='n9FQm0zcv$@SA')
        data.update(self.auth_session)
        res = await self.post_request('reload_config', data)
        input(f"{res.get('msg', 'Internal Error')}. Press enter to continue...")


if __name__ == '__main__':
    tui = TUI()
    loop = asyncio.new_event_loop()
    loop.run_until_complete(tui.init())
    while tui.do_continue:
        try:
            loop.run_until_complete(tui.loop())
        except KeyboardInterrupt:
            pass

