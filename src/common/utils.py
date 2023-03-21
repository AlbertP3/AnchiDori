
QSTAT_CODES = {
    -1: 'Not Yet Ran',
    0: 'OK',
    1: 'Access Denied',
    2: 'Connection Lost',
}

__true_values = {'true','yes','1','on', True}
def boolinize(s:str):
    return s in __true_values

def safe_division(x, y, default=0):
    try:
        return x / y
    except ZeroDivisionError:
        return default
