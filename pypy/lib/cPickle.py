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
