"""
Built-in functions.
"""

import types
import sys, math, os, time
from pypy.tool.ansi_print import ansi_print
from pypy.annotation.model import SomeInteger, SomeObject, SomeChar, SomeBool
from pypy.annotation.model import SomeList, SomeString, SomeTuple, SomeSlice
from pypy.annotation.model import SomeUnicodeCodePoint
from pypy.annotation.model import SomeFloat, unionof
from pypy.annotation.model import annotation_to_lltype
from pypy.annotation.model import add_knowntypedata
from pypy.annotation.bookkeeper import getbookkeeper
from pypy.objspace.flow.model import Constant
import pypy.rpython.rarithmetic

# convenience only!
def immutablevalue(x):
    return getbookkeeper().immutablevalue(x)

def constpropagate(func, args_s, s_result):
    """Returns s_result unless all args are constants, in which case the
    func() is called and a constant result is returned (it must be contained
    in s_result).
    """
    args = []
    for s in args_s:
        if not s.is_constant():
            return s_result
        args.append(s.const)
    realresult = func(*args)
    s_realresult = immutablevalue(realresult)
    if not s_result.contains(s_realresult):
        raise Exception("%s%r returned %r, which is not contained in %s" % (
            func, args, realresult, s_result))
    return s_realresult

# ____________________________________________________________

def builtin_range(*args):
    s_step = immutablevalue(1)
    if len(args) == 1:
        s_start = immutablevalue(0)
        s_stop = args[0]
    elif len(args) == 2:
        s_start, s_stop = args
    elif len(args) == 3:
        s_start, s_stop = args[:2]
        s_step = args[2]
    else:
        raise Exception, "range() takes 1 to 3 arguments"
    if not s_step.is_constant():
        raise Exception, "range() step argument should be a constant"
    step = s_step.const
    if step == 0:
        raise Exception, "range() with step zero"
    elif step > 0:
        nonneg = s_start.nonneg
    else:
        nonneg = s_stop.nonneg or (s_stop.is_constant() and s_stop.const >= -1)
    return getbookkeeper().newlist(SomeInteger(nonneg=nonneg), range_step=step)

builtin_xrange = builtin_range # xxx for now allow it

def builtin_bool(s_obj):
    return constpropagate(bool, [s_obj], SomeBool())

def builtin_int(s_obj, s_base=None):
    assert (s_base is None or isinstance(s_base, SomeInteger)
            and s_obj.knowntype == str), "only int(v|string) or int(string,int) expected"
    if s_base is not None:
        args_s = [s_obj, s_base]
    else:
        args_s = [s_obj]
    return constpropagate(int, args_s, SomeInteger())

def restricted_uint(s_obj):    # for r_uint
    return constpropagate(pypy.rpython.rarithmetic.r_uint, [s_obj],
                          SomeInteger(nonneg=True, unsigned=True))

def builtin_float(s_obj):
    return constpropagate(float, [s_obj], SomeFloat())

def builtin_long(s_obj):
    return SomeObject()   # XXX go away

def builtin_chr(s_int):
    return constpropagate(chr, [s_int], SomeChar())

def builtin_unichr(s_int):
    return constpropagate(unichr, [s_int], SomeUnicodeCodePoint())

##def builtin_unicode(s_obj):
##    raise TypeError, "unicode() calls should not happen at interp-level"

def our_issubclass(cls1, cls2):
    """ we're going to try to be less silly in the face of old-style classes"""
    return cls2 is object or issubclass(cls1, cls2)

