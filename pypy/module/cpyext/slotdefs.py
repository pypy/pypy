from __future__ import with_statement

import re

from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rlib.rarithmetic import widen
from rpython.rlib import rgc # Force registration of gc.collect
from pypy.module.cpyext.api import (
    slot_function, generic_cpy_call, PyObject, Py_ssize_t,
    pypy_decl, Py_buffer, Py_bufferP, PyTypeObjectPtr)
from pypy.module.cpyext.typeobjectdefs import (
    unaryfunc, ternaryfunc, binaryfunc,
    getattrfunc, getattrofunc, setattrofunc, lenfunc, ssizeargfunc, inquiry,
    ssizessizeargfunc, ssizeobjargproc, iternextfunc, initproc, richcmpfunc,
    cmpfunc, hashfunc, descrgetfunc, descrsetfunc, objobjproc, objobjargproc,
    getbufferproc, releasebufferproc, ssizessizeobjargproc)
from pypy.module.cpyext.pyobject import make_ref, decref
from pypy.module.cpyext.pyerrors import PyErr_Occurred
from pypy.module.cpyext.memoryobject import fill_Py_buffer
from pypy.module.cpyext.state import State
from pypy.module.cpyext import userslot
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.argument import Arguments
from rpython.rlib.buffer import Buffer
from rpython.rlib.unroll import unrolling_iterable
from rpython.rlib.objectmodel import specialize, not_rpython
from rpython.tool.sourcetools import func_renamer
from rpython.flowspace.model import Constant
from rpython.flowspace.specialcase import register_flow_sc
from rpython.rtyper.annlowlevel import llhelper
from pypy.module.sys.version import CPYTHON_VERSION

PY3 = CPYTHON_VERSION[0] == 3

# XXX: Also defined in object.h
Py_LT = 0
Py_LE = 1
Py_EQ = 2
Py_NE = 3
Py_GT = 4
Py_GE = 5


def check_num_args(space, w_ob, n):
    from pypy.module.cpyext.tupleobject import PyTuple_CheckExact
    if not PyTuple_CheckExact(space, w_ob):
        raise oefmt(space.w_SystemError,
                    "PyArg_UnpackTuple() argument list is not a tuple")
    if n == space.len_w(w_ob):
        return
    raise oefmt(space.w_TypeError,
                "expected %d arguments, got %d",
                n, space.len_w(w_ob))

def check_num_argsv(space, w_ob, low, high):
    from pypy.module.cpyext.tupleobject import PyTuple_CheckExact
    if not PyTuple_CheckExact(space, w_ob):
        raise oefmt(space.w_SystemError,
                    "PyArg_UnpackTuple() argument list is not a tuple")
    if low <=space.len_w(w_ob) <= high:
        return
    raise oefmt(space.w_TypeError,
                "expected %d-%d arguments, got %d",
                low, high, space.len_w(w_ob))

@not_rpython
def llslot(space, func):
    return func.api_func.get_llhelper(space)

@register_flow_sc(llslot)
def sc_llslot(ctx, v_space, v_func):
    assert isinstance(v_func, Constant)
    get_llhelper = v_func.value.api_func.get_llhelper
    return ctx.appcall(get_llhelper, v_space)


def wrap_init(space, w_self, w_args, func, w_kwargs):
    func_init = rffi.cast(initproc, func)
    res = generic_cpy_call(space, func_init, w_self, w_args, w_kwargs)
    if rffi.cast(lltype.Signed, res) == -1:
        space.fromcache(State).check_and_raise_exception(always=True)
    return None

def wrap_unaryfunc(space, w_self, w_args, func):
    func_unary = rffi.cast(unaryfunc, func)
    check_num_args(space, w_args, 0)
    return generic_cpy_call(space, func_unary, w_self)

def wrap_binaryfunc(space, w_self, w_args, func):
    func_binary = rffi.cast(binaryfunc, func)
    check_num_args(space, w_args, 1)
    args_w = space.fixedview(w_args)
    return generic_cpy_call(space, func_binary, w_self, args_w[0])

def wrap_binaryfunc_l(space, w_self, w_args, func):
    func_binary = rffi.cast(binaryfunc, func)
    check_num_args(space, w_args, 1)
    args_w = space.fixedview(w_args)
    ref = make_ref(space, w_self)
    decref(space, ref)
    return generic_cpy_call(space, func_binary, w_self, args_w[0])

def wrap_binaryfunc_r(space, w_self, w_args, func):
    func_binary = rffi.cast(binaryfunc, func)
    check_num_args(space, w_args, 1)
    args_w = space.fixedview(w_args)
    ref = make_ref(space, w_self)
    decref(space, ref)
    return generic_cpy_call(space, func_binary, args_w[0], w_self)

def wrap_ternaryfunc(space, w_self, w_args, func):
    # The third argument is optional
    func_ternary = rffi.cast(ternaryfunc, func)
    check_num_argsv(space, w_args, 1, 2)
    args_w = space.fixedview(w_args)
    arg3 = space.w_None
    if len(args_w) > 1:
        arg3 = args_w[1]
    return generic_cpy_call(space, func_ternary, w_self, args_w[0], arg3)

def wrap_ternaryfunc_r(space, w_self, w_args, func):
    # The third argument is optional
    func_ternary = rffi.cast(ternaryfunc, func)
    check_num_argsv(space, w_args, 1, 2)
    args_w = space.fixedview(w_args)
    ref = make_ref(space, w_self)
    decref(space, ref)
    arg3 = space.w_None
    if len(args_w) > 1:
        arg3 = args_w[1]
    return generic_cpy_call(space, func_ternary, args_w[0], w_self, arg3)


def wrap_inquirypred(space, w_self, w_args, func):
    func_inquiry = rffi.cast(inquiry, func)
    check_num_args(space, w_args, 0)
    args_w = space.fixedview(w_args)
    res = generic_cpy_call(space, func_inquiry, w_self)
    res = rffi.cast(lltype.Signed, res)
    if res == -1:
        space.fromcache(State).check_and_raise_exception(always=True)
    return space.wrap(bool(res))

def wrap_getattr(space, w_self, w_args, func):
    func_target = rffi.cast(getattrfunc, func)
    check_num_args(space, w_args, 1)
    args_w = space.fixedview(w_args)
    name_ptr = rffi.str2charp(space.str_w(args_w[0]))
    try:
        return generic_cpy_call(space, func_target, w_self, name_ptr)
    finally:
        rffi.free_charp(name_ptr)

