"""
Built-in functions.
"""

from pypy.annotation.model import SomeInteger, SomeObject
from pypy.annotation.factory import ListFactory, getbookkeeper
import pypy.objspace.std.restricted_int


def builtin_len(s_obj):
    return s_obj.len()

def builtin_range(*args):
    factory = getbookkeeper().getfactory(ListFactory)
    factory.generalize(SomeInteger())  # XXX nonneg=...
    return factory.create()

def builtin_pow(s_base, s_exponent, *args):
    if s_base.knowntype is s_exponent.knowntype is int:
        return SomeInteger()
    else:
        return SomeObject()

def builtin_int(s_obj):     # we can consider 'int' as a function
    return SomeInteger()

def restricted_uint(s_obj):    # for r_uint
    return SomeInteger(nonneg=True, unsigned=True)


# collect all functions
import __builtin__
BUILTIN_FUNCTIONS = {}
for name, value in globals().items():
    if name.startswith('builtin_'):
        original = getattr(__builtin__, name[8:])
        BUILTIN_FUNCTIONS[original] = value

BUILTIN_FUNCTIONS[pypy.objspace.std.restricted_int.r_int] = builtin_int
BUILTIN_FUNCTIONS[pypy.objspace.std.restricted_int.r_uint] = restricted_uint