def builtin_isinstance(s_obj, s_type, variables=None):
    r = SomeBool() 
    if s_type.is_constant():
        typ = s_type.const
        if typ == pypy.rpython.rarithmetic.r_uint:
            if s_obj.is_constant():
                r.const = isinstance(s_obj.const, typ)
            else:
                if s_obj.knowntype == int:
                    r.const = s_obj.unsigned
        else:
            if typ == long:
                getbookkeeper().warning("isinstance(., long) is not RPython")
                if s_obj.is_constant():
                    r.const = isinstance(s_obj.const, long)
                else:
                    if type(s_obj) is not SomeObject: # only SomeObjects could be longs
                        # type(s_obj) < SomeObject -> SomeBool(False)
                        # type(s_obj) == SomeObject -> SomeBool()
                        r.const = False
                return r
                
            assert not issubclass(typ, (int,long)) or typ in (bool, int), (
                "for integers only isinstance(.,int|r_uint) are supported")
            if s_obj.is_constant():
                r.const = isinstance(s_obj.const, typ)
            elif our_issubclass(s_obj.knowntype, typ) and not s_obj.can_be_none():
                r.const = True 
            elif not our_issubclass(typ, s_obj.knowntype): 
                r.const = False 
        # XXX HACK HACK HACK
        # XXX HACK HACK HACK
        # XXX HACK HACK HACK
        bk = getbookkeeper()
        if variables is None:
            fn, block, i = bk.position_key
            op = block.operations[i]
            assert op.opname == "simple_call" 
            assert len(op.args) == 3
            assert op.args[0] == Constant(isinstance)
            variables = [op.args[1]]
        for variable in variables:
            assert bk.annotator.binding(variable) == s_obj
        r.knowntypedata = {}
        add_knowntypedata(r.knowntypedata, True, variables, bk.valueoftype(typ))
    return r

def builtin_hasattr(s_obj, s_attr):
    if not s_attr.is_constant() or not isinstance(s_attr.const, str):
        getbookkeeper().warning('hasattr(%r, %r) is not RPythonic enough' %
                                (s_obj, s_attr))
    r = SomeBool()
    if s_obj.is_constant():
        r.const = hasattr(s_obj.const, s_attr.const)
    return r

##def builtin_callable(s_obj):
##    return SomeBool()

def builtin_tuple(s_iterable):
    if isinstance(s_iterable, SomeTuple):
        return s_iterable
    return SomeObject()

def builtin_list(s_iterable):
    s_iter = s_iterable.iter()
    return getbookkeeper().newlist(s_iter.next())

def builtin_zip(s_iterable1, s_iterable2):
    s_iter1 = s_iterable1.iter()
    s_iter2 = s_iterable2.iter()
    s_tup = SomeTuple((s_iter1.next(),s_iter2.next()))
    return getbookkeeper().newlist(s_tup)

def builtin_min(*s_values):
    if len(s_values) == 1: # xxx do we support this?
        s_iter = s_values[0].iter()
        return s_iter.next()
    else:
        return unionof(*s_values)

builtin_max = builtin_min

def builtin_apply(*stuff):
    getbookkeeper().warning("ignoring apply%r" % (stuff,))
    return SomeObject()

##def builtin_compile(*stuff):
##    s = SomeObject()
##    s.knowntype = types.CodeType
##    return s

def builtin_slice(*args):
    bk = getbookkeeper()
    if len(args) == 1:
        return SomeSlice(
            bk.immutablevalue(None), args[0], bk.immutablevalue(None))
    elif len(args) == 2:
        return SomeSlice(
            args[0], args[1], bk.immutablevalue(None))
    elif len(args) == 3:
        return SomeSlice(
            args[0], args[1], args[2])
    else:
        raise Exception, "bogus call to slice()"
        

def exception_init(s_self, *args):
    pass   # XXX check correctness of args, maybe

def count(s_obj):
    return SomeInteger()

def conf():
    return SomeString()

def math_fmod(x, y):
    return SomeFloat()

def math_floor(x):
    return SomeFloat()

def math_any(*args):
    return SomeFloat()

def rarith_intmask(s_obj):
    return SomeInteger()

##def rarith_ovfcheck(s_obj):
##    if isinstance(s_obj, SomeInteger) and s_obj.unsigned:
##        getbookkeeper().warning("ovfcheck on unsigned")
##    return s_obj

##def rarith_ovfcheck_lshift(s_obj1, s_obj2):
##    if isinstance(s_obj1, SomeInteger) and s_obj1.unsigned:
##        getbookkeeper().warning("ovfcheck_lshift with unsigned")
##    return SomeInteger()

def unicodedata_decimal(s_uchr):
    raise TypeError, "unicodedate.decimal() calls should not happen at interp-level"    

def test(*args):
    return SomeBool()

def pathpart(*args):
    return SomeString()

def time_func():
    return SomeFloat()

def import_func(*args):
    return SomeObject()

# collect all functions
import __builtin__
BUILTIN_ANALYZERS = {}
for name, value in globals().items():
    if name.startswith('builtin_'):
        original = getattr(__builtin__, name[8:])
        BUILTIN_ANALYZERS[original] = value

