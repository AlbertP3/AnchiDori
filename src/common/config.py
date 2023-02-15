import configparser

class Config:
    '''Loads .ini file to a dict. Should be declared ONCE per service'''

    def __init__(self, path:str):
        self.PATH_TO_DICT = path
        self.parser = configparser.RawConfigParser(inline_comment_prefixes=None)
        self.refresh()
    
    def __getitem__(self, key):
        return self.config[key]

    def get(self, key, default=None):
        return self.config.get(key, default)

    def refresh(self):
        self.parser.read(self.PATH_TO_DICT)
        self.config = dict(self.parser.items('PARAMETERS'))

    def save(self):
        for k, v in self.config.items():
           self.parser.set('PARAMETERS', k, v)
        with open(self.PATH_TO_DICT, 'w') as configfile:
            self.parser.write(configfile)

    def update(self, modified_dict:dict):
        self.config.update(modified_dict)

