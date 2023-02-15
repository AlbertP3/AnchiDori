# Based on: https://github.com/richardpenman/browsercookie
import os
import json
import lz4.block
import sqlite3
import tempfile
from contextlib import contextmanager



@contextmanager
def create_local_copy(cookie_file):
    """
    Make a local copy of the sqlite cookie database and return the new filename.
    This is necessary in case this database is still being written to while the user browses
    to avoid sqlite locking errors.
    """
    if os.path.exists(cookie_file):
        # copy to random name in tmp folder
        tmp_cookie_file = tempfile.NamedTemporaryFile(suffix='.sqlite').name
        open(tmp_cookie_file, 'wb').write(open(cookie_file, 'rb').read())
        yield tmp_cookie_file
    else:
        raise Exception('Can not find cookie file at: ' + cookie_file)
    os.remove(tmp_cookie_file)


def create_cookie(name_, value_):
    return {name_:value_}


class Firefox():
    def __init__(self):
        self.path = os.path.join(os.path.expanduser('~'), '.mozilla/firefox/7koyiezt.default-release')
        self.cookie_files = [os.path.join(self.path, 'cookies.sqlite')]

    def load(self, host):
        cookie_jar = dict()
        for cookie in self.get_cookies(host):
            cookie_jar.update(cookie)
        return cookie_jar

    def get_cookies(self, host):
        for cookie_file in self.cookie_files:
            with create_local_copy(cookie_file) as tmp_cookie_file:
                con = sqlite3.connect(tmp_cookie_file)
                cur = con.cursor()
                cur.execute(f"SELECT name, value FROM moz_cookies WHERE host LIKE '%{host}%'")

                for item in cur.fetchall():
                    yield create_cookie(*item)
                con.close()

                session_files = (os.path.join(os.path.dirname(cookie_file), 'sessionstore.js'),
                    os.path.join(self.path, 'sessionstore-backups', 'recovery.js'),
                    os.path.join(self.path, 'sessionstore-backups', 'recovery.json'),
                    os.path.join(self.path, 'sessionstore-backups', 'recovery.jsonlz4'))
                for file_path in session_files:
                    if os.path.exists(file_path):
                        if file_path.endswith('4'):
                            try:
                                session_file = open(file_path, 'rb')
                                # skip the first 8 bytes to avoid decompress failure (custom Mozilla header)
                                session_file.seek(8)
                                json_data = json.loads(lz4.block.decompress(session_file.read()).decode())
                            except IOError as e:
                                print('Could not read file:', str(e))
                            except ValueError as e:
                                print('Error parsing Firefox session file:', str(e))
                        else:
                            try:
                                json_data = json.loads(open(file_path, 'rb').read().decode('utf-8'))
                            except IOError as e:
                                print('Could not read file:', str(e))
                            except ValueError as e:
                                print('Error parsing firefox session JSON:', str(e))

                if 'json_data' in locals():
                    for window in json_data.get('windows', []):
                        for cookie in window.get('cookies', []):
                            yield dict(name=cookie.get('name', ''), value=cookie.get('value', '')) 
                else:
                    print('Could not find any Firefox session files')