def wrap_getattro(space, w_self, w_args, func):
    func_target = rffi.cast(getattrofunc, func)
    check_num_args(space, w_args, 1)
    args_w = space.fixedview(w_args)
    return generic_cpy_call(space, func_target, w_self, args_w[0])

def wrap_setattr(space, w_self, w_args, func):
    func_target = rffi.cast(setattrofunc, func)
    check_num_args(space, w_args, 2)
    w_name, w_value = space.fixedview(w_args)
    # XXX "Carlo Verre hack"?
    res = generic_cpy_call(space, func_target, w_self, w_name, w_value)
    if rffi.cast(lltype.Signed, res) == -1:
        space.fromcache(State).check_and_raise_exception(always=True)

def wrap_delattr(space, w_self, w_args, func):
    func_target = rffi.cast(setattrofunc, func)
    check_num_args(space, w_args, 1)
    w_name, = space.fixedview(w_args)
    # XXX "Carlo Verre hack"?
    res = generic_cpy_call(space, func_target, w_self, w_name, None)
    if rffi.cast(lltype.Signed, res) == -1:
        space.fromcache(State).check_and_raise_exception(always=True)

def wrap_descr_get(space, w_self, w_args, func):
    func_target = rffi.cast(descrgetfunc, func)
    args_w = space.fixedview(w_args)
    if len(args_w) == 1:
        w_obj, = args_w
        w_type = None
    elif len(args_w) == 2:
        w_obj, w_type = args_w
    else:
        raise oefmt(space.w_TypeError,
                    "expected 1 or 2 arguments, got %d", len(args_w))
    if w_obj is space.w_None:
        w_obj = None
    if w_type is space.w_None:
        w_type = None
    if w_obj is None and w_type is None:
        raise oefmt(space.w_TypeError, "__get__(None, None) is invalid")
    return generic_cpy_call(space, func_target, w_self, w_obj, w_type)

def wrap_descr_set(space, w_self, w_args, func):
    func_target = rffi.cast(descrsetfunc, func)
    check_num_args(space, w_args, 2)
    w_obj, w_value = space.fixedview(w_args)
    res = generic_cpy_call(space, func_target, w_self, w_obj, w_value)
    if rffi.cast(lltype.Signed, res) == -1:
        space.fromcache(State).check_and_raise_exception(always=True)

def wrap_descr_delete(space, w_self, w_args, func):
    func_target = rffi.cast(descrsetfunc, func)
    check_num_args(space, w_args, 1)
    w_obj, = space.fixedview(w_args)
    res = generic_cpy_call(space, func_target, w_self, w_obj, None)
    if rffi.cast(lltype.Signed, res) == -1:
        space.fromcache(State).check_and_raise_exception(always=True)

def wrap_call(space, w_self, w_args, func, w_kwds):
    func_target = rffi.cast(ternaryfunc, func)
    return generic_cpy_call(space, func_target, w_self, w_args, w_kwds)

def wrap_ssizessizeobjargproc(space, w_self, w_args, func):
    func_target = rffi.cast(ssizessizeobjargproc, func)
    check_num_args(space, w_args, 3)
    args_w = space.fixedview(w_args)
    i = space.int_w(space.index(args_w[0]))
    j = space.int_w(space.index(args_w[1]))
    w_y = args_w[2]
    res = generic_cpy_call(space, func_target, w_self, i, j, w_y)
    if rffi.cast(lltype.Signed, res) == -1:
        space.fromcache(State).check_and_raise_exception(always=True)

def wrap_lenfunc(space, w_self, w_args, func):
    func_len = rffi.cast(lenfunc, func)
    check_num_args(space, w_args, 0)
    return space.wrap(generic_cpy_call(space, func_len, w_self))

def wrap_sq_item(space, w_self, w_args, func):
    func_target = rffi.cast(ssizeargfunc, func)
    check_num_args(space, w_args, 1)
    args_w = space.fixedview(w_args)
    index = space.int_w(space.index(args_w[0]))
    return generic_cpy_call(space, func_target, w_self, index)

def wrap_sq_setitem(space, w_self, w_args, func):
    func_target = rffi.cast(ssizeobjargproc, func)
    check_num_args(space, w_args, 2)
    args_w = space.fixedview(w_args)
    index = space.int_w(space.index(args_w[0]))
    res = generic_cpy_call(space, func_target, w_self, index, args_w[1])
    if rffi.cast(lltype.Signed, res) == -1:
        space.fromcache(State).check_and_raise_exception(always=True)

def wrap_sq_delitem(space, w_self, w_args, func):
    func_target = rffi.cast(ssizeobjargproc, func)
    check_num_args(space, w_args, 1)
    args_w = space.fixedview(w_args)
    index = space.int_w(space.index(args_w[0]))
    null = lltype.nullptr(PyObject.TO)
    res = generic_cpy_call(space, func_target, w_self, index, null)
    if rffi.cast(lltype.Signed, res) == -1:
        space.fromcache(State).check_and_raise_exception(always=True)

# Warning, confusing function name (like CPython).  Used only for sq_contains.
def wrap_objobjproc(space, w_self, w_args, func):
    func_target = rffi.cast(objobjproc, func)
    check_num_args(space, w_args, 1)
    w_value, = space.fixedview(w_args)
    res = generic_cpy_call(space, func_target, w_self, w_value)
    res = rffi.cast(lltype.Signed, res)
    if res == -1:
        space.fromcache(State).check_and_raise_exception(always=True)
    return space.wrap(bool(res))

def wrap_objobjargproc(space, w_self, w_args, func):
    func_target = rffi.cast(objobjargproc, func)
    check_num_args(space, w_args, 2)
    w_key, w_value = space.fixedview(w_args)
    res = generic_cpy_call(space, func_target, w_self, w_key, w_value)
    if rffi.cast(lltype.Signed, res) == -1:
        space.fromcache(State).check_and_raise_exception(always=True)
    return space.w_None

def wrap_delitem(space, w_self, w_args, func):
    func_target = rffi.cast(objobjargproc, func)
    check_num_args(space, w_args, 1)
    w_key, = space.fixedview(w_args)
    res = generic_cpy_call(space, func_target, w_self, w_key, None)
    if rffi.cast(lltype.Signed, res) == -1:
        space.fromcache(State).check_and_raise_exception(always=True)
    return space.w_None

def wrap_ssizessizeargfunc(space, w_self, w_args, func):
    func_target = rffi.cast(ssizessizeargfunc, func)
    check_num_args(space, w_args, 2)
    args_w = space.fixedview(w_args)
    start = space.int_w(args_w[0])
    end = space.int_w(args_w[1])
    return generic_cpy_call(space, func_target, w_self, start, end)

