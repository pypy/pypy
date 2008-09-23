from ctypes import *
import ctypes.util
import os

_singleton = 'one'

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
        getattr(lib, funcs['close'])(self._aobj)
        self._aobj = None

    def keys(self):
        if not self._aobj:
            raise error('DBM object has already been closed')
        allkeys = []
        k = getattr(lib, funcs['firstkey'])(self._aobj)
        while k.dptr:
            allkeys.append(k.dptr[:k.dsize])
            k = getattr(lib, funcs['nextkey'])(self._aobj)
        return allkeys

    def get(self, key, default=_singleton):
        if not self._aobj:
            raise error('DBM object has already been closed')
        dat = datum()
        dat.dptr = c_char_p(key)
        dat.dsize = c_int(len(key))
        k = getattr(lib, funcs['fetch'])(self._aobj, dat)
        if k.dptr:
            return k.dptr[:k.dsize]
        if default is _singleton:
            raise KeyError
        if getattr(lib, funcs['error'])(self._aobj):
            getattr(lib, funcs['clearerr'])(self._aobj)
            raise error("")
        return default

    def __len__(self):
        return len(self.keys())

    def __getitem__(self, key):
        assert isinstance(key, str)
        value = self.get(key)
        if value is None:
            raise KeyError

    def _set(self, key, value):
        if not self._aobj: 
            raise error('DBM object has already been closed')
        if not isinstance(key, str):
            raise TypeError("dbm mappings have string indices only")
        dat = datum()
        dat.dptr = c_char_p(key)
        dat.dsize = c_int(len(key))
        if value == None:
            status = getattr(lib, funcs['delete'])(self._aobj, dat)
            if status < 0:
                getattr(lib, funcs['clearerr'])(self._aobj)
                raise KeyError(key)
        else:
            if not isinstance(value, str):
                raise TypeError("dbm mappings have string indices only")
            data = datum()
            data.dptr = c_char_p(value)
            data.dsize = c_int(len(value))
            status = getattr(lib, funcs['store'])(self._aobj, dat, data, lib.DBM_INSERT)
            if status == 1:
                status = getattr(lib, funcs['store'])(self._aobj, dat, data, lib.DBM_REPLACE)
        if getattr(lib, funcs['error'])(self._aobj):
            getattr(lib, funcs['clearerr'])(self._aobj)
            raise error("")
        return status

    def setdefault(self, key, default=None):
        if not self._aobj:
            raise error('DBM object has already been closed')
        dat = datum()
        dat.dptr = c_char_p(key)
        dat.dsize = c_int(len(key))
        k = getattr(lib, funcs['fetch'])(self._aobj, dat)
        if k.dptr:
            return k.dptr[:k.dsize]
        if default:
            data = datum()
            data.dptr = c_char_p(default)
            data.dsize = c_int(len(default))
            status = getattr(lib, funcs['store'])(self._aobj, dat, data, lib.DBM_INSERT)
            if status < 0:
                getattr(lib, funcs['clearerr'])(self._aobj)
                raise error("cannot add item to database")
            return default
        return None

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

    def __setitem__(self, key, value):
        if not isinstance(key, str) and isinstance(value, str):
            raise error("dbm mappings have string indices only")
        self._set(key, value)

# initialization for Berkeley DB
_bdb_funcs = {
    'open': '__db_ndbm_open',
    'close': '__db_ndbm_close',
    'firstkey': '__db_ndbm_firstkey',
    'nextkey': '__db_ndbm_nextkey',
    'fetch': '__db_ndbm_fetch',
    'store': '__db_ndbm_store',
    'error': '__db_ndbm_error',
    'delete': '__db_ndbm_delete',
}

_normal_funcs = {
    'open': 'dbm_open',
    'close': 'dbm_close',
    'firstkey': 'dbm_firstkey',
    'nextkey': 'dbm_nextkey',
    'fetch': 'dbm_fetch',
    'store': 'dbm_store',
    'error': 'dbm_error',
    'delete': 'dbm_delete',
}

try:
    libpath = ctypes.util.find_library('db')
    if not libpath: raise
    lib = CDLL(libpath) # Linux
    _platform = 'bdb'
    lib.__db_ndbm_open.argtypes = [c_char_p, c_int, c_int]
    lib.__db_ndbm_close.restype = c_void_p
    lib.__db_ndbm_firstkey.restype = datum
    lib.__db_ndbm_nextkey.restype = datum
    lib.__db_ndbm_fetch.restype = datum
    lib.__db_ndbm_store.restype = c_int
    funcs = _bdb_funcs
except:
    lib = CDLL("/usr/lib/libdbm.dylib") # OS X
    _platform = 'osx'
    lib.dbm_open.argtypes = [c_char_p, c_int, c_int]
    lib.dbm_close.restype = c_void_p
    lib.dbm_firstkey.restype = datum
    lib.dbm_nextkey.restype = datum
    lib.dbm_fetch.restype = datum
    lib.dbm_store.restype = c_int
    funcs = _normal_funcs



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
