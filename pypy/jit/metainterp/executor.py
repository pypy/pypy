"""This implements pyjitpl's execution of operations.
"""

import py
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rlib.rarithmetic import ovfcheck, r_uint, intmask
from pypy.jit.metainterp.history import BoxInt, BoxPtr, ConstInt, check_descr
from pypy.jit.metainterp.history import INT, REF, ConstFloat
from pypy.jit.metainterp import resoperation
from pypy.jit.metainterp.resoperation import rop


# Operations in the _ALWAYS_PURE part of the table of resoperation.py
# must return a ConstInt or ConstPtr.  Other operations must return
# a BoxInt or BoxPtr or None.

# ____________________________________________________________

def do_int_add(cpu, box1, box2):
    return ConstInt(intmask(box1.getint() + box2.getint()))

def do_int_sub(cpu, box1, box2):
    return ConstInt(intmask(box1.getint() - box2.getint()))

def do_int_mul(cpu, box1, box2):
    return ConstInt(intmask(box1.getint() * box2.getint()))

def do_int_floordiv(cpu, box1, box2):
    z = llop.int_floordiv(lltype.Signed, box1.getint(), box2.getint())
    return ConstInt(z)

def do_int_mod(cpu, box1, box2):
    z = llop.int_mod(lltype.Signed, box1.getint(), box2.getint())
    return ConstInt(z)

def do_int_and(cpu, box1, box2):
    return ConstInt(box1.getint() & box2.getint())

def do_int_or(cpu, box1, box2):
    return ConstInt(box1.getint() | box2.getint())

def do_int_xor(cpu, box1, box2):
    return ConstInt(box1.getint() ^ box2.getint())

def do_int_rshift(cpu, box1, box2):
    return ConstInt(box1.getint() >> box2.getint())

def do_int_lshift(cpu, box1, box2):
    return ConstInt(intmask(box1.getint() << box2.getint()))

def do_uint_rshift(cpu, box1, box2):
    v = r_uint(box1.getint()) >> r_uint(box2.getint())
    return ConstInt(intmask(v))

# ----------

def do_int_lt(cpu, box1, box2):
    return ConstInt(box1.getint() < box2.getint())

def do_int_le(cpu, box1, box2):
    return ConstInt(box1.getint() <= box2.getint())

def do_int_eq(cpu, box1, box2):
    return ConstInt(box1.getint() == box2.getint())

def do_int_ne(cpu, box1, box2):
    return ConstInt(box1.getint() != box2.getint())

def do_int_gt(cpu, box1, box2):
    return ConstInt(box1.getint() > box2.getint())

def do_int_ge(cpu, box1, box2):
    return ConstInt(box1.getint() >= box2.getint())

def do_uint_lt(cpu, box1, box2):
    return ConstInt(r_uint(box1.getint()) < r_uint(box2.getint()))

def do_uint_le(cpu, box1, box2):
    return ConstInt(r_uint(box1.getint()) <= r_uint(box2.getint()))

def do_uint_gt(cpu, box1, box2):
    return ConstInt(r_uint(box1.getint()) > r_uint(box2.getint()))

def do_uint_ge(cpu, box1, box2):
    return ConstInt(r_uint(box1.getint()) >= r_uint(box2.getint()))

# ----------

def do_int_is_true(cpu, box1):
    return ConstInt(bool(box1.getint()))

def do_int_neg(cpu, box1):
    return ConstInt(intmask(-box1.getint()))

def do_int_invert(cpu, box1):
    return ConstInt(~box1.getint())

def do_bool_not(cpu, box1):
    return ConstInt(not box1.getint())

def do_same_as(cpu, box1):
    return box1

def do_oois(cpu, box1, box2):
    tp = box1.type
    assert tp == box2.type
    if tp == INT:
        x = box1.getint() == box2.getint()
    elif tp == REF:
        x = box1.getref_base() == box2.getref_base()
    else:
        assert False
    return ConstInt(x)