def wrap_next(space, w_self, w_args, func):
    from pypy.module.cpyext.api import generic_cpy_call_expect_null
    func_target = rffi.cast(iternextfunc, func)
    check_num_args(space, w_args, 0)
    w_res = generic_cpy_call_expect_null(space, func_target, w_self)
    if not w_res and not PyErr_Occurred(space):
        raise OperationError(space.w_StopIteration, space.w_None)
    return w_res

def wrap_hashfunc(space, w_self, w_args, func):
    func_target = rffi.cast(hashfunc, func)
    check_num_args(space, w_args, 0)
    res = generic_cpy_call(space, func_target, w_self)
    if res == -1:
        space.fromcache(State).check_and_raise_exception(always=True)
    return space.wrap(res)

class CPyBuffer(Buffer):
    # Similar to Py_buffer
    _immutable_ = True

    def __init__(self, space, ptr, size, w_obj, format='B', shape=None,
                strides=None, ndim=1, itemsize=1, readonly=True,
                releasebufferproc=rffi.cast(rffi.VOIDP, 0)):
        self.space = space
        self.ptr = ptr
        self.size = size
        self.w_obj = w_obj # kept alive
        self.pyobj = make_ref(space, w_obj)
        self.format = format
        if not shape:
            self.shape = [size]
        else:
            self.shape = shape
        if not strides:
            self.strides = [1]
        else:
            self.strides = strides
        self.ndim = ndim
        self.itemsize = itemsize
        self.readonly = readonly
        self.releasebufferproc = releasebufferproc

    def releasebuffer(self):
        if self.pyobj:
            decref(self.space, self.pyobj)
            self.pyobj = lltype.nullptr(PyObject.TO)
        else:
            #do not call twice
            return
        if self.releasebufferproc:
            func_target = rffi.cast(releasebufferproc, self.releasebufferproc)
            with lltype.scoped_alloc(Py_buffer) as pybuf:
                pybuf.c_buf = self.ptr
                pybuf.c_len = self.size
                pybuf.c_ndim = rffi.cast(rffi.INT_real, self.ndim)
                for i in range(self.ndim):
                    pybuf.c_shape[i] = self.shape[i]
                    pybuf.c_strides[i] = self.strides[i]
                if self.format:
                    pybuf.c_format = rffi.str2charp(self.format)
                else:
                    pybuf.c_format = rffi.str2charp("B")
                generic_cpy_call(self.space, func_target, self.pyobj, pybuf)
            self.releasebufferproc = rffi.cast(rffi.VOIDP, 0)

    def getlength(self):
        return self.size

    def getitem(self, index):
        return self.ptr[index]

    def get_raw_address(self):
        return rffi.cast(rffi.CCHARP, self.ptr)

    def getformat(self):
        return self.format

    def getshape(self):
        return self.shape

    def getstrides(self):
        return self.strides

    def getitemsize(self):
        return self.itemsize

    def getndim(self):
        return self.ndim

    def setitem(self, index, char):
        # absolutely no safety checks, what could go wrong?
        self.ptr[index] = char

class FQ(rgc.FinalizerQueue):
    Class = CPyBuffer
    def finalizer_trigger(self):
        while 1:
            buf  = self.next_dead()
            if not buf:
                break
            buf.releasebuffer()

fq = FQ()

def wrap_getreadbuffer(space, w_self, w_args, func):
    func_target = rffi.cast(readbufferproc, func)
    py_obj = make_ref(space, w_self)
    py_type = py_obj.c_ob_type
    rbp = rffi.cast(rffi.VOIDP, 0)
    if py_type.c_tp_as_buffer:
        rbp = rffi.cast(rffi.VOIDP, py_type.c_tp_as_buffer.c_bf_releasebuffer)
    decref(space, py_obj)
    with lltype.scoped_alloc(rffi.VOIDPP.TO, 1) as ptr:
        index = rffi.cast(Py_ssize_t, 0)
        size = generic_cpy_call(space, func_target, w_self, index, ptr)
        if size < 0:
            space.fromcache(State).check_and_raise_exception(always=True)
        buf = CPyBuffer(space, ptr[0], size, w_self,
                               releasebufferproc=rbp)
        fq.register_finalizer(buf)
        return space.newbuffer(buf)

def wrap_getwritebuffer(space, w_self, w_args, func):
    func_target = rffi.cast(readbufferproc, func)
    py_obj = make_ref(space, w_self)
    py_type = py_obj.c_ob_type
    decref(space, py_obj)
    rbp = rffi.cast(rffi.VOIDP, 0)
    if py_type.c_tp_as_buffer:
        rbp = rffi.cast(rffi.VOIDP, py_type.c_tp_as_buffer.c_bf_releasebuffer)
    with lltype.scoped_alloc(rffi.VOIDPP.TO, 1) as ptr:
        index = rffi.cast(Py_ssize_t, 0)
        size = generic_cpy_call(space, func_target, w_self, index, ptr)
        if size < 0:
            space.fromcache(State).check_and_raise_exception(always=True)
        buf = CPyBuffer(space, ptr[0], size, w_self, readonly=False,
                               releasebufferproc=rbp)
        fq.register_finalizer(buf)
        return space.newbuffer(buf)

def wrap_getbuffer(space, w_self, w_args, func):
    func_target = rffi.cast(getbufferproc, func)
    py_obj = make_ref(space, w_self)
    py_type = py_obj.c_ob_type
    rbp = rffi.cast(rffi.VOIDP, 0)
    if py_type.c_tp_as_buffer:
        rbp = rffi.cast(rffi.VOIDP, py_type.c_tp_as_buffer.c_bf_releasebuffer)
    decref(space, py_obj)
    with lltype.scoped_alloc(Py_buffer) as pybuf:
        _flags = 0
        if space.len_w(w_args) > 0:
            _flags = space.int_w(space.listview(w_args)[0])
        flags = rffi.cast(rffi.INT_real,_flags)
        size = generic_cpy_call(space, func_target, w_self, pybuf, flags)
        if widen(size) < 0:
            space.fromcache(State).check_and_raise_exception(always=True)
        ptr = pybuf.c_buf
        size = pybuf.c_len
        ndim = widen(pybuf.c_ndim)
        if pybuf.c_shape:
            shape = [pybuf.c_shape[i] for i in range(ndim)]
        else:
            shape = None
        if pybuf.c_strides:
            strides = [pybuf.c_strides[i] for i in range(ndim)]
        else:
            strides = [1]
        if pybuf.c_format:
            format = rffi.charp2str(pybuf.c_format)
        else:
            format = 'B'
        buf = CPyBuffer(space, ptr, size, w_self, format=format,
                            ndim=ndim, shape=shape, strides=strides,
                            itemsize=pybuf.c_itemsize,
                            readonly=widen(pybuf.c_readonly),
                            releasebufferproc = rbp)
        fq.register_finalizer(buf)
        return space.newbuffer(buf)

