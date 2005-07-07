"""
information table about external functions for annotation/ rtyping and backends
"""
import os
import time
import types

class ExtFuncInfo:
    def __init__(self, func, annotation, ll_function, ll_annotable, backend_functiontemplate):
        self.func = func
        self.annotation = annotation
        self.ll_function = ll_function
        self.ll_annotable = ll_annotable
        self.backend_functiontemplate = backend_functiontemplate

table = {}
def declare(func, annotation, ll_function, ll_annotable=False, backend_functiontemplate=None):
    # annotation can be a function computing the annotation
    # or a simple python type from which an annotation will be constructed
    global table
    if not isinstance(annotation, types.FunctionType):
        typ = annotation
        def annotation(*args_s):
            from pypy.annotation import bookkeeper
            return bookkeeper.getbookkeeper().valueoftype(typ)
    table[func] = ExtFuncInfo(func, annotation, ll_function, ll_annotable, backend_functiontemplate)

# utility conversion functions
def to_rstr(s):
    from pypy.rpython import rstr
    p = rstr.malloc(rstr.STR, len(s))
    for i in range(len(s)):
        p.chars[i] = s[i]
    return p

def from_rstr(rs):
    return ''.join(rs.chars)

# dummy low-level implementations for the external functions
def ll_os_open(fname, flag, mode):
    return os.open(from_rstr(fname), flag, mode)

def ll_os_read(fd, n):
    return to_rstr(os.read(fd, n))
    
def ll_os_write(fd, astring):
    return os.write(fd, from_rstr(astring))

def ll_os_close(fd):
    os.close(fd)
    
def ll_os_getcwd():
    return to_rstr(os.getcwd())

def ll_os_dup(fd):
    return os.dup(fd)

def ll_time_time():
    return time.time()

def ll_time_clock():
    return time.clock()

def ll_time_sleep(t):
    time.sleep(t)


nonefactory = lambda *args: None

# external function declarations
declare(os.open   , int        , ll_os_open)
declare(os.read   , str        , ll_os_read)
declare(os.write  , int        , ll_os_write)
declare(os.close  , nonefactory, ll_os_close)
declare(os.getcwd , str        , ll_os_getcwd)
declare(os.dup    , int        , ll_os_dup)
declare(time.time , float      , ll_time_time)
declare(time.clock, float      , ll_time_clock)
declare(time.sleep, nonefactory, ll_time_sleep)
