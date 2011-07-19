from __future__ import with_statement

from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rlib.objectmodel import specialize, enforceargs, we_are_translated
from pypy.rlib.rarithmetic import intmask, r_uint, r_singlefloat
from pypy.rlib import jit
from pypy.rlib import clibffi
from pypy.rlib.clibffi import get_libc_name, FUNCFLAG_CDECL, AbstractFuncPtr, \
    push_arg_as_ffiptr, c_ffi_call, FFI_TYPE_STRUCT
from pypy.rlib.rdynload import dlopen, dlclose, dlsym, dlsym_byordinal
from pypy.rlib.rdynload import DLLHANDLE
from pypy.rlib.longlong2float import longlong2float, float2longlong

class types(object):
    """
    This namespace contains the primitive types you can use to declare the
    signatures of the ffi functions.

    In general, the name of the types are closely related to the ones of the
    C-level ffi_type_*: e.g, instead of ffi_type_sint you should use
    libffi.types.sint.

    However, you should not rely on a perfect correspondence: in particular,
    the exact meaning of ffi_type_{slong,ulong} changes a lot between libffi
    versions, so types.slong could be different than ffi_type_slong.
    """

    @classmethod
    def _import(cls):
        prefix = 'ffi_type_'
        for key, value in clibffi.__dict__.iteritems():
            if key.startswith(prefix):
                name = key[len(prefix):]
                setattr(cls, name, value)
        cls.slong = clibffi.cast_type_to_ffitype(rffi.LONG)
        cls.ulong = clibffi.cast_type_to_ffitype(rffi.ULONG)
        cls.slonglong = clibffi.cast_type_to_ffitype(rffi.LONGLONG)
        cls.ulonglong = clibffi.cast_type_to_ffitype(rffi.ULONGLONG)
        cls.wchar_t = clibffi.cast_type_to_ffitype(lltype.UniChar)
        del cls._import

    @staticmethod
    @jit.elidable
    def getkind(ffi_type):
        """Returns 'v' for void, 'f' for float, 'i' for signed integer,
        and 'u' for unsigned integer.
        """
        if   ffi_type is types.void:    return 'v'
        elif ffi_type is types.double:  return 'f'
        elif ffi_type is types.float:   return 's'
        elif ffi_type is types.pointer: return 'u'
        #
        elif ffi_type is types.schar:   return 'i'
        elif ffi_type is types.uchar:   return 'u'
        elif ffi_type is types.sshort:  return 'i'
        elif ffi_type is types.ushort:  return 'u'
        elif ffi_type is types.sint:    return 'i'
        elif ffi_type is types.uint:    return 'u'
        elif ffi_type is types.slong:   return 'i'
        elif ffi_type is types.ulong:   return 'u'
        #
        elif ffi_type is types.sint8:   return 'i'
        elif ffi_type is types.uint8:   return 'u'
        elif ffi_type is types.sint16:  return 'i'
        elif ffi_type is types.uint16:  return 'u'
        elif ffi_type is types.sint32:  return 'i'
        elif ffi_type is types.uint32:  return 'u'
        ## (note that on 64-bit platforms, types.sint64 is types.slong and the
        ## case is caught above)
        elif ffi_type is types.sint64:  return 'I'
        elif ffi_type is types.uint64:  return 'U'
        #
        elif types.is_struct(ffi_type): return 'S'
        raise KeyError

    @staticmethod
    @jit.elidable
    def is_struct(ffi_type):
        return intmask(ffi_type.c_type) == intmask(FFI_TYPE_STRUCT)

types._import()

@specialize.arg(0)
def _fits_into_long(TYPE):
    if isinstance(TYPE, lltype.Ptr):
        return True # pointers always fits into longs
    if not isinstance(TYPE, lltype.Primitive):
        return False
    if TYPE is lltype.Void or TYPE is rffi.FLOAT or TYPE is rffi.DOUBLE:
        return False
    sz = rffi.sizeof(TYPE)
    return sz <= rffi.sizeof(rffi.LONG)


# ======================================================================

IS_32_BIT = (r_uint.BITS == 32)