def get_richcmp_func(OP_CONST):
    def inner(space, w_self, w_args, func):
        func_target = rffi.cast(richcmpfunc, func)
        check_num_args(space, w_args, 1)
        w_other, = space.fixedview(w_args)
        return generic_cpy_call(space, func_target,
            w_self, w_other, rffi.cast(rffi.INT_real, OP_CONST))
    return inner

richcmp_eq = get_richcmp_func(Py_EQ)
richcmp_ne = get_richcmp_func(Py_NE)
richcmp_lt = get_richcmp_func(Py_LT)
richcmp_le = get_richcmp_func(Py_LE)
richcmp_gt = get_richcmp_func(Py_GT)
richcmp_ge = get_richcmp_func(Py_GE)

def wrap_cmpfunc(space, w_self, w_args, func):
    func_target = rffi.cast(cmpfunc, func)
    check_num_args(space, w_args, 1)
    w_other, = space.fixedview(w_args)

    if not space.issubtype_w(space.type(w_self), space.type(w_other)):
        raise oefmt(space.w_TypeError,
                    "%T.__cmp__(x,y) requires y to be a '%T', not a '%T'",
                    w_self, w_self, w_other)

    return space.wrap(generic_cpy_call(space, func_target, w_self, w_other))

from rpython.rlib.nonconst import NonConstant

SLOTS = {}

@specialize.memo()
def get_slot_tp_function(space, typedef, name):
    """Return a description of the slot C function to use for the built-in
    type for 'typedef'.  The 'name' is the slot name.  This is a memo
    function that, after translation, returns one of a built-in finite set.
    """
    key = (typedef, name)
    try:
        return SLOTS[key]
    except KeyError:
        slot_func = build_slot_tp_function(space, typedef, name)
        api_func = slot_func.api_func if slot_func else None
        SLOTS[key] = api_func
        return api_func

