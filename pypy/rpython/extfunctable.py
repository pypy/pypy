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
def declare(func, annotation, ll_function, ll_annotable=True, backend_functiontemplate=None):
    # annotation can be a function computing the annotation
    # or a simple python type from which an annotation will be constructed
    global table
    if not isinstance(annotation, types.FunctionType):
        typ = annotation
        def annotation(*args_s):
            from pypy.annotation import bookkeeper
            return bookkeeper.getbookkeeper().valueoftype(typ)
    table[func] = ExtFuncInfo(func, annotation, ll_function, ll_annotable, backend_functiontemplate)

# low-level helpers representing the external functions
def ll_os_open(fname, mode):
    return os.open(''.join(fname.chars), mode)

def ll_os_read(fd, n):
    return os.read(fd, n)
    
def ll_os_write(fd, astring):
    return os.write(fd, astring)
    
def ll_os_close(fd):
    os.close(fd)
    
def ll_os_getcwd():
    cwd = os.getcwd()
    from pypy.rpython import rstr
    p = rstr.malloc(rstr.STR, len(cwd))
    for i in range(len(cwd)):
        p.chars[i] = cwd[i]
    return p

def ll_os_dup(fd):
    return 999

def ll_time_time():
    return time.time()

def ll_time_clock():
    return time.clock()

def ll_time_sleep(t):
    time.sleep(t)

# external function declarations
declare(os.open   , int           , ll_os_open   , True             )   #this is not annotatable actually, but llvm has an issue
declare(os.read   , str           , ll_os_read   , True             )
declare(os.write  , int           , ll_os_write  , True             )
declare(os.close  , lambda a: None, ll_os_close  , True , 'C:close' )
declare(os.getcwd , str           , ll_os_getcwd , True             )
declare(os.dup    , int           , ll_os_dup    , True , 'C:dup'   )
declare(time.time , float         , ll_time_time , True             )
declare(time.clock, float         , ll_time_clock, True             )
declare(time.sleep, lambda a: None, ll_time_sleep, True             )
