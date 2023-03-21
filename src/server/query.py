from datetime import datetime
from dataclasses import dataclass
from bs4 import BeautifulSoup
from server.utils import register_log, config, safe_date_fmt, safe_strptime
from common.utils import boolinize
import requests
import re


captcha_kw = set(config['captcha_kw'].split(';'))

class Query:
    '''Represents a single search'''

    def __init__(self, url:str, sequence:str, cookies:dict=dict(), min_matches:int=1, mode:str='exists'):
        self.url = url
        self.min_matches = min_matches
        self.re_compilers:list = [re.compile(s.lower()) for s in sequence.split('|')]
        self.cookies = cookies
        self.headers = {'User-Agent': config['user_agent']}
        self.mode = mode.lower() == 'exists'
        self.allowed_chars = 'qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM_1234567890'
        self.do_dump_page_content = boolinize(config['dump_page_content'])

    def __repr__(self):
        return f"Query(url={self.url}, re_compilers={self.re_compilers})"

    async def close_session(self):
        # Kept in case an aiohttp.ClientSession is needed
        #self.session.close()
        pass

    def run(self) -> tuple[bool, int]:
        '''Returns True if the searched sequences exist'''
        status_code = 0
        try:
            #TODO add headers if turns out to be needed
            html = requests.get(self.url, cookies=self.cookies).text 
            parsed_html = str(BeautifulSoup(html, 'html.parser')).lower()
            res = sum(len(r.findall(parsed_html)) for r in self.re_compilers)
            if res == 0:
                matched_kws = {kw for kw in captcha_kw if kw in parsed_html}
                if matched_kws: 
                    register_log(f'Page Access Denied: {matched_kws}', 'WARNING')
                    status_code = 1
            if self.do_dump_page_content: self.dump_page_content(parsed_html)
        except requests.exceptions.ConnectionError:
            register_log(f'Connection Lost during query: {self.url}', 'ERROR')
            status_code = 2
            res = 0
        return (res >= self.min_matches) == self.mode, status_code

    def dump_page_content(self, parsed_html:str):
        filename = '_'.join(re.split(rf'[^{self.allowed_chars}]+', self.url))
        with open(f'page_dump/{filename}.txt', 'w') as f:
            f.write(parsed_html)
        register_log(f"Dumped content of a page {self.url}")
            


@dataclass
class query_parameters:
    # Used as a reference
    uid:str
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
    last_match_datetime:datetime = datetime(1970, 1, 1)
    min_matches:int = 1
    is_new:bool = False
    status:int=-1  # common.utils.QSTAT_CODES


def serialize(d:dict) -> dict:
    '''Prepare object to be sent as a web response'''
    return dict(
        url = d['url'],
        uid = d['uid'],
        target_url = d['target_url'] or d['url'],
        sequence = d['sequence'],
        interval = d['interval'],
        randomize = d['randomize'],
        eta = safe_date_fmt(d['eta']),
        mode = d['mode'],
        cycles_limit = d['cycles_limit'],
        cycles = d['cycles'],
        last_run = safe_date_fmt(d['last_run']),
        found = d['found'],
        is_recurring = d['is_recurring'],
        cookies_filename = d['cookies_filename'],
        alias = d['alias'] or d['url'],
        local_sound = d['local_sound'],
        last_match_datetime = safe_date_fmt(d['last_match_datetime']),
        is_new = d.get('is_new', False),
        min_matches = d['min_matches'],
        status = d['status']
    )


def parse_serialized(d:dict) -> dict:
    '''Restore objects properties '''
    return dict(
        url = str(d['url']),
        uid = str(d['uid']),
        target_url = str(d['target_url'] or d['url']),
        sequence = str(d['sequence']),
        interval = float(d['interval']),
        randomize = int(d['randomize']),
        eta = safe_strptime(d['eta']),
        mode = str(d['mode']),
        cycles_limit = int(d['cycles_limit']),
        cycles = int(d.get('cycles', 0)),
        last_run = safe_strptime(d['last_run']),
        found = boolinize(d['found']),
        is_recurring = boolinize(d['is_recurring']),
        cookies_filename = str(d['cookies_filename']),
        alias = str(d['alias'] or d['url']),
        local_sound = str(d['local_sound']),
        last_match_datetime = safe_strptime(d['last_match_datetime']),
        min_matches = int(d['min_matches']),
        status = int(d['status'])
    )
