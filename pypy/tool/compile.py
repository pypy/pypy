from __future__ import generators 
cache = {}

def compile2(source, filename='', mode='exec', flags=
            generators.compiler_flag, dont_inherit=0):
    """ central compile hook for pypy initialization 
        purposes. 
    """
    key = (source, filename, mode, flags)
    try:
        co = cache[key]
    except KeyError: 
        co = compile(source, filename, mode, flags) 
        cache[key] = co 
    return co 