def do_ooisnot(cpu, box1, box2):
    tp = box1.type
    assert tp == box2.type
    if tp == INT:
        x = box1.getint() != box2.getint()
    elif tp == REF:
        x = box1.getref_base() != box2.getref_base()
    else:
        assert False
    return ConstInt(x)

def do_subclassof(cpu, box1, box2):
    return ConstInt(cpu.ts.subclassOf(cpu, box1, box2))

# ----------

def do_int_add_ovf(cpu, box1, box2):
    x = box1.getint()
    y = box2.getint()
    try:
        z = ovfcheck(x + y)
    except OverflowError:
        ovf = True
        z = 0
    else:
        ovf = False
    cpu._overflow_flag = ovf
    return BoxInt(z)

def do_int_sub_ovf(cpu, box1, box2):
    x = box1.getint()
    y = box2.getint()
    try:
        z = ovfcheck(x - y)
    except OverflowError:
        ovf = True
        z = 0
    else:
        ovf = False
    cpu._overflow_flag = ovf
    return BoxInt(z)

def do_int_mul_ovf(cpu, box1, box2):
    x = box1.getint()
    y = box2.getint()
    try:
        z = ovfcheck(x * y)
    except OverflowError:
        ovf = True
        z = 0
    else:
        ovf = False
    cpu._overflow_flag = ovf
    return BoxInt(z)

# ----------

def do_float_neg(cpu, box1):
    return ConstFloat(-box1.getfloat())

def do_float_abs(cpu, box1):
    return ConstFloat(abs(box1.getfloat()))

def do_float_is_true(cpu, box1):
    return ConstInt(bool(box1.getfloat()))

def do_float_add(cpu, box1, box2):
    return ConstFloat(box1.getfloat() + box2.getfloat())

def do_float_sub(cpu, box1, box2):
    return ConstFloat(box1.getfloat() - box2.getfloat())

def do_float_mul(cpu, box1, box2):
    return ConstFloat(box1.getfloat() * box2.getfloat())

def do_float_truediv(cpu, box1, box2):
    return ConstFloat(box1.getfloat() / box2.getfloat())

def do_float_lt(cpu, box1, box2):
    return ConstInt(box1.getfloat() < box2.getfloat())

def do_float_le(cpu, box1, box2):
    return ConstInt(box1.getfloat() <= box2.getfloat())

def do_float_eq(cpu, box1, box2):
    return ConstInt(box1.getfloat() == box2.getfloat())

def do_float_ne(cpu, box1, box2):
    return ConstInt(box1.getfloat() != box2.getfloat())

def do_float_gt(cpu, box1, box2):
    return ConstInt(box1.getfloat() > box2.getfloat())

def do_float_ge(cpu, box1, box2):
    return ConstInt(box1.getfloat() >= box2.getfloat())

def do_cast_float_to_int(cpu, box1):
    # note: we need to call int() twice to care for the fact that
    # int(-2147483648.0) returns a long :-(
    return ConstInt(int(int(box1.getfloat())))

def do_cast_int_to_float(cpu, box1):
    return ConstFloat(float(box1.getint()))

# ____________________________________________________________

def do_force_token(cpu):
    raise NotImplementedError

def do_virtual_ref(cpu, box1, box2):
    raise NotImplementedError

def do_virtual_ref_finish(cpu, box1, box2):
    raise NotImplementedError

def do_debug_merge_point(cpu, box1):
    from pypy.jit.metainterp.warmspot import get_stats
    loc = box1._get_str()
    get_stats().add_merge_point_location(loc)

# ____________________________________________________________