def build_slot_tp_function(space, typedef, name):
    w_type = space.gettypeobject(typedef)

    handled = False
    # unary functions
    for tp_name, attr in [('tp_as_number.c_nb_int', '__int__'),
                          ('tp_as_number.c_nb_long', '__long__'),
                          ('tp_as_number.c_nb_float', '__float__'),
                          ('tp_as_number.c_nb_negative', '__neg__'),
                          ('tp_as_number.c_nb_positive', '__pos__'),
                          ('tp_as_number.c_nb_absolute', '__abs__'),
                          ('tp_as_number.c_nb_invert', '__invert__'),
                          ('tp_as_number.c_nb_index', '__index__'),
                          ('tp_str', '__str__'),
                          ('tp_repr', '__repr__'),
                          ('tp_iter', '__iter__'),
                          ]:
        if name == tp_name:
            slot_fn = w_type.getdictvalue(space, attr)
            if slot_fn is None:
                return

            @slot_function([PyObject], PyObject)
            @func_renamer("cpyext_%s_%s" % (name.replace('.', '_'), typedef.name))
            def slot_func(space, w_self):
                return space.call_function(slot_fn, w_self)
            handled = True

    for tp_name, attr in [('tp_hash', '__hash__'),
                         ]:
        if name == tp_name:
            slot_fn = w_type.getdictvalue(space, attr)
            if slot_fn is None:
                return
            @slot_function([PyObject], lltype.Signed, error=-1)
            @func_renamer("cpyext_%s_%s" % (name.replace('.', '_'), typedef.name))
            def slot_func(space, w_obj):
                return space.int_w(space.call_function(slot_fn, w_obj))
            handled = True


    # binary functions
    for tp_name, attr in [('tp_as_number.c_nb_add', '__add__'),
                          ('tp_as_number.c_nb_subtract', '__sub__'),
                          ('tp_as_number.c_nb_multiply', '__mul__'),
                          ('tp_as_number.c_nb_divide', '__div__'),
                          ('tp_as_number.c_nb_remainder', '__mod__'),
                          ('tp_as_number.c_nb_divmod', '__divmod__'),
                          ('tp_as_number.c_nb_lshift', '__lshift__'),
                          ('tp_as_number.c_nb_rshift', '__rshift__'),
                          ('tp_as_number.c_nb_and', '__and__'),
                          ('tp_as_number.c_nb_xor', '__xor__'),
                          ('tp_as_number.c_nb_or', '__or__'),
                          ('tp_as_sequence.c_sq_concat', '__add__'),
                          ('tp_as_sequence.c_sq_inplace_concat', '__iadd__')
                          ]:
        if name == tp_name:
            slot_fn = w_type.getdictvalue(space, attr)
            if slot_fn is None:
                return

            @slot_function([PyObject, PyObject], PyObject)
            @func_renamer("cpyext_%s_%s" % (name.replace('.', '_'), typedef.name))
            def slot_func(space, w_self, w_arg):
                return space.call_function(slot_fn, w_self, w_arg)
            handled = True

    # binary-with-Py_ssize_t-type
    for tp_name, attr in [('tp_as_sequence.c_sq_item', '__getitem'),
                          ('tp_as_sequence.c_sq_repeat', '__mul__'),
                          ('tp_as_sequence.c_sq_repeat', '__mul__'),
                          ('tp_as_sequence.c_sq_inplace_repeat', '__imul__'),
                          ]:
        if name == tp_name:
            slot_fn = w_type.getdictvalue(space, attr)
            if slot_fn is None:
                return

            @slot_function([PyObject, Py_ssize_t], PyObject)
            @func_renamer("cpyext_%s_%s" % (name.replace('.', '_'), typedef.name))
            def slot_func(space, w_self, arg):
                return space.call_function(slot_fn, w_self, space.wrap(arg))
            handled = True

    # ternary functions
    for tp_name, attr in [('tp_as_number.c_nb_power', '__pow__'),
                          ]:
        if name == tp_name:
            slot_fn = w_type.getdictvalue(space, attr)
            if slot_fn is None:
                return

            @slot_function([PyObject, PyObject, PyObject], PyObject)
            @func_renamer("cpyext_%s_%s" % (name.replace('.', '_'), typedef.name))
            def slot_func(space, w_self, w_arg1, w_arg2):
                return space.call_function(slot_fn, w_self, w_arg1, w_arg2)
            handled = True

    if handled:
        pass
    elif name == 'tp_setattro':
        setattr_fn = w_type.getdictvalue(space, '__setattr__')
        delattr_fn = w_type.getdictvalue(space, '__delattr__')
        if setattr_fn is None:
            return

        @slot_function([PyObject, PyObject, PyObject], rffi.INT_real,
                     error=-1)
        @func_renamer("cpyext_tp_setattro_%s" % (typedef.name,))
        def slot_tp_setattro(space, w_self, w_name, w_value):
            if w_value is not None:
                space.call_function(setattr_fn, w_self, w_name, w_value)
            else:
                space.call_function(delattr_fn, w_self, w_name)
            return 0
        slot_func = slot_tp_setattro
    elif name == 'tp_getattro':
        getattr_fn = w_type.getdictvalue(space, '__getattribute__')
        if getattr_fn is None:
            return

        @slot_function([PyObject, PyObject], PyObject)
        @func_renamer("cpyext_tp_getattro_%s" % (typedef.name,))
        def slot_tp_getattro(space, w_self, w_name):
            return space.call_function(getattr_fn, w_self, w_name)
        slot_func = slot_tp_getattro

    elif name == 'tp_call':
        call_fn = w_type.getdictvalue(space, '__call__')
        if call_fn is None:
            return

        @slot_function([PyObject, PyObject, PyObject], PyObject)
        @func_renamer("cpyext_%s_%s" % (name.replace('.', '_'), typedef.name))
        def slot_tp_call(space, w_self, w_args, w_kwds):
            args = Arguments(space, [w_self],
                             w_stararg=w_args, w_starstararg=w_kwds)
            return space.call_args(call_fn, args)
        slot_func = slot_tp_call

    elif name == 'tp_iternext':
        iternext_fn = w_type.getdictvalue(space, '__next__')
        if iternext_fn is None:
            return

        @slot_function([PyObject], PyObject)
        @func_renamer("cpyext_%s_%s" % (name.replace('.', '_'), typedef.name))
        def slot_tp_iternext(space, w_self):
            try:
                return space.call_function(iternext_fn, w_self)
            except OperationError as e:
                if not e.match(space, space.w_StopIteration):
                    raise
                return None
        slot_func = slot_tp_iternext

    elif name == 'tp_init':
        init_fn = w_type.getdictvalue(space, '__init__')
        if init_fn is None:
            return

        @slot_function([PyObject, PyObject, PyObject], rffi.INT_real, error=-1)
        @func_renamer("cpyext_%s_%s" % (name.replace('.', '_'), typedef.name))
        def slot_tp_init(space, w_self, w_args, w_kwds):
            args = Arguments(space, [w_self],
                             w_stararg=w_args, w_starstararg=w_kwds)
            space.call_args(init_fn, args)
            return 0
        slot_func = slot_tp_init
    elif name == 'tp_new':
        new_fn = w_type.getdictvalue(space, '__new__')
        if new_fn is None:
            return

        @slot_function([PyTypeObjectPtr, PyObject, PyObject], PyObject)
        @func_renamer("cpyext_%s_%s" % (name.replace('.', '_'), typedef.name))
        def slot_tp_new(space, w_self, w_args, w_kwds):
            args = Arguments(space, [w_self],
                             w_stararg=w_args, w_starstararg=w_kwds)
            return space.call_args(space.get(new_fn, w_self), args)
        slot_func = slot_tp_new
    elif name == 'tp_as_buffer.c_bf_getbuffer':
        buff_fn = w_type.getdictvalue(space, '__buffer__')
        if buff_fn is None:
            return
        @slot_function([PyObject, Py_bufferP, rffi.INT_real],
                rffi.INT_real, error=-1)
        @func_renamer("cpyext_%s_%s" % (name.replace('.', '_'), typedef.name))
        def buff_w(space, w_self, view, flags):
            args = Arguments(space, [space.newint(flags)])
            w_obj = space.call_args(space.get(buff_fn, w_self), args)
            if view:
                #like PyObject_GetBuffer
                flags = widen(flags)
                buf = space.buffer_w(w_obj, flags)
                try:
                    view.c_buf = rffi.cast(rffi.VOIDP, buf.get_raw_address())
                    view.c_obj = make_ref(space, w_obj)
                except ValueError:
                    w_s = space.newbytes(buf.as_str())
                    view.c_obj = make_ref(space, w_s)
                    view.c_buf = rffi.cast(rffi.VOIDP, rffi.str2charp(
                                    space.str_w(w_s), track_allocation=False))
                    rffi.setintfield(view, 'c_readonly', 1)
                ret = fill_Py_buffer(space, buf, view)
                return ret
            return 0
        # XXX remove this when it no longer crashes a translated PyPy
        return
        slot_func = buff_w
    else:
        # missing: tp_as_number.nb_nonzero, tp_as_number.nb_coerce
        # tp_as_sequence.c_sq_contains, tp_as_sequence.c_sq_length
        # richcmpfunc(s)
        return

    return slot_func

PyWrapperFlag_KEYWORDS = 1

class TypeSlot:
    def __init__(self, method_name, slot_name, function, wrapper1, wrapper2, doc):
        self.method_name = method_name
        self.slot_name = slot_name
        self.slot_names = ("c_" + slot_name).split(".")
        self.slot_func = function
        self.wrapper_func = wrapper1
        self.wrapper_func_kwds = wrapper2
        self.doc = doc

# adapted from typeobject.c
def FLSLOT(NAME, SLOT, FUNCTION, WRAPPER, DOC, FLAGS):
    if WRAPPER is None:
        wrapper = None
    else:
        wrapper = globals().get(WRAPPER, Ellipsis)

    # irregular interface, because of tp_getattr/tp_getattro confusion
    if NAME == "__getattr__":
        if SLOT == "tp_getattro":
            wrapper = wrap_getattro
        elif SLOT == "tp_getattr":
            wrapper = wrap_getattr
        else:
            assert False

    function = getattr(userslot, FUNCTION or '!missing', None)
    assert FLAGS == 0 or FLAGS == PyWrapperFlag_KEYWORDS
    if FLAGS:
        if wrapper is Ellipsis:
            @func_renamer(WRAPPER)
            def wrapper(space, w_self, w_args, func, w_kwds):
                raise NotImplementedError("Wrapper for slot " + NAME)
        wrapper1 = None
        wrapper2 = wrapper
    else:
        if wrapper is Ellipsis:
            @func_renamer(WRAPPER)
            def wrapper(space, w_self, w_args, func):
                raise NotImplementedError("Wrapper for slot " + NAME)
        wrapper1 = wrapper
        wrapper2 = None
    return TypeSlot(NAME, SLOT, function, wrapper1, wrapper2, DOC)

