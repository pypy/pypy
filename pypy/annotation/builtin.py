"""
Built-in functions.
"""

from pypy.annotation.model import SomeInteger, SomeObject, SomeChar, SomeBool
from pypy.annotation.model import immutablevalue
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

def builtin_chr(s_int):
    return SomeChar()

def builtin_isinstance(s_obj, s_type):
    # XXX simple case only
    if s_type.is_constant():
        typ = s_type.const
        if issubclass(s_obj.knowntype, typ):
            return immutablevalue(True)
    return SomeBool()

def builtin_getattr(s_obj, s_attr):
    if not s_attr.is_constant() or not isinstance(s_attr.const, str):
        raise Exception, 'getattr(%r, %r) is not RPythonic enough' % (
            s_obj, s_attr)
    return s_obj.getattr(s_attr)

def builtin_type(s_obj, *moreargs):
    if moreargs:
        raise Exception, 'type() called with more than one argument'
    #...
    return SomeObject()

def builtin_str(s_obj):
    return SomeString()

# collect all functions
import __builtin__
BUILTIN_FUNCTIONS = {}
for name, value in globals().items():
    if name.startswith('builtin_'):
        original = getattr(__builtin__, name[8:])
        BUILTIN_FUNCTIONS[original] = value

BUILTIN_FUNCTIONS[pypy.objspace.std.restricted_int.r_int] = builtin_int
BUILTIN_FUNCTIONS[pypy.objspace.std.restricted_int.r_uint] = restricted_uint