@specialize.memo()
def _check_type(TYPE):
    if isinstance(TYPE, lltype.Ptr):
        if TYPE.TO._gckind != 'raw':
            raise TypeError, "Can only push raw values to C, not 'gc'"
        # XXX probably we should recursively check for struct fields here,
        # lets just ignore that for now
        if isinstance(TYPE.TO, lltype.Array) and 'nolength' not in TYPE.TO._hints:
            raise TypeError, "Can only push to C arrays without length info"


class ArgChain(object):
    first = None
    last = None
    numargs = 0

    @specialize.argtype(1)
    def arg(self, val):
        TYPE = lltype.typeOf(val)
        _check_type(TYPE)
        if _fits_into_long(TYPE):
            cls = IntArg
            val = rffi.cast(rffi.LONG, val)
        elif TYPE is rffi.DOUBLE:
            cls = FloatArg
        elif TYPE is rffi.LONGLONG or TYPE is rffi.ULONGLONG:
            raise TypeError, 'r_(u)longlong not supported by arg(), use arg_(u)longlong()'
        elif TYPE is rffi.FLOAT:
            raise TypeError, 'r_singlefloat not supported by arg(), use arg_singlefloat()'
        else:
            raise TypeError, 'Unsupported argument type: %s' % TYPE
        self._append(cls(val))
        return self

    def arg_raw(self, val):
        self._append(RawArg(val))

    def arg_longlong(self, val):
        """
        Note: this is a hack. So far, the JIT does not support long longs, so
        you must pass it as if it were a python Float (rffi.DOUBLE).  You can
        use the convenience functions longlong2float and float2longlong to do
        the conversions.  Note that if you use long longs, the call won't
        be jitted at all.
        """
        assert IS_32_BIT      # use a normal integer on 64-bit platforms
        self._append(LongLongArg(val))

    def arg_singlefloat(self, val):
        """
        Note: you must pass a python Float (rffi.DOUBLE), not a r_singlefloat
        (else the jit complains).  Note that if you use single floats, the
        call won't be jitted at all.
        """
        self._append(SingleFloatArg(val))

    def _append(self, arg):
        if self.first is None:
            self.first = self.last = arg
        else:
            self.last.next = arg
            self.last = arg
        self.numargs += 1
    

class AbstractArg(object):
    next = None

class IntArg(AbstractArg):
    """ An argument holding an integer
    """

    def __init__(self, intval):
        self.intval = intval

    def push(self, func, ll_args, i):
        func._push_int(self.intval, ll_args, i)


class FloatArg(AbstractArg):
    """ An argument holding a python float (i.e. a C double)
    """

    def __init__(self, floatval):
        self.floatval = floatval

    def push(self, func, ll_args, i):
        func._push_float(self.floatval, ll_args, i)

class RawArg(AbstractArg):
    """ An argument holding a raw pointer to put inside ll_args
    """

    def __init__(self, ptrval):
        self.ptrval = ptrval

    def push(self, func, ll_args, i):
        func._push_raw(self.ptrval, ll_args, i)

class SingleFloatArg(AbstractArg):
    """ An argument representing a C float (but holding a C double)
    """

    def __init__(self, floatval):
        self.floatval = floatval

    def push(self, func, ll_args, i):
        func._push_single_float(self.floatval, ll_args, i)


class LongLongArg(AbstractArg):
    """ An argument representing a C long long (but holding a C double)
    """

    def __init__(self, floatval):
        self.floatval = floatval

    def push(self, func, ll_args, i):
        func._push_longlong(self.floatval, ll_args, i)


# ======================================================================