def TPSLOT(NAME, SLOT, FUNCTION, WRAPPER, DOC):
    return FLSLOT(NAME, SLOT, FUNCTION, WRAPPER, DOC, 0)

ETSLOT = TPSLOT

def AMSLOT(NAME, SLOT, FUNCTION, WRAPPER, DOC):
    return ETSLOT(NAME, "tp_as_async.c_" + SLOT, FUNCTION, WRAPPER, DOC)
def SQSLOT(NAME, SLOT, FUNCTION, WRAPPER, DOC):
    return ETSLOT(NAME, "tp_as_sequence.c_" + SLOT, FUNCTION, WRAPPER, DOC)
def MPSLOT(NAME, SLOT, FUNCTION, WRAPPER, DOC):
    return ETSLOT(NAME, "tp_as_mapping.c_" + SLOT, FUNCTION, WRAPPER, DOC)
def NBSLOT(NAME, SLOT, FUNCTION, WRAPPER, DOC):
    return ETSLOT(NAME, "tp_as_number.c_" + SLOT, FUNCTION, WRAPPER, DOC)
def UNSLOT(NAME, SLOT, FUNCTION, WRAPPER, DOC):
    return ETSLOT(NAME, "tp_as_number.c_" + SLOT, FUNCTION, WRAPPER,
            "x." + NAME + "() <==> " + DOC)
def IBSLOT(NAME, SLOT, FUNCTION, WRAPPER, DOC):
    return ETSLOT(NAME, "tp_as_number.c_" + SLOT, FUNCTION, WRAPPER,
            "x." + NAME + "(y) <==> x" + DOC + "y")
def BINSLOT(NAME, SLOT, FUNCTION, DOC):
    return ETSLOT(NAME, "tp_as_number.c_" + SLOT, FUNCTION, "wrap_binaryfunc_l", \
            "x." + NAME + "(y) <==> x" + DOC + "y")
def RBINSLOT(NAME, SLOT, FUNCTION, DOC):
    return ETSLOT(NAME, "tp_as_number.c_" + SLOT, FUNCTION, "wrap_binaryfunc_r", \
            "x." + NAME + "(y) <==> y" + DOC + "x")
def BINSLOTNOTINFIX(NAME, SLOT, FUNCTION, DOC):
    return ETSLOT(NAME, "tp_as_number.c_" + SLOT, FUNCTION, "wrap_binaryfunc_l", \
            "x." + NAME + "(y) <==> " + DOC)
def RBINSLOTNOTINFIX(NAME, SLOT, FUNCTION, DOC):
    return ETSLOT(NAME, "tp_as_number.c_" + SLOT, FUNCTION, "wrap_binaryfunc_r", \
            "x." + NAME + "(y) <==> " + DOC)

