"""
Built-in functions.
"""

from pypy.annotation.model import SomeInteger, SomeObject, SomeChar, SomeBool
from pypy.annotation.model import SomeList, SomeString, SomeTuple
from pypy.annotation.factory import ListFactory, getbookkeeper
from pypy.objspace.flow.model import Constant
import pypy.objspace.std.restricted_int

# convenience only!
def immutablevalue(x):
    return getbookkeeper().immutablevalue(x)

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

def our_issubclass(cls1, cls2):
    """ we're going to try to be less silly in the face of old-style classes"""
    return cls2 is object or issubclass(cls1, cls2)

def builtin_isinstance(s_obj, s_type):
    s = SomeBool() 
    if s_type.is_constant():
        typ = s_type.const
        # XXX bit of a hack:
        if issubclass(typ, (int, long)):
            typ = int
        if s_obj.is_constant():
            s.const = isinstance(s_obj.const, typ)
        elif our_issubclass(s_obj.knowntype, typ):
            s.const = True 
        elif not our_issubclass(typ, s_obj.knowntype): 
            s.const = False 
        # XXX HACK HACK HACK
        # XXX HACK HACK HACK
        # XXX HACK HACK HACK
        bk = getbookkeeper()
        fn, block, i = bk.position_key
        annotator = bk.annotator
        op = block.operations[i]
        assert op.opname == "simple_call" 
        assert len(op.args) == 3
        assert op.args[0] == Constant(isinstance)
        assert annotator.binding(op.args[1]) is s_obj
        s.knowntypedata = (op.args[1], bk.valueoftype(typ))
    return s 

def builtin_issubclass(s_cls1, s_cls2):
    if s_cls1.is_constant() and s_cls2.is_constant():
        return immutablevalue(issubclass(s_cls1, s_cls2))
    else:
        return SomeBool()

def builtin_getattr(s_obj, s_attr, s_default=None):
    if not s_attr.is_constant() or not isinstance(s_attr.const, str):
        print "UN-RPYTHONIC-WARNING", \
              'getattr(%r, %r) is not RPythonic enough' % (s_obj, s_attr)
        return SomeObject()
    return s_obj.getattr(s_attr)

def builtin_hasattr(s_obj, s_attr):
    if not s_attr.is_constant() or not isinstance(s_attr.const, str):
        print "UN-RPYTHONIC-WARNING", \
              'hasattr(%r, %r) is not RPythonic enough' % (s_obj, s_attr)
    return SomeBool()

def builtin_callable(s_obj):
    return SomeBool()

def builtin_tuple(s_iterable):
    if isinstance(s_iterable, SomeTuple):
        return s_iterable
    return SomeObject()

def builtin_type(s_obj, *moreargs):
    if moreargs:
        raise Exception, 'type() called with more than one argument'
    if s_obj.is_constant():
        return immutablevalue(type(s_obj.const))
    return SomeObject()

def builtin_str(s_obj):
    return SomeString()

def builtin_list(s_iterable):
    factory = getbookkeeper().getfactory(ListFactory)
    s_iter = s_iterable.iter()
    factory.generalize(s_iter.next())
    return factory.create()

def builtin_apply(*stuff):
    print "XXX ignoring apply%r" % (stuff,)
    return SomeObject()

# collect all functions
import __builtin__
BUILTIN_ANALYZERS = {}
for name, value in globals().items():
    if name.startswith('builtin_'):
        original = getattr(__builtin__, name[8:])
        BUILTIN_ANALYZERS[original] = value

BUILTIN_ANALYZERS[pypy.objspace.std.restricted_int.r_int] = builtin_int
BUILTIN_ANALYZERS[pypy.objspace.std.restricted_int.r_uint] = restricted_uint
