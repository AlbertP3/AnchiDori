
__true_values = {'true','yes','1','on', True}
def boolinize(s:str):
    return s in __true_values

def safe_division(x, y, default=0):
    try:
        return x / y
    except ZeroDivisionError:
        return default
