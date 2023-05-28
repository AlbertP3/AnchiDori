from bs4 import BeautifulSoup
from copy import deepcopy
import logging
from server.utils import safe_date_fmt
from server import config, CWD
from common.utils import boolinize
import requests
import re
import os

LOGGER = logging.getLogger('Query')
PAGEDUMP = os.path.realpath(f'{CWD}/../../page_dump')

captcha_kw = set(config['captcha_kw'].lower().split(';'))

class Query:
    '''Represents a single search'''

    def __init__(self, url:str, sequence:str, cookies:dict=dict(), min_matches:int=1, mode:str='exists'):
        self.url = url
        self.min_matches = min_matches
        self.re_compilers:list = [re.compile(s.lower()) for s in sequence.split('\&')]
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
        status_code = 0
        try:
            #TODO add headers if turns out to be needed
            html = requests.get(self.url, cookies=self.cookies).text 
            parsed_html = str(BeautifulSoup(html, 'html.parser')).lower()
            res = sum(len(r.findall(parsed_html)) for r in self.re_compilers)
            if res == 0:
                matched_kws = {kw for kw in captcha_kw if kw in parsed_html}
                if matched_kws: 
                    LOGGER.warning(f'Page Access Denied: {matched_kws}')
                    status_code = 1
            if self.do_dump_page_content: self.dump_page_content(parsed_html)
        except requests.exceptions.ConnectionError:
            LOGGER.warning(f'Connection Lost during query: {self.url}')
            status_code = 2
            res = 0
        return (res >= self.min_matches) == self.mode, status_code

    def dump_page_content(self, parsed_html:str):
        filename = '_'.join(re.split(rf'[^{self.allowed_chars}]+', self.url))
        with open(f'{PAGEDUMP}/{filename}.txt', 'w') as f:
            f.write(parsed_html)
        LOGGER.debug(f"Dumped content of a page {self.url}")
            


def serialize(d:dict) -> dict:
    '''Prepare Query object to be sent as a web response'''
    d = deepcopy(d)
    template = dict(
        eta = lambda x: x.get('raw', ''),
        last_run = lambda x: safe_date_fmt(x),
        last_match_datetime = lambda x: safe_date_fmt(x),
    )
    for k, v in template.items():
        try:
            d[k] = v(d[k])
        except AttributeError as e:
            pass
    try: del d['query']
    except KeyError: pass
    d['target_url'] = d['target_url'] or d['url']
    return d
   
