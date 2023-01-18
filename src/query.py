import aiohttp
from bs4 import BeautifulSoup
from common import *
import re
import json



class Query:
    '''Represents a single search'''

    def __init__(self, url:str, sequence:str, cookies:dict=None):
        self.url = url
        self.sequence:list = [s.lower() for s in sequence.split('|')]
        self.session = aiohttp.ClientSession()
        self.cookies = cookies

    def __repr__(self):
        return f"Query(url={self.url}, sequence={self.sequence})"

    async def close_session(self):
        await self.session.close()

    async def run(self) -> bool:
        '''Returns True if the searched sequence exists'''
        async with self.session.get(self.url, cookies=self.cookies) as resp:
            html = await resp.text()
        parsed_html = BeautifulSoup(html, 'html.parser')
        res = any(re.search(pattern, str(parsed_html).lower()) for pattern in self.sequence)
        register_log(f'Run query for {self.url=} -> "{self.sequence}" found: {res}')
        return res 

