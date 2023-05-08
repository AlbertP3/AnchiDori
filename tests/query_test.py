import logging
import os
from unittest import TestCase
from unittest.mock import Mock, MagicMock, AsyncMock

CWD = os.path.dirname(os.path.abspath(__file__))

import requests
requests.get = Mock()

from . import Query

class fake_response:
    def __init__(self, text) -> None:
        self.text = text


class Test_Query(TestCase):

    def setUp(self) -> None:
        return super().setUp()

    
    def test_run_single_match(self):
        data = fake_response('<head></head><body><div><h1>Hello, World</h1><p>blob</p></div></body>')
        requests.get = Mock(return_value=data)
        q = Query(url=None, sequence='world')
        q.do_dump_page_content = False
        res, s = q.run()
        self.assertEqual(s, 0)
        self.assertTrue(res)

    
    def test_run_multiple_match(self):
        data = fake_response('<div><h1>Hello, World</h1><p>world</p></div>')
        requests.get = Mock(return_value=data)
        q = Query(url=None, sequence='world', min_matches=3)
        q.do_dump_page_content = False
        res, s = q.run()
        self.assertFalse(res)
        self.assertEqual(s, 0)

    
    def test_run_access_denied(self):
        data = fake_response('<div><h1>Hello</h1><p>Permission denied</p></div>')
        requests.get = Mock(return_value=data)
        q = Query(url=None, sequence='world')
        q.do_dump_page_content = False
        res, s = q.run()
        self.assertFalse(res)
        self.assertEqual(s, 1)


    def test_run_connection_lost(self):
        data = fake_response('<div><h1>Hello</h1><p></p></div>')
        requests.get = Mock(side_effect=requests.exceptions.ConnectionError)
        q = Query(url=None, sequence='world')
        q.do_dump_page_content = False
        res, s = q.run()
        self.assertFalse(res)
        self.assertEqual(s, 2)

    
    def test_multiple_regex(self):
        data = fake_response('<div><h1>cbt-1c9</h1><p>dam1cs</p></div>')
        requests.get = Mock(return_value=data)
        q = Query(url=None, sequence='dam\w+\&cbt-(1|c9)')
        q.do_dump_page_content = False
        res, s = q.run()
        self.assertTrue(res)
        self.assertEqual(s, 0)