class Func(AbstractFuncPtr):

    _immutable_fields_ = ['funcsym']
    argtypes = []
    restype = lltype.nullptr(clibffi.FFI_TYPE_P.TO)
    funcsym = lltype.nullptr(rffi.VOIDP.TO)

    def __init__(self, name, argtypes, restype, funcsym, flags=FUNCFLAG_CDECL,
                 keepalive=None):
        AbstractFuncPtr.__init__(self, name, argtypes, restype, flags)
        self.keepalive = keepalive
        self.funcsym = funcsym

    # ========================================================================
    # PUBLIC INTERFACE
    # ========================================================================

    @jit.unroll_safe
    @specialize.arg(2, 3)
    def call(self, argchain, RESULT, is_struct=False):
        # WARNING!  This code is written carefully in a way that the JIT
        # optimizer will see a sequence of calls like the following:
        #
        #    libffi_prepare_call
        #    libffi_push_arg
        #    libffi_push_arg
        #    ...
        #    libffi_call
        #
        # It is important that there is no other operation in the middle, else
        # the optimizer will fail to recognize the pattern and won't turn it
        # into a fast CALL.  Note that "arg = arg.next" is optimized away,
        # assuming that archain is completely virtual.
        self = jit.promote(self)
        if argchain.numargs != len(self.argtypes):
            raise TypeError, 'Wrong number of arguments: %d expected, got %d' %\
                (argchain.numargs, len(self.argtypes))
        ll_args = self._prepare()
        i = 0
        arg = argchain.first
        while arg:
            arg.push(self, ll_args, i)
            i += 1
            arg = arg.next
        #
        if is_struct:
            assert types.is_struct(self.restype)
            res = self._do_call_raw(self.funcsym, ll_args)
        elif _fits_into_long(RESULT):
            assert not types.is_struct(self.restype)
            res = self._do_call_int(self.funcsym, ll_args)
        elif RESULT is rffi.DOUBLE:
            return self._do_call_float(self.funcsym, ll_args)
        elif RESULT is rffi.FLOAT:
            # XXX: even if RESULT is FLOAT, we still return a DOUBLE, else the
            # jit complains. Note that the jit is disabled in this case
            return self._do_call_single_float(self.funcsym, ll_args)
        elif RESULT is rffi.LONGLONG or RESULT is rffi.ULONGLONG:
            # XXX: even if RESULT is LONGLONG, we still return a DOUBLE, else the
            # jit complains. Note that the jit is disabled in this case
            # (it's not a typo, we really return a DOUBLE)
            assert IS_32_BIT
            return self._do_call_longlong(self.funcsym, ll_args)
        elif RESULT is lltype.Void:
            return self._do_call_void(self.funcsym, ll_args)
        else:
            raise TypeError, 'Unsupported result type: %s' % RESULT
        #
        return rffi.cast(RESULT, res)

    # END OF THE PUBLIC INTERFACE
    # ------------------------------------------------------------------------

    # JIT friendly interface
    # the following methods are supposed to be seen opaquely by the optimizer

    @jit.oopspec('libffi_prepare_call(self)')
    def _prepare(self):
        ll_args = lltype.malloc(rffi.VOIDPP.TO, len(self.argtypes), flavor='raw')
        return ll_args


    # _push_* and _do_call_* in theory could be automatically specialize()d by
    # the annotator.  However, specialization doesn't work well with oopspec,
    # so we specialize them by hand

    @jit.oopspec('libffi_push_int(self, value, ll_args, i)')
    @enforceargs( None, int,   None,    int) # fix the annotation for tests
    def _push_int(self, value, ll_args, i):
        self._push_arg(value, ll_args, i)

    @jit.dont_look_inside
    def _push_raw(self, value, ll_args, i):
        ll_args[i] = value

    @jit.oopspec('libffi_push_float(self, value, ll_args, i)')
    @enforceargs(   None, float, None,    int) # fix the annotation for tests
    def _push_float(self, value, ll_args, i):
        self._push_arg(value, ll_args, i)

    @jit.dont_look_inside
    def _push_single_float(self, value, ll_args, i):
        self._push_arg(r_singlefloat(value), ll_args, i)

    @jit.dont_look_inside
    def _push_longlong(self, floatval, ll_args, i):
        """
        Takes a longlong represented as a python Float. It's a hack for the
        jit, else we could not see the whole libffi module at all"""  
        self._push_arg(float2longlong(floatval), ll_args, i)

    @jit.oopspec('libffi_call_int(self, funcsym, ll_args)')
    def _do_call_int(self, funcsym, ll_args):
        return self._do_call(funcsym, ll_args, rffi.LONG)

    @jit.oopspec('libffi_call_float(self, funcsym, ll_args)')
    def _do_call_float(self, funcsym, ll_args):
        return self._do_call(funcsym, ll_args, rffi.DOUBLE)

    @jit.dont_look_inside
    def _do_call_single_float(self, funcsym, ll_args):
        single_res = self._do_call(funcsym, ll_args, rffi.FLOAT)
        return float(single_res)

    @jit.dont_look_inside
    def _do_call_raw(self, funcsym, ll_args):
        # same as _do_call_int, but marked as jit.dont_look_inside
        return self._do_call(funcsym, ll_args, rffi.LONG)

    @jit.dont_look_inside
    def _do_call_longlong(self, funcsym, ll_args):
        llres = self._do_call(funcsym, ll_args, rffi.LONGLONG)
        return longlong2float(llres)

    @jit.oopspec('libffi_call_void(self, funcsym, ll_args)')
    def _do_call_void(self, funcsym, ll_args):
        return self._do_call(funcsym, ll_args, lltype.Void)

    # ------------------------------------------------------------------------
    # private methods

    @specialize.argtype(1)
    def _push_arg(self, value, ll_args, i):
        # XXX: check the type is not translated?
        argtype = self.argtypes[i]
        c_size = intmask(argtype.c_size)
        ll_buf = lltype.malloc(rffi.CCHARP.TO, c_size, flavor='raw')
        push_arg_as_ffiptr(argtype, value, ll_buf)
        ll_args[i] = ll_buf

    @specialize.arg(3)
    def _do_call(self, funcsym, ll_args, RESULT):
        # XXX: check len(args)?
        ll_result = lltype.nullptr(rffi.CCHARP.TO)
        if self.restype != types.void:
            ll_result = lltype.malloc(rffi.CCHARP.TO,
                                      intmask(self.restype.c_size),
                                      flavor='raw')
        ffires = c_ffi_call(self.ll_cif,
                            self.funcsym,
                            rffi.cast(rffi.VOIDP, ll_result),
                            rffi.cast(rffi.VOIDPP, ll_args))
        if RESULT is not lltype.Void:
            TP = lltype.Ptr(rffi.CArray(RESULT))
            buf = rffi.cast(TP, ll_result)
            if types.is_struct(self.restype):
                assert RESULT == rffi.LONG
                # for structs, we directly return the buffer and transfer the
                # ownership
                res = rffi.cast(RESULT, buf)
            else:
                res = buf[0]
        else:
            res = None
        self._free_buffers(ll_result, ll_args)
        #check_fficall_result(ffires, self.flags)
        return res

    def _free_buffers(self, ll_result, ll_args):
        if ll_result:
            self._free_buffer_maybe(rffi.cast(rffi.VOIDP, ll_result), self.restype)
        for i in range(len(self.argtypes)):
            argtype = self.argtypes[i]
            self._free_buffer_maybe(ll_args[i], argtype)
        lltype.free(ll_args, flavor='raw')

    def _free_buffer_maybe(self, buf, ffitype):
        # if it's a struct, the buffer is not freed and the ownership is
        # already of the caller (in case of ll_args buffers) or transferred to
        # it (in case of ll_result buffer)
        if not types.is_struct(ffitype):
            lltype.free(buf, flavor='raw')


# ======================================================================


# XXX: it partially duplicate the code in clibffi.py
class CDLL(object):
    def __init__(self, libname, mode=-1):
        """Load the library, or raises DLOpenError."""
        self.lib = rffi.cast(DLLHANDLE, 0)
        with rffi.scoped_str2charp(libname) as ll_libname:
            self.lib = dlopen(ll_libname, mode)

    def __del__(self):
        if self.lib:
            dlclose(self.lib)
            self.lib = rffi.cast(DLLHANDLE, 0)

    def getpointer(self, name, argtypes, restype, flags=FUNCFLAG_CDECL):
        return Func(name, argtypes, restype, dlsym(self.lib, name),
                    flags=flags, keepalive=self)

    def getaddressindll(self, name):
        return dlsym(self.lib, name)
