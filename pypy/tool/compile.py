from __future__ import generators 
cache = {}

import py
DEBUG = 1

def compile2(source, filename='', mode='exec', flags=
            generators.compiler_flag, dont_inherit=0):
    """ central compile hook for pypy initialization 
        purposes. 
    """
    key = (source, filename, mode, flags)
    try:
        co = cache[key]
        #print "***** duplicate code ******* "
        #print source 
    except KeyError: 
        if DEBUG: 
            co = py.code.compile(source, filename, mode, flags) 
        else: 
            co = compile(source, filename, mode, flags) 
        cache[key] = co 
    return co 
