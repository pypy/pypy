

def _genex():
    glob = globals()
    import __builtin__ 
    for name, value in __builtin__.__dict__.items():
        try:
            if issubclass(value, Exception):
                glob[name] = value 
        except TypeError:
            pass

_genex()
del _genex