BUILTIN_ANALYZERS[pypy.rpython.rarithmetic.r_uint] = restricted_uint
##BUILTIN_ANALYZERS[pypy.rpython.rarithmetic.ovfcheck] = rarith_ovfcheck
##BUILTIN_ANALYZERS[pypy.rpython.rarithmetic.ovfcheck_lshift] = rarith_ovfcheck_lshift
BUILTIN_ANALYZERS[pypy.rpython.rarithmetic.intmask] = rarith_intmask

BUILTIN_ANALYZERS[Exception.__init__.im_func] = exception_init
BUILTIN_ANALYZERS[OSError.__init__.im_func] = exception_init
# this one is needed otherwise when annotating assert in a test we may try to annotate 
# py.test AssertionError.__init__ .
BUILTIN_ANALYZERS[AssertionError.__init__.im_func] = exception_init
BUILTIN_ANALYZERS[math.fmod] = math_fmod
BUILTIN_ANALYZERS[math.floor] = math_floor
BUILTIN_ANALYZERS[math.exp] = math_any
BUILTIN_ANALYZERS[math.ldexp] = math_any
BUILTIN_ANALYZERS[math.frexp] = math_any
BUILTIN_ANALYZERS[sys.getrefcount] = count
BUILTIN_ANALYZERS[sys.getdefaultencoding] = conf
import unicodedata
BUILTIN_ANALYZERS[unicodedata.decimal] = unicodedata_decimal # xxx

# os.path stuff
#BUILTIN_ANALYZERS[os.path.dirname] = pathpart
#BUILTIN_ANALYZERS[os.path.normpath] = pathpart
#BUILTIN_ANALYZERS[os.path.join] = pathpart
BUILTIN_ANALYZERS[os.path.exists] = test
BUILTIN_ANALYZERS[os.path.isdir] = test

# time stuff
BUILTIN_ANALYZERS[time.time] = time_func
BUILTIN_ANALYZERS[time.clock] = time_func

# import
BUILTIN_ANALYZERS[__import__] = import_func

# annotation of low-level types
from pypy.annotation.model import SomePtr
from pypy.rpython import lltype

def malloc(T, n=None):
    assert n is None or n.knowntype == int
    assert T.is_constant()
    if n is not None:
        n = 1
    p = lltype.malloc(T.const, n)
    r = SomePtr(lltype.typeOf(p))
    #print "MALLOC", r
    return r

def typeOf(s_val):
    lltype = annotation_to_lltype(s_val, info="in typeOf(): ")
    return immutablevalue(lltype)

def nullptr(T):
    assert T.is_constant()
    p = lltype.nullptr(T.const)
    return immutablevalue(p)

def cast_pointer(PtrT, s_p):
    assert isinstance(s_p, SomePtr), "casting of non-pointer: %r" % s_p
    assert PtrT.is_constant()
    cast_p = lltype.cast_pointer(PtrT.const, s_p.ll_ptrtype._defl())
    return SomePtr(ll_ptrtype=lltype.typeOf(cast_p))

def getRuntimeTypeInfo(T):
    assert T.is_constant()
    return immutablevalue(lltype.getRuntimeTypeInfo(T.const))

def runtime_type_info(s_p):
    assert isinstance(s_p, SomePtr), "runtime_type_info of non-pointer: %r" % s_p
    return SomePtr(lltype.typeOf(lltype.runtime_type_info(s_p.ll_ptrtype._example())))

BUILTIN_ANALYZERS[lltype.malloc] = malloc
BUILTIN_ANALYZERS[lltype.typeOf] = typeOf
BUILTIN_ANALYZERS[lltype.nullptr] = nullptr
BUILTIN_ANALYZERS[lltype.cast_pointer] = cast_pointer
BUILTIN_ANALYZERS[lltype.getRuntimeTypeInfo] = getRuntimeTypeInfo
BUILTIN_ANALYZERS[lltype.runtime_type_info] = runtime_type_info

from pypy.rpython import extfunctable

# import annotation information for external functions 
# from the extfunctable.table  into our own annotation specific table 
for func, extfuncinfo in extfunctable.table.iteritems():
    BUILTIN_ANALYZERS[func] = extfuncinfo.annotation 
