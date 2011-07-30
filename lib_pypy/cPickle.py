#
# One-liner implementation of cPickle
#

from pickle import *
from pickle import __doc__, __version__, format_version, compatible_formats

try: from __pypy__ import builtinify
except ImportError: builtinify = lambda f: f


BadPickleGet = KeyError
UnpickleableError = PicklingError

# ____________________________________________________________
# XXX some temporary dark magic to produce pickled dumps that are
#     closer to the ones produced by cPickle in CPython

from pickle import StringIO

PythonPickler = Pickler
class Pickler(PythonPickler):
    def __init__(self, *args, **kw):
        self.__f = None
        if len(args) == 1 and isinstance(args[0], int):
            self.__f = StringIO()
            PythonPickler.__init__(self, self.__f, args[0], **kw)
        else:
            PythonPickler.__init__(self, *args, **kw)

    def memoize(self, obj):
        self.memo[id(None)] = None   # cPickle starts counting at one
        return PythonPickler.memoize(self, obj)

    def getvalue(self):
        return self.__f and self.__f.getvalue()

@builtinify
def dump(obj, file, protocol=None):
    Pickler(file, protocol).dump(obj)

@builtinify
def dumps(obj, protocol=None):
    file = StringIO()
    Pickler(file, protocol).dump(obj)
    return file.getvalue()
