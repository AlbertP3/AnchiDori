from string import Template
from datetime import datetime
import requests
from common import *
from sys import platform
from os import confstr, system, path
from time import sleep
from playsound import playsound

config = Config()


class TUI:
    '''Terminal User Interface'''
    def __init__(self):
        self.do_continue = True
        self.server = config['server']
        self.port = int(config['port'])
        self.refresh_interval = int(config['tui_refresh_seconds'])
        self.session = requests.Session()
        self.address = f"http://{self.server}:{self.port}"
        self.clear_cmd = 'clear' if platform == 'linux' else 'cls'
        self.auth_session = dict()
        self.already_matched = set()  # stores urls of historical matches
        self.unnotified_new = list() # list of sound files for unnotified queries
        self.SOUND_PATH = Template('sounds/$filename')
        self.default_local_sound = self.SOUND_PATH.substitute(filename=config['local_sound'])
        self.date_fmt = config['date_fmt']
        self.id_for_target_urls = dict()

    def loop(self):
        while self.do_continue:
            try:
                self.main_menu()
            except (KeyboardInterrupt, EOFError):
                break

    def login_form(self):
        system(self.clear_cmd)
        usr = input('Username: ')
        passw = input('Password: ')
        res = self.session.get(self.address+'/auth', json=dict(username=usr, password=passw))
        res = res.json()
        if res['auth_success']:
            self.username = res['username']
            self.auth_session = dict(username=self.username, password=passw)
            self.loop()

    def main_menu(self):
        system(self.clear_cmd)
        choices = dict()
        i = 1
        if not self.auth_session:
            print(f"{i}. Login")
            choices[i] = self.login_form
            i+=1
        print(f"{i}. Scan")
        choices[i] = self.scan_menu
        i+=1
        print(f"{i}. Add Query")
        choices[i] = self.add_query_menu
        i+=1
        print(f"{i}. Edit Query")
        choices[i] = self.edit_query
        i+=1
        print(f"{i}. Refresh")
        choices[i] = self.refresh_data
        i+=1
        print(f"{i}. Clear")
        choices[i] = self.clear_completed
        i+=1
        print(f"{i}. Save & Exit")
        choices[i] = self.save_and_exit
        choice = input('Select: ')
        try:
            choices[int(choice)]()
        except ValueError:
            pass

    def save_and_exit(self):
        self.do_continue = False
        resp = self.session.post(self.address+'/save', json=self.auth_session)
        resp = resp.json()
        print(resp['msg'])

    def clear_completed(self):
        self.session.post(self.address+'/clean', json=self.auth_session)

    def scan_menu(self):
        system(self.clear_cmd)
        while True:
            try:
                res = self.session.get(self.address+'/get_dashboard', json=self.auth_session).json()
                system(self.clear_cmd)
                print(self.dashboard_printout(res), end='')
                if self.unnotified_new:
                    self.play_sound(self.unnotified_new[0])
                    self.unnotified_new = list()
                sleep(self.refresh_interval)
            except KeyboardInterrupt: 
                try:
                    id = input('\nID: ')
                    url = self.id_for_target_urls[int(id)] if id.isnumeric() else [v['target_url'] for v in res.values() if v['alias']==id][0]
                    if url: self.open_url_in_browser(url)
                except (KeyboardInterrupt, KeyError):
                    break

    def play_sound(self, filename:str=''):
        if not path.exists(self.SOUND_PATH.substitute(filename=filename)):
            filename = self.default_local_sound
        playsound(self.SOUND_PATH.substitute(filename=filename))

    def open_url_in_browser(self, url):
        system(f"{config['browser']} {url}")
        try:
            self.already_matched.remove(url)
        except KeyError:
            pass

    def add_query_menu(self):
        try:
            system(self.clear_cmd)
            url_ = input('URL: ')
            target_url = input('Target URL: ') or url_
            seq = input('Sequence: ')
            interval = input('Interval (minutes): ')
            cycles_limit = input('cycles_limit: ')
            randomize = input('*Randomize (0-100): ') or 0
            eta = input('*ETA (d-m-Y H:M:S): ') or '0'
            mode = input('*Mode: ') or 'exists'
            is_recurring = input('Recurring: ') or False
            cookies_filename = input('Cookies filename: ')
            alias = input('Alias: ') or url_
            local_sound = input('Local Sound: ')
            q = dict(url=url_, sequence=seq, interval=interval, randomize=randomize, eta=eta, 
                     mode=mode, cycles_limit=cycles_limit, is_recurring=is_recurring, 
                     cookies_filename=cookies_filename, alias=alias, local_sound=local_sound, target_url=target_url)
            q.update(self.auth_session)
            res = self.session.post(self.address+'/add_query', json=q)
            res = res.json()
            if res['success']:
                input('Query Added\nPress any key to continue...')
        except KeyboardInterrupt:
            pass

    def dashboard_printout(self, data:dict) -> str:
        i = 1
        output = "         ALIAS         | FOUND | INTERVAL |  CYCLES  |       LAST_RUN       |\n"
        for u, v in data.items():
            recurring = boolinize(v['is_recurring']) if isinstance(v['is_recurring'], str) else v['is_recurring']
            if v['found']:
                if u not in self.already_matched:
                    match = '!!!'
                    self.unnotified_new.append(v['local_sound'])
                    self.already_matched.add(u)
                else: 
                    match = '+'
            else: 
                if recurring:
                    try: 
                        self.already_matched.remove(u)
                        match = ' '
                    except KeyError:
                        match = ' '
                else:
                    match = ' '
            output += f"{v['alias'][:22]:^22} | {match:^5} | {v['interval']:^8} | {v['cycles']:>3}/{v['cycles_limit']:<4} | {v['last_run'][1:20]:^20} |"+'\n'
            self.id_for_target_urls[i] = v['target_url']; i+=1
        output += 77*'-' + '\nPress Ctrl+c to open a browser' + 9*' ' + f'refresh_rate:{self.refresh_interval}s last_refresh={datetime.now().strftime("%H:%M:%S")}'
        return output
            
    def edit_query(self):
        '''Enter a new loop for editing the query'''
        query_data = self.load_query_for_edit()
        if not query_data['success']:
            print(query_data['msg'])
            input('Press any key...')
            return
        try:
            success = self.form_edit_query(query_data)
        except KeyboardInterrupt:
            success = False
        if success: input('Query Edited\nPress any key to continue...')

    def load_query_for_edit(self):
        system(self.clear_cmd)
        alias = input("Enter the query's alias: ")
        d = dict(alias=alias)
        d.update(self.auth_session)
        res = self.session.get(self.address+'/get_query', json=d)
        return res.json()

    def form_edit_query(self, data):
        url = rlinput('url: ', prefill=data['url'])
        sequence = rlinput('sequence: ', prefill=data['sequence'][0])
        interval = rlinput('interval: ', prefill=data['interval'])
        randomize = rlinput('randomize: ', prefill=data['randomize'])
        eta = rlinput('eta: ', prefill=data['eta'])
        mode = rlinput('mode: ', prefill=data['mode'])
        cycles_limit = rlinput('cycles_limit: ', prefill=data['cycles_limit'])
        cycles = rlinput('cycles: ', prefill=data['cycles'])
        last_run = rlinput('last_run: ', prefill=data['last_run'])
        found = rlinput('found: ', prefill=data['found'])
        is_recurring = rlinput('is_recurring: ', prefill=data['is_recurring'])
        cookies_filename = rlinput('cookies_filename: ', prefill=data['cookies_filename'])
        alias = rlinput('alias: ', prefill=data['alias'])
        local_sound = rlinput('local_sound: ', prefill=data['local_sound'])
        q = dict(url=url, sequence=sequence, interval=interval, randomize=randomize, eta=eta, 
                    mode=mode, cycles=cycles, cycles_limit=cycles_limit, is_recurring=is_recurring,
                    last_run=last_run, found=found, cookies_filename=cookies_filename, alias=alias, 
                    local_sound=local_sound
                 )
        q.update(self.auth_session)
        res = self.session.post(self.address+'/add_query', json=q).json()
        return res['success']

    def refresh_data(self):
        system(self.clear_cmd)
        resp = self.session.post(self.address+'/refresh_data', json=self.auth_session)
        resp = resp.json()
        print(resp['msg'])
        input('Press any key...')


if __name__ == '__main__':
    tui = TUI()
    tui.loop()

