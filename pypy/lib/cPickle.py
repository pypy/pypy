#
# One-liner implementation of cPickle
#

from pickle import *
from pickle import __doc__, __version__, format_version, compatible_formats

class UnpickleableError(PicklingError):
    def __init__(self, *args):
        self.args=args

    def __str__(self):
        a=self.args
        a=a and type(a[0]) or '(what)'
        return 'Cannot pickle %s objects' % a

class BadPickleGet(UnpicklingError):
    pass

# ____________________________________________________________
# XXX some temporary dark magic to produce pickled dumps that are
#     closer to the ones produced by cPickle in CPython

from pickle import StringIO

PythonPickler = Pickler
class Pickler(PythonPickler):
    def memoize(self, obj):
        self.memo[None] = None   # cPickle starts counting at one
        return PythonPickler.memoize(self, obj)

def dump(obj, file, protocol=None, bin=None):
    Pickler(file, protocol, bin).dump(obj)

def dumps(obj, protocol=None, bin=None):
    file = StringIO()
    Pickler(file, protocol, bin).dump(obj)
    return file.getvalue()
