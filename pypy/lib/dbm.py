from ctypes import *
import ctypes.util
import os, sys

class error(Exception):
    def __init__(self, msg):
        self.msg = msg  

    def __str__(self):
        return self.msg

class datum(Structure):
    _fields_ = [
    ('dptr', c_char_p),
    ('dsize', c_int),
    ]

class dbm(object):
    def __init__(self, dbmobj):
        self._aobj = dbmobj

    def close(self):
        if not self._aobj:
            raise error('DBM object has already been closed')
        getattr(lib, funcs['close'])(self._aobj)
        self._aobj = None

    def __del__(self):
        if self._aobj:
            self.close()

    def keys(self):
        if not self._aobj:
            raise error('DBM object has already been closed')
        allkeys = []
        k = getattr(lib, funcs['firstkey'])(self._aobj)
        while k.dptr:
            allkeys.append(k.dptr[:k.dsize])
            k = getattr(lib, funcs['nextkey'])(self._aobj)
        return allkeys

    def get(self, key, default=None):
        if not self._aobj:
            raise error('DBM object has already been closed')
        dat = datum()
        dat.dptr = c_char_p(key)
        dat.dsize = c_int(len(key))
        k = getattr(lib, funcs['fetch'])(self._aobj, dat)
        if k.dptr:
            return k.dptr[:k.dsize]
        if getattr(lib, funcs['error'])(self._aobj):
            getattr(lib, funcs['clearerr'])(self._aobj)
            raise error("")
        return default

    def __len__(self):
        return len(self.keys())

    def __getitem__(self, key):
        value = self.get(key)
        if value is None:
            raise KeyError(key)
        return value

    def __setitem__(self, key, value):
        if not self._aobj: 
            raise error('DBM object has already been closed')
        dat = datum()
        dat.dptr = c_char_p(key)
        dat.dsize = c_int(len(key))
        data = datum()
        data.dptr = c_char_p(value)
        data.dsize = c_int(len(value))
        status = getattr(lib, funcs['store'])(self._aobj, dat, data, lib.DBM_REPLACE)
        if getattr(lib, funcs['error'])(self._aobj):
            getattr(lib, funcs['clearerr'])(self._aobj)
            raise error("")
        return status

    def setdefault(self, key, default=''):
        if not self._aobj:
            raise error('DBM object has already been closed')
        dat = datum()
        dat.dptr = c_char_p(key)
        dat.dsize = c_int(len(key))
        k = getattr(lib, funcs['fetch'])(self._aobj, dat)
        if k.dptr:
            return k.dptr[:k.dsize]
        data = datum()
        data.dptr = c_char_p(default)
        data.dsize = c_int(len(default))
        status = getattr(lib, funcs['store'])(self._aobj, dat, data, lib.DBM_INSERT)
        if status < 0:
            getattr(lib, funcs['clearerr'])(self._aobj)
            raise error("cannot add item to database")
        return default

    def has_key(self, key):
        if not self._aobj:
            raise error('DBM object has already been closed')
        dat = datum()
        dat.dptr = c_char_p(key)
        dat.dsize = c_int(len(key))
        k = getattr(lib, funcs['fetch'])(self._aobj, dat)
        if k.dptr:
            return True
        return False

    def __delitem__(self, key):
        if not self._aobj:
            raise error('DBM object has already been closed')
        dat = datum()
        dat.dptr = c_char_p(key)
        dat.dsize = c_int(len(key))
        status = getattr(lib, funcs['delete'])(self._aobj, dat)
        if status < 0:
            raise KeyError(key)

### initialization: Berkeley DB versus normal DB

def _init_func(name, argtypes=None, restype=None):
    try:
        func = getattr(lib, '__db_ndbm_' + name)
        funcs[name] = '__db_ndbm_' + name
    except AttributeError:
        func = getattr(lib, 'dbm_' + name)
        funcs[name] = 'dbm_' + name
    if argtypes is not None:
        func.argtypes = argtypes
    if restype is not None:
        func.restype = restype

if sys.platform != 'darwin':
    libpath = ctypes.util.find_library('db')
    if not libpath:
        # XXX this is hopeless...
        libpath = ctypes.util.find_library('db-4.5')
        if not libpath:
            raise ImportError("Cannot find dbm library")
    lib = CDLL(libpath) # Linux
    _platform = 'bdb'
else:
    lib = CDLL("/usr/lib/libdbm.dylib") # OS X
    _platform = 'osx'

library = "GNU gdbm"

funcs = {}
_init_func('open', [c_char_p, c_int, c_int])
_init_func('close', restype=c_void_p)
_init_func('firstkey', restype=datum)
_init_func('nextkey', restype=datum)
_init_func('fetch', restype=datum)
_init_func('store', restype=c_int)
_init_func('error')
_init_func('delete', restype=c_int)

lib.DBM_INSERT = 0
lib.DBM_REPLACE = 1

def open(filename, flag='r', mode=0666):
    "open a DBM database"
    openflag = 0

    try:
        openflag = {
            'r': os.O_RDONLY,
            'rw': os.O_RDWR,
            'w': os.O_RDWR | os.O_CREAT,
            'c': os.O_RDWR | os.O_CREAT,
            'n': os.O_RDWR | os.O_CREAT | os.O_TRUNC,
            }[flag]
    except KeyError, e:
        raise error("arg 2 to open should be 'r', 'w', 'c', or 'n'")

    a_db = getattr(lib, funcs['open'])(filename, openflag, mode)
    if a_db == 0:
        raise error("Could not open file %s.db" % filename)
    return dbm(a_db)
