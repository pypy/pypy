"""
Built-in functions.
"""

from pypy.annotation.model import SomeInteger, SomeObject
from pypy.annotation.factory import ListFactory, getbookkeeper


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


# collect all functions
import __builtin__
BUILTIN_FUNCTIONS = {}
for name, value in globals().items():
    if name.startswith('builtin_'):
        original = getattr(__builtin__, name[8:])
        BUILTIN_FUNCTIONS[original] = value