def make_execute_list(cpuclass):
    from pypy.jit.backend.model import AbstractCPU
    if 0:     # enable this to trace calls to do_xxx
        def wrap(fn):
            def myfn(*args):
                print '<<<', fn.__name__
                try:
                    return fn(*args)
                finally:
                    print fn.__name__, '>>>'
            return myfn
    else:
        def wrap(fn):
            return fn
    #
    execute_by_num_args = {}
    for key, value in rop.__dict__.items():
        if not key.startswith('_'):
            if (rop._FINAL_FIRST <= value <= rop._FINAL_LAST or
                rop._GUARD_FIRST <= value <= rop._GUARD_LAST):
                continue
            # find which list to store the operation in, based on num_args
            num_args = resoperation.oparity[value]
            withdescr = resoperation.opwithdescr[value]
            if withdescr and num_args >= 0:
                num_args += 1
            if num_args not in execute_by_num_args:
                execute_by_num_args[num_args] = [None] * (rop._LAST+1)
            execute = execute_by_num_args[num_args]
            #
            if execute[value] is not None:
                raise Exception("duplicate entry for op number %d" % value)
            if key.endswith('_PURE'):
                key = key[:-5]
            name = 'do_' + key.lower()
            if hasattr(cpuclass, name):
                execute[value] = wrap(getattr(cpuclass, name))
            elif name in globals():
                execute[value] = wrap(globals()[name])
            else:
                assert hasattr(AbstractCPU, name), name
    cpuclass._execute_by_num_args = execute_by_num_args


def get_execute_funclist(cpu, num_args):
    # workaround, similar to the next one
    return cpu._execute_by_num_args[num_args]
get_execute_funclist._annspecialcase_ = 'specialize:memo'

def get_execute_function(cpu, opnum, num_args):
    # workaround for an annotation limitation: putting this code in
    # a specialize:memo function makes sure the following line is
    # constant-folded away.  Only works if opnum and num_args are
    # constants, of course.
    return cpu._execute_by_num_args[num_args][opnum]
get_execute_function._annspecialcase_ = 'specialize:memo'

def has_descr(opnum):
    # workaround, similar to the previous one
    return resoperation.opwithdescr[opnum]
has_descr._annspecialcase_ = 'specialize:memo'


def execute(cpu, opnum, descr, *argboxes):
    # only for opnums with a fixed arity
    if has_descr(opnum):
        check_descr(descr)
        argboxes = argboxes + (descr,)
    else:
        assert descr is None
    func = get_execute_function(cpu, opnum, len(argboxes))
    assert func is not None
    return func(cpu, *argboxes)
execute._annspecialcase_ = 'specialize:arg(1)'

def execute_varargs(cpu, opnum, argboxes, descr):
    # only for opnums with a variable arity (calls, typically)
    check_descr(descr)
    func = get_execute_function(cpu, opnum, -1)
    assert func is not None
    return func(cpu, argboxes, descr)
execute_varargs._annspecialcase_ = 'specialize:arg(1)'


def execute_nonspec(cpu, opnum, argboxes, descr=None):
    arity = resoperation.oparity[opnum]
    assert arity == -1 or len(argboxes) == arity
    if resoperation.opwithdescr[opnum]:
        check_descr(descr)
        if arity == -1:
            func = get_execute_funclist(cpu, -1)[opnum]
            return func(cpu, argboxes, descr)
        if arity == 0:
            func = get_execute_funclist(cpu, 1)[opnum]
            return func(cpu, descr)
        if arity == 1:
            func = get_execute_funclist(cpu, 2)[opnum]
            return func(cpu, argboxes[0], descr)
        if arity == 2:
            func = get_execute_funclist(cpu, 3)[opnum]
            return func(cpu, argboxes[0], argboxes[1], descr)
        if arity == 3:
            func = get_execute_funclist(cpu, 4)[opnum]
            return func(cpu, argboxes[0], argboxes[1], argboxes[2], descr)
    else:
        assert descr is None
        if arity == 1:
            func = get_execute_funclist(cpu, 1)[opnum]
            return func(cpu, argboxes[0])
        if arity == 2:
            func = get_execute_funclist(cpu, 2)[opnum]
            return func(cpu, argboxes[0], argboxes[1])
        if arity == 3:
            func = get_execute_funclist(cpu, 3)[opnum]
            return func(cpu, argboxes[0], argboxes[1], argboxes[2])
    raise NotImplementedError
