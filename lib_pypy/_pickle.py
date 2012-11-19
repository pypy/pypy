#
# One-liner implementation of cPickle
#

import marshal
import struct
import sys
import io
from pickle import _Pickler, _Unpickler, dump, dumps, PickleError, PicklingError, UnpicklingError
from pickle import __doc__, __version__, format_version, compatible_formats
from types import *
from copyreg import dispatch_table
from copyreg import _extension_registry, _inverted_registry, _extension_cache

try: from __pypy__ import builtinify
except ImportError: builtinify = lambda f: f

# These are purely informational; no code uses these.
format_version = "3.0"                  # File format version we write
compatible_formats = ["1.0",            # Original protocol 0
                      "1.1",            # Protocol 0 with INST added
                      "1.2",            # Original protocol 1
                      "1.3",            # Protocol 1 with BINFLOAT added
                      "2.0",            # Protocol 2
                      "3.0",            # Protocol 3
                      ]                 # Old format versions we can read

# Keep in synch with cPickle.  This is the highest protocol number we
# know how to read.
HIGHEST_PROTOCOL = 3

# The protocol we write by default.  May be less than HIGHEST_PROTOCOL.
# We intentionally write a protocol that Python 2.x cannot read;
# there are too many issues with that.
DEFAULT_PROTOCOL = 3

BadPickleGet = KeyError

# An instance of _Stop is raised by Unpickler.load_stop() in response to
# the STOP opcode, passing the object that is the result of unpickling.
class _Stop(Exception):
    def __init__(self, value):
        self.value = value

# Jython has PyStringMap; it's a dict subclass with string keys
try:
    from org.python.core import PyStringMap
except ImportError:
    PyStringMap = None

# Pickle opcodes.  See pickletools.py for extensive docs.  The listing
# here is in kind-of alphabetical order of 1-character pickle code.
# pickletools groups them by purpose.

MARK           = b'('   # push special markobject on stack
STOP           = b'.'   # every pickle ends with STOP
POP            = b'0'   # discard topmost stack item
POP_MARK       = b'1'   # discard stack top through topmost markobject
DUP            = b'2'   # duplicate top stack item
FLOAT          = b'F'   # push float object; decimal string argument
INT            = b'I'   # push integer or bool; decimal string argument
BININT         = b'J'   # push four-byte signed int
BININT1        = b'K'   # push 1-byte unsigned int
LONG           = b'L'   # push long; decimal string argument
BININT2        = b'M'   # push 2-byte unsigned int
NONE           = b'N'   # push None
PERSID         = b'P'   # push persistent object; id is taken from string arg
BINPERSID      = b'Q'   #  "       "         "  ;  "  "   "     "  stack
REDUCE         = b'R'   # apply callable to argtuple, both on stack
STRING         = b'S'   # push string; NL-terminated string argument
BINSTRING      = b'T'   # push string; counted binary string argument
SHORT_BINSTRING= b'U'   #  "     "   ;    "      "       "      " < 256 bytes
UNICODE        = b'V'   # push Unicode string; raw-unicode-escaped'd argument
BINUNICODE     = b'X'   #   "     "       "  ; counted UTF-8 string argument
APPEND         = b'a'   # append stack top to list below it
BUILD          = b'b'   # call __setstate__ or __dict__.update()
GLOBAL         = b'c'   # push self.find_class(modname, name); 2 string args
DICT           = b'd'   # build a dict from stack items
EMPTY_DICT     = b'}'   # push empty dict
APPENDS        = b'e'   # extend list on stack by topmost stack slice
GET            = b'g'   # push item from memo on stack; index is string arg
BINGET         = b'h'   #   "    "    "    "   "   "  ;   "    " 1-byte arg
INST           = b'i'   # build & push class instance
LONG_BINGET    = b'j'   # push item from memo on stack; index is 4-byte arg
LIST           = b'l'   # build list from topmost stack items
EMPTY_LIST     = b']'   # push empty list
OBJ            = b'o'   # build & push class instance
PUT            = b'p'   # store stack top in memo; index is string arg
BINPUT         = b'q'   #   "     "    "   "   " ;   "    " 1-byte arg
LONG_BINPUT    = b'r'   #   "     "    "   "   " ;   "    " 4-byte arg
SETITEM        = b's'   # add key+value pair to dict
TUPLE          = b't'   # build tuple from topmost stack items
EMPTY_TUPLE    = b')'   # push empty tuple
SETITEMS       = b'u'   # modify dict by adding topmost key+value pairs
BINFLOAT       = b'G'   # push float; arg is 8-byte float encoding

TRUE           = b'I01\n'  # not an opcode; see INT docs in pickletools.py
FALSE          = b'I00\n'  # not an opcode; see INT docs in pickletools.py

# Protocol 2

PROTO          = b'\x80'  # identify pickle protocol
NEWOBJ         = b'\x81'  # build object by applying cls.__new__ to argtuple
EXT1           = b'\x82'  # push object from extension registry; 1-byte index
EXT2           = b'\x83'  # ditto, but 2-byte index
EXT4           = b'\x84'  # ditto, but 4-byte index
TUPLE1         = b'\x85'  # build 1-tuple from stack top
TUPLE2         = b'\x86'  # build 2-tuple from two topmost stack items
TUPLE3         = b'\x87'  # build 3-tuple from three topmost stack items
NEWTRUE        = b'\x88'  # push True
NEWFALSE       = b'\x89'  # push False
LONG1          = b'\x8a'  # push long from < 256 bytes
LONG4          = b'\x8b'  # push really big long

_tuplesize2code = [EMPTY_TUPLE, TUPLE1, TUPLE2, TUPLE3]

# Protocol 3 (Python 3.x)

BINBYTES       = b'B'   # push bytes; counted binary string argument
SHORT_BINBYTES = b'C'   #  "     "   ;    "      "       "      " < 256 bytes

# ____________________________________________________________
# XXX some temporary dark magic to produce pickled dumps that are
#     closer to the ones produced by cPickle in CPython

class Pickler(_Pickler):
    def __init__(self, *args, **kw):
        self.__f = None
        if len(args) == 1 and isinstance(args[0], int):
            self.__f = io.BytesIO()
            _Pickler.__init__(self, self.__f, args[0], **kw)
        else:
            _Pickler.__init__(self, *args, **kw)

    def memoize(self, obj):
        self.memo[id(None)] = None   # cPickle starts counting at one
        return _Pickler.memoize(self, obj)

    def getvalue(self):
        return self.__f and self.__f.getvalue()

@builtinify
def dump(obj, file, protocol=None):
    Pickler(file, protocol).dump(obj)

@builtinify
def dumps(obj, protocol=None):
    file = io.BytesIO()
    Pickler(file, protocol).dump(obj)
    return file.getvalue()

# Why use struct.pack() for pickling but marshal.loads() for
# unpickling?  struct.pack() is 40% faster than marshal.dumps(), but
# marshal.loads() is twice as fast as struct.unpack()!
mloads = marshal.loads

# Unpickling machinery

class Unpickler(_Unpickler):
    pass

from pickle import decode_long

def load(file, *, fix_imports=True, encoding="ASCII", errors="strict"):
    return Unpickler(file, fix_imports=fix_imports,
                     encoding=encoding, errors=errors).load()

def loads(s, *, fix_imports=True, encoding="ASCII", errors="strict"):
    if isinstance(s, str):
        raise TypeError("Can't load pickle from unicode string")
    file = io.BytesIO(s)
    return Unpickler(file, fix_imports=fix_imports,
                     encoding=encoding, errors=errors).load()