"""
    /* Heap types defining __add__/__mul__ have sq_concat/sq_repeat == NULL.
       The logic in abstract.c always falls back to nb_add/nb_multiply in
       this case.  Defining both the nb_* and the sq_* slots to call the
       user-defined methods has unexpected side-effects, as shown by
       test_descr.notimplemented() */
"""
# Instructions for update:
# Copy new slotdefs from typeobject.c
# Remove comments and tabs
# Done.
slotdefs_str = r"""
static slotdef slotdefs[] = {
    TPSLOT("__getattribute__", tp_getattr, NULL, NULL, ""),
    TPSLOT("__getattr__", tp_getattr, NULL, NULL, ""),
    TPSLOT("__setattr__", tp_setattr, NULL, NULL, ""),
    TPSLOT("__delattr__", tp_setattr, NULL, NULL, ""),
    TPSLOT("__repr__", tp_repr, slot_tp_repr, wrap_unaryfunc,
           "__repr__($self, /)\n--\n\nReturn repr(self)."),
    TPSLOT("__hash__", tp_hash, slot_tp_hash, wrap_hashfunc,
           "__hash__($self, /)\n--\n\nReturn hash(self)."),
    FLSLOT("__call__", tp_call, slot_tp_call, (wrapperfunc)wrap_call,
           "__call__($self, /, *args, **kwargs)\n--\n\nCall self as a function.",
           PyWrapperFlag_KEYWORDS),
    TPSLOT("__str__", tp_str, slot_tp_str, wrap_unaryfunc,
           "__str__($self, /)\n--\n\nReturn str(self)."),
    TPSLOT("__getattribute__", tp_getattro, slot_tp_getattr_hook,
           wrap_binaryfunc,
           "__getattribute__($self, name, /)\n--\n\nReturn getattr(self, name)."),
    TPSLOT("__getattr__", tp_getattro, slot_tp_getattr_hook, NULL, ""),
    TPSLOT("__setattr__", tp_setattro, slot_tp_setattro, wrap_setattr,
           "__setattr__($self, name, value, /)\n--\n\nImplement setattr(self, name, value)."),
    TPSLOT("__delattr__", tp_setattro, slot_tp_setattro, wrap_delattr,
           "__delattr__($self, name, /)\n--\n\nImplement delattr(self, name)."),
    TPSLOT("__lt__", tp_richcompare, slot_tp_richcompare, richcmp_lt,
           "__lt__($self, value, /)\n--\n\nReturn self<value."),
    TPSLOT("__le__", tp_richcompare, slot_tp_richcompare, richcmp_le,
           "__le__($self, value, /)\n--\n\nReturn self<=value."),
    TPSLOT("__eq__", tp_richcompare, slot_tp_richcompare, richcmp_eq,
           "__eq__($self, value, /)\n--\n\nReturn self==value."),
    TPSLOT("__ne__", tp_richcompare, slot_tp_richcompare, richcmp_ne,
           "__ne__($self, value, /)\n--\n\nReturn self!=value."),
    TPSLOT("__gt__", tp_richcompare, slot_tp_richcompare, richcmp_gt,
           "__gt__($self, value, /)\n--\n\nReturn self>value."),
    TPSLOT("__ge__", tp_richcompare, slot_tp_richcompare, richcmp_ge,
           "__ge__($self, value, /)\n--\n\nReturn self>=value."),
    TPSLOT("__iter__", tp_iter, slot_tp_iter, wrap_unaryfunc,
           "__iter__($self, /)\n--\n\nImplement iter(self)."),
    TPSLOT("__next__", tp_iternext, slot_tp_iternext, wrap_next,
           "__next__($self, /)\n--\n\nImplement next(self)."),
    TPSLOT("__get__", tp_descr_get, slot_tp_descr_get, wrap_descr_get,
           "__get__($self, instance, owner, /)\n--\n\nReturn an attribute of instance, which is of type owner."),
    TPSLOT("__set__", tp_descr_set, slot_tp_descr_set, wrap_descr_set,
           "__set__($self, instance, value, /)\n--\n\nSet an attribute of instance to value."),
    TPSLOT("__delete__", tp_descr_set, slot_tp_descr_set,
           wrap_descr_delete,
           "__delete__($self, instance, /)\n--\n\nDelete an attribute of instance."),
    FLSLOT("__init__", tp_init, slot_tp_init, (wrapperfunc)wrap_init,
           "__init__($self, /, *args, **kwargs)\n--\n\n"
           "Initialize self.  See help(type(self)) for accurate signature.",
           PyWrapperFlag_KEYWORDS),
    TPSLOT("__new__", tp_new, slot_tp_new, NULL,
           "__new__(type, /, *args, **kwargs)\n--\n\n"
           "Create and return new object.  See help(type) for accurate signature."),
    TPSLOT("__del__", tp_finalize, slot_tp_finalize, (wrapperfunc)wrap_del, ""),

    AMSLOT("__await__", am_await, slot_am_await, wrap_unaryfunc,
           "__await__($self, /)\n--\n\nReturn an iterator to be used in await expression."),
    AMSLOT("__aiter__", am_aiter, slot_am_aiter, wrap_unaryfunc,
           "__aiter__($self, /)\n--\n\nReturn an awaitable, that resolves in asynchronous iterator."),
    AMSLOT("__anext__", am_anext, slot_am_anext, wrap_unaryfunc,
           "__anext__($self, /)\n--\n\nReturn a value or raise StopAsyncIteration."),

    BINSLOT("__add__", nb_add, slot_nb_add,
           "+"),
    RBINSLOT("__radd__", nb_add, slot_nb_add,
           "+"),
    BINSLOT("__sub__", nb_subtract, slot_nb_subtract,
           "-"),
    RBINSLOT("__rsub__", nb_subtract, slot_nb_subtract,
           "-"),
    BINSLOT("__mul__", nb_multiply, slot_nb_multiply,
           "*"),
    RBINSLOT("__rmul__", nb_multiply, slot_nb_multiply,
           "*"),
    BINSLOT("__mod__", nb_remainder, slot_nb_remainder,
           "%"),
    RBINSLOT("__rmod__", nb_remainder, slot_nb_remainder,
           "%"),
    BINSLOTNOTINFIX("__divmod__", nb_divmod, slot_nb_divmod,
           "Return divmod(self, value)."),
    RBINSLOTNOTINFIX("__rdivmod__", nb_divmod, slot_nb_divmod,
           "Return divmod(value, self)."),
    NBSLOT("__pow__", nb_power, slot_nb_power, wrap_ternaryfunc,
           "__pow__($self, value, mod=None, /)\n--\n\nReturn pow(self, value, mod)."),
    NBSLOT("__rpow__", nb_power, slot_nb_power, wrap_ternaryfunc_r,
           "__rpow__($self, value, mod=None, /)\n--\n\nReturn pow(value, self, mod)."),
    UNSLOT("__neg__", nb_negative, slot_nb_negative, wrap_unaryfunc, "-self"),
    UNSLOT("__pos__", nb_positive, slot_nb_positive, wrap_unaryfunc, "+self"),
    UNSLOT("__abs__", nb_absolute, slot_nb_absolute, wrap_unaryfunc,
           "abs(self)"),
    UNSLOT("__bool__", nb_bool, slot_nb_bool, wrap_inquirypred,
           "self != 0"),
    UNSLOT("__invert__", nb_invert, slot_nb_invert, wrap_unaryfunc, "~self"),
    BINSLOT("__lshift__", nb_lshift, slot_nb_lshift, "<<"),
    RBINSLOT("__rlshift__", nb_lshift, slot_nb_lshift, "<<"),
    BINSLOT("__rshift__", nb_rshift, slot_nb_rshift, ">>"),
    RBINSLOT("__rrshift__", nb_rshift, slot_nb_rshift, ">>"),
    BINSLOT("__and__", nb_and, slot_nb_and, "&"),
    RBINSLOT("__rand__", nb_and, slot_nb_and, "&"),
    BINSLOT("__xor__", nb_xor, slot_nb_xor, "^"),
    RBINSLOT("__rxor__", nb_xor, slot_nb_xor, "^"),
    BINSLOT("__or__", nb_or, slot_nb_or, "|"),
    RBINSLOT("__ror__", nb_or, slot_nb_or, "|"),
    UNSLOT("__int__", nb_int, slot_nb_int, wrap_unaryfunc,
           "int(self)"),
    UNSLOT("__float__", nb_float, slot_nb_float, wrap_unaryfunc,
           "float(self)"),
    IBSLOT("__iadd__", nb_inplace_add, slot_nb_inplace_add,
           wrap_binaryfunc, "+="),
    IBSLOT("__isub__", nb_inplace_subtract, slot_nb_inplace_subtract,
           wrap_binaryfunc, "-="),
    IBSLOT("__imul__", nb_inplace_multiply, slot_nb_inplace_multiply,
           wrap_binaryfunc, "*="),
    IBSLOT("__imod__", nb_inplace_remainder, slot_nb_inplace_remainder,
           wrap_binaryfunc, "%="),
    IBSLOT("__ipow__", nb_inplace_power, slot_nb_inplace_power,
           wrap_binaryfunc, "**="),
    IBSLOT("__ilshift__", nb_inplace_lshift, slot_nb_inplace_lshift,
           wrap_binaryfunc, "<<="),
    IBSLOT("__irshift__", nb_inplace_rshift, slot_nb_inplace_rshift,
           wrap_binaryfunc, ">>="),
    IBSLOT("__iand__", nb_inplace_and, slot_nb_inplace_and,
           wrap_binaryfunc, "&="),
    IBSLOT("__ixor__", nb_inplace_xor, slot_nb_inplace_xor,
           wrap_binaryfunc, "^="),
    IBSLOT("__ior__", nb_inplace_or, slot_nb_inplace_or,
           wrap_binaryfunc, "|="),
    BINSLOT("__floordiv__", nb_floor_divide, slot_nb_floor_divide, "//"),
    RBINSLOT("__rfloordiv__", nb_floor_divide, slot_nb_floor_divide, "//"),
    BINSLOT("__truediv__", nb_true_divide, slot_nb_true_divide, "/"),
    RBINSLOT("__rtruediv__", nb_true_divide, slot_nb_true_divide, "/"),
    IBSLOT("__ifloordiv__", nb_inplace_floor_divide,
           slot_nb_inplace_floor_divide, wrap_binaryfunc, "//="),
    IBSLOT("__itruediv__", nb_inplace_true_divide,
           slot_nb_inplace_true_divide, wrap_binaryfunc, "/="),
    NBSLOT("__index__", nb_index, slot_nb_index, wrap_unaryfunc,
           "__index__($self, /)\n--\n\n"
           "Return self converted to an integer, if self is suitable "
           "for use as an index into a list."),
    BINSLOT("__matmul__", nb_matrix_multiply, slot_nb_matrix_multiply,
            "@"),
    RBINSLOT("__rmatmul__", nb_matrix_multiply, slot_nb_matrix_multiply,
             "@"),
    IBSLOT("__imatmul__", nb_inplace_matrix_multiply, slot_nb_inplace_matrix_multiply,
           wrap_binaryfunc, "@="),
    MPSLOT("__len__", mp_length, slot_mp_length, wrap_lenfunc,
           "__len__($self, /)\n--\n\nReturn len(self)."),
    MPSLOT("__getitem__", mp_subscript, slot_mp_subscript,
           wrap_binaryfunc,
           "__getitem__($self, key, /)\n--\n\nReturn self[key]."),
    MPSLOT("__setitem__", mp_ass_subscript, slot_mp_ass_subscript,
           wrap_objobjargproc,
           "__setitem__($self, key, value, /)\n--\n\nSet self[key] to value."),
    MPSLOT("__delitem__", mp_ass_subscript, slot_mp_ass_subscript,
           wrap_delitem,
           "__delitem__($self, key, /)\n--\n\nDelete self[key]."),

    SQSLOT("__len__", sq_length, slot_sq_length, wrap_lenfunc,
           "__len__($self, /)\n--\n\nReturn len(self)."),

    SQSLOT("__add__", sq_concat, NULL, wrap_binaryfunc,
           "__add__($self, value, /)\n--\n\nReturn self+value."),
    SQSLOT("__mul__", sq_repeat, NULL, wrap_indexargfunc,
           "__mul__($self, value, /)\n--\n\nReturn self*value.n"),
    SQSLOT("__rmul__", sq_repeat, NULL, wrap_indexargfunc,
           "__rmul__($self, value, /)\n--\n\nReturn self*value."),
    SQSLOT("__getitem__", sq_item, slot_sq_item, wrap_sq_item,
           "__getitem__($self, key, /)\n--\n\nReturn self[key]."),
    SQSLOT("__setitem__", sq_ass_item, slot_sq_ass_item, wrap_sq_setitem,
           "__setitem__($self, key, value, /)\n--\n\nSet self[key] to value."),
    SQSLOT("__delitem__", sq_ass_item, slot_sq_ass_item, wrap_sq_delitem,
           "__delitem__($self, key, /)\n--\n\nDelete self[key]."),
    SQSLOT("__contains__", sq_contains, slot_sq_contains, wrap_objobjproc,
           "__contains__($self, key, /)\n--\n\nReturn key in self."),
    SQSLOT("__iadd__", sq_inplace_concat, NULL,
           wrap_binaryfunc,
           "__iadd__($self, value, /)\n--\n\nImplement self+=value."),
    SQSLOT("__imul__", sq_inplace_repeat, NULL,
           wrap_indexargfunc,
           "__imul__($self, value, /)\n--\n\nImplement self*=value."),

    {NULL}
};
"""

# Convert the above string into python code
slotdef_replacements = (
    ("\s+", " "),            # all on one line
    ("static [^{]*{", "("),  # remove first line...
    ("};", ")"),             # ...last line...
    ("{NULL}", ""),          # ...and sentinel
    # add quotes around function name, slot name, and wrapper name
    (r"(?P<start> +..SLOT\([^,]*, )(?P<fname>[^,]*), (?P<slotcname>[^,]*), (?P<wname>[^,]*)", r"\g<start>'\g<fname>', '\g<slotcname>', '\g<wname>'"),
    (r"(?P<start> *R?[^ ]{3}SLOT(NOTINFIX)?\([^,]*, )(?P<fname>[^,]*), (?P<slotcname>[^,]*)", r"\g<start>'\g<fname>', '\g<slotcname>'"),
    ("'NULL'", "None"),      # but NULL becomes None
    ("\(wrapperfunc\)", ""), # casts are not needed in python tuples
    ("\),", "),\n"),         # add newlines again
)

for regex, repl in slotdef_replacements:
    slotdefs_str = re.sub(regex, repl, slotdefs_str)

slotdefs = eval(slotdefs_str)
# PyPy addition
slotdefs += (
    TPSLOT("__buffer__", "tp_as_buffer.c_bf_getbuffer", None, "wrap_getbuffer", ""),
)

if not PY3:
    slotdefs += (
        TPSLOT("__rbuffer__", "tp_as_buffer.c_bf_getreadbuffer", None, "wrap_getreadbuffer", ""),
        TPSLOT("__wbuffer__", "tp_as_buffer.c_bf_getwritebuffer", None, "wrap_getwritebuffer", ""),
    )


# partial sort to solve some slot conflicts:
# Number slots before Mapping slots before Sequence slots.
# also prefer the new buffer interface
# These are the only conflicts between __name__ methods
def slotdef_sort_key(slotdef):
    if slotdef.slot_name.startswith('tp_as_number'):
        return 1
    if slotdef.slot_name.startswith('tp_as_mapping'):
        return 2
    if slotdef.slot_name.startswith('tp_as_sequence'):
        return 3
    if slotdef.slot_name == 'tp_as_buffer.c_bf_getbuffer':
        return 100
    if slotdef.slot_name == 'tp_as_buffer.c_bf_getreadbuffer':
        return 101
    return 0
slotdefs = sorted(slotdefs, key=slotdef_sort_key)

slotdefs_for_tp_slots = unrolling_iterable(
    [(x.method_name, x.slot_name, x.slot_names,
      x.slot_func.api_func if x.slot_func else None) for x in slotdefs])

slotdefs_for_wrappers = unrolling_iterable(
    [(x.method_name, x.slot_names, x.wrapper_func, x.wrapper_func_kwds, x.doc)
     for x in slotdefs])

if __name__ == "__main__":
    print slotdefs_str
