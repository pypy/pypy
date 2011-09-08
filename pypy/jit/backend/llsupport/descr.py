import py
from pypy.rpython.lltypesystem import lltype, rffi, llmemory, rclass
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.jit.backend.llsupport import symbolic, support
from pypy.jit.metainterp.history import AbstractDescr, getkind, BoxInt, BoxPtr
from pypy.jit.metainterp.history import BasicFailDescr, LoopToken, BoxFloat
from pypy.jit.metainterp import history
from pypy.jit.metainterp.resoperation import ResOperation, rop
from pypy.jit.codewriter import heaptracker, longlong
from pypy.rlib.rarithmetic import r_longlong, r_ulonglong

# The point of the class organization in this file is to make instances
# as compact as possible.  This is done by not storing the field size or
# the 'is_pointer_field' flag in the instance itself but in the class
# (in methods actually) using a few classes instead of just one.


class GcCache(object):
    def __init__(self, translate_support_code, rtyper=None):
        self.translate_support_code = translate_support_code
        self.rtyper = rtyper
        self._cache_size = {}
        self._cache_field = {}
        self._cache_array = {}
        self._cache_call = {}

    def init_size_descr(self, STRUCT, sizedescr):
        assert isinstance(STRUCT, lltype.GcStruct)

    def init_array_descr(self, ARRAY, arraydescr):
        assert isinstance(ARRAY, lltype.GcArray)


if lltype.SignedLongLong is lltype.Signed:
    def is_longlong(TYPE):
        return False
else:
    assert rffi.sizeof(lltype.SignedLongLong) == rffi.sizeof(lltype.Float)
    def is_longlong(TYPE):
        return TYPE in (lltype.SignedLongLong, lltype.UnsignedLongLong)

# ____________________________________________________________
# SizeDescrs

class SizeDescr(AbstractDescr):
    size = 0      # help translation
    is_immutable = False

    tid = llop.combine_ushort(lltype.Signed, 0, 0)

    def __init__(self, size, count_fields_if_immut=-1):
        self.size = size
        self.count_fields_if_immut = count_fields_if_immut

    def count_fields_if_immutable(self):
        return self.count_fields_if_immut

    def repr_of_descr(self):
        return '<SizeDescr %s>' % self.size

class SizeDescrWithVTable(SizeDescr):
    def as_vtable_size_descr(self):
        return self

BaseSizeDescr = SizeDescr

def get_size_descr(gccache, STRUCT):
    cache = gccache._cache_size
    try:
        return cache[STRUCT]
    except KeyError:
        size = symbolic.get_size(STRUCT, gccache.translate_support_code)
        count_fields_if_immut = heaptracker.count_fields_if_immutable(STRUCT)
        if heaptracker.has_gcstruct_a_vtable(STRUCT):
            sizedescr = SizeDescrWithVTable(size, count_fields_if_immut)
        else:
            sizedescr = SizeDescr(size, count_fields_if_immut)
        gccache.init_size_descr(STRUCT, sizedescr)
        cache[STRUCT] = sizedescr
        return sizedescr

# ____________________________________________________________
# FieldDescrs

class BaseFieldDescr(AbstractDescr):
    offset = 0      # help translation
    name = ''
    _clsname = ''

    def __init__(self, name, offset):
        self.name = name
        self.offset = offset

    def sort_key(self):
        return self.offset

    def get_field_size(self, translate_support_code):
        raise NotImplementedError

    _is_pointer_field = False   # unless overridden by GcPtrFieldDescr
    _is_float_field = False     # unless overridden by FloatFieldDescr
    _is_field_signed = False    # unless overridden by XxxFieldDescr

    def is_pointer_field(self):
        return self._is_pointer_field

    def is_float_field(self):
        return self._is_float_field

    def is_field_signed(self):
        return self._is_field_signed

    def repr_of_descr(self):
        return '<%s %s %s>' % (self._clsname, self.name, self.offset)


class NonGcPtrFieldDescr(BaseFieldDescr):
    _clsname = 'NonGcPtrFieldDescr'
    def get_field_size(self, translate_support_code):
        return symbolic.get_size_of_ptr(translate_support_code)

class GcPtrFieldDescr(NonGcPtrFieldDescr):
    _clsname = 'GcPtrFieldDescr'
    _is_pointer_field = True

def getFieldDescrClass(TYPE):
    return getDescrClass(TYPE, BaseFieldDescr, GcPtrFieldDescr,
                         NonGcPtrFieldDescr, 'Field', 'get_field_size',
                         '_is_float_field', '_is_field_signed')

def get_field_descr(gccache, STRUCT, fieldname):
    cache = gccache._cache_field
    try:
        return cache[STRUCT][fieldname]
    except KeyError:
        offset, _ = symbolic.get_field_token(STRUCT, fieldname,
                                             gccache.translate_support_code)
        FIELDTYPE = getattr(STRUCT, fieldname)
        name = '%s.%s' % (STRUCT._name, fieldname)
        fielddescr = getFieldDescrClass(FIELDTYPE)(name, offset)
        cachedict = cache.setdefault(STRUCT, {})
        cachedict[fieldname] = fielddescr
        return fielddescr


# ____________________________________________________________
# ArrayDescrs

_A = lltype.GcArray(lltype.Signed)     # a random gcarray
_AF = lltype.GcArray(lltype.Float)     # an array of C doubles


class BaseArrayDescr(AbstractDescr):
    _clsname = ''
    tid = llop.combine_ushort(lltype.Signed, 0, 0)

    def get_base_size(self, translate_support_code):
        basesize, _, _ = symbolic.get_array_token(_A, translate_support_code)
        return basesize

    def get_ofs_length(self, translate_support_code):
        _, _, ofslength = symbolic.get_array_token(_A, translate_support_code)
        return ofslength

    def get_item_size(self, translate_support_code):
        raise NotImplementedError

    _is_array_of_pointers = False      # unless overridden by GcPtrArrayDescr
    _is_array_of_floats   = False      # unless overridden by FloatArrayDescr
    _is_item_signed       = False      # unless overridden by XxxArrayDescr

    def is_array_of_pointers(self):
        return self._is_array_of_pointers

    def is_array_of_floats(self):
        return self._is_array_of_floats

    def is_item_signed(self):
        return self._is_item_signed

    def repr_of_descr(self):
        return '<%s>' % self._clsname

class NonGcPtrArrayDescr(BaseArrayDescr):
    _clsname = 'NonGcPtrArrayDescr'
    def get_item_size(self, translate_support_code):
        return symbolic.get_size_of_ptr(translate_support_code)

class GcPtrArrayDescr(NonGcPtrArrayDescr):
    _clsname = 'GcPtrArrayDescr'
    _is_array_of_pointers = True

class FloatArrayDescr(BaseArrayDescr):
    _clsname = 'FloatArrayDescr'
    _is_array_of_floats = True
    def get_base_size(self, translate_support_code):
        basesize, _, _ = symbolic.get_array_token(_AF, translate_support_code)
        return basesize
    def get_item_size(self, translate_support_code):
        return symbolic.get_size(lltype.Float, translate_support_code)

class BaseArrayNoLengthDescr(BaseArrayDescr):
    def get_base_size(self, translate_support_code):
        return 0

    def get_ofs_length(self, translate_support_code):
        return -1

class NonGcPtrArrayNoLengthDescr(BaseArrayNoLengthDescr):
    _clsname = 'NonGcPtrArrayNoLengthDescr'
    def get_item_size(self, translate_support_code):
        return symbolic.get_size_of_ptr(translate_support_code)

class GcPtrArrayNoLengthDescr(NonGcPtrArrayNoLengthDescr):
    _clsname = 'GcPtrArrayNoLengthDescr'
    _is_array_of_pointers = True

def getArrayDescrClass(ARRAY):
    if ARRAY.OF is lltype.Float:
        return FloatArrayDescr
    return getDescrClass(ARRAY.OF, BaseArrayDescr, GcPtrArrayDescr,
                         NonGcPtrArrayDescr, 'Array', 'get_item_size',
                         '_is_array_of_floats', '_is_item_signed')

def getArrayNoLengthDescrClass(ARRAY):
    return getDescrClass(ARRAY.OF, BaseArrayNoLengthDescr, GcPtrArrayNoLengthDescr,
                         NonGcPtrArrayNoLengthDescr, 'ArrayNoLength', 'get_item_size',
                         '_is_array_of_floats', '_is_item_signed')

def get_array_descr(gccache, ARRAY):
    cache = gccache._cache_array
    try:
        return cache[ARRAY]
    except KeyError:
        # we only support Arrays that are either GcArrays, or raw no-length
        # non-gc Arrays.
        if ARRAY._hints.get('nolength', False):
            assert not isinstance(ARRAY, lltype.GcArray)
            arraydescr = getArrayNoLengthDescrClass(ARRAY)()
        else:
            assert isinstance(ARRAY, lltype.GcArray)
            arraydescr = getArrayDescrClass(ARRAY)()
        # verify basic assumption that all arrays' basesize and ofslength
        # are equal
        basesize, itemsize, ofslength = symbolic.get_array_token(ARRAY, False)
        assert basesize == arraydescr.get_base_size(False)
        assert itemsize == arraydescr.get_item_size(False)
        if not ARRAY._hints.get('nolength', False):
            assert ofslength == arraydescr.get_ofs_length(False)
        if isinstance(ARRAY, lltype.GcArray):
            gccache.init_array_descr(ARRAY, arraydescr)
        cache[ARRAY] = arraydescr
        return arraydescr


# ____________________________________________________________
# CallDescrs

class BaseCallDescr(AbstractDescr):
    _clsname = ''
    loop_token = None
    arg_classes = ''     # <-- annotation hack
    ffi_flags = 0

    def __init__(self, arg_classes, extrainfo=None, ffi_flags=0):
        self.arg_classes = arg_classes    # string of "r" and "i" (ref/int)
        self.extrainfo = extrainfo
        self.ffi_flags = ffi_flags

    def __repr__(self):
        res = '%s(%s)' % (self.__class__.__name__, self.arg_classes)
        extraeffect = getattr(self.extrainfo, 'extraeffect', None)
        if extraeffect is not None:
            res += ' EF=%r' % extraeffect
        oopspecindex = getattr(self.extrainfo, 'oopspecindex', 0)
        if oopspecindex:
            from pypy.jit.codewriter.effectinfo import EffectInfo
            for key, value in EffectInfo.__dict__.items():
                if key.startswith('OS_') and value == oopspecindex:
                    break
            else:
                key = 'oopspecindex=%r' % oopspecindex
            res += ' ' + key
        return '<%s>' % res

    def get_extra_info(self):
        return self.extrainfo

    def get_ffi_flags(self):
        return self.ffi_flags

    def get_call_conv(self):
        from pypy.rlib.clibffi import get_call_conv
        return get_call_conv(self.ffi_flags, True)

    def get_arg_types(self):
        return self.arg_classes

    def get_return_type(self):
        return self._return_type

    def get_result_size(self, translate_support_code):
        raise NotImplementedError

    def is_result_signed(self):
        return False    # unless overridden

    def create_call_stub(self, rtyper, RESULT):
        def process(c):
            if c == 'L':
                assert longlong.supports_longlong
                c = 'f'
            elif c == 'f' and longlong.supports_longlong:
                return 'longlong.getrealfloat(%s)' % (process('L'),)
            elif c == 'S':
                return 'longlong.int2singlefloat(%s)' % (process('i'),)
            arg = 'args_%s[%d]' % (c, seen[c])
            seen[c] += 1
            return arg

        def TYPE(arg):
            if arg == 'i':
                return lltype.Signed
            elif arg == 'f':
                return lltype.Float
            elif arg == 'r':
                return llmemory.GCREF
            elif arg == 'v':
                return lltype.Void
            elif arg == 'L':
                return lltype.SignedLongLong
            elif arg == 'S':
                return lltype.SingleFloat
            else:
                raise AssertionError(arg)

        seen = {'i': 0, 'r': 0, 'f': 0}
        args = ", ".join([process(c) for c in self.arg_classes])

        if self.get_return_type() == history.INT:
            result = 'rffi.cast(lltype.Signed, res)'
        elif self.get_return_type() == history.REF:
            result = 'lltype.cast_opaque_ptr(llmemory.GCREF, res)'
        elif self.get_return_type() == history.FLOAT:
            result = 'longlong.getfloatstorage(res)'
        elif self.get_return_type() == 'L':
            result = 'rffi.cast(lltype.SignedLongLong, res)'
        elif self.get_return_type() == history.VOID:
            result = 'None'
        elif self.get_return_type() == 'S':
            result = 'longlong.singlefloat2int(res)'
        else:
            assert 0
        source = py.code.Source("""
        def call_stub(func, args_i, args_r, args_f):
            fnptr = rffi.cast(lltype.Ptr(FUNC), func)
            res = support.maybe_on_top_of_llinterp(rtyper, fnptr)(%(args)s)
            return %(result)s
        """ % locals())
        ARGS = [TYPE(arg) for arg in self.arg_classes]
        FUNC = lltype.FuncType(ARGS, RESULT)
        d = globals().copy()
        d.update(locals())
        exec source.compile() in d
        self.call_stub = d['call_stub']

    def verify_types(self, args_i, args_r, args_f, return_type):
        assert self._return_type in return_type
        assert (self.arg_classes.count('i') +
                self.arg_classes.count('S')) == len(args_i or ())
        assert self.arg_classes.count('r') == len(args_r or ())
        assert (self.arg_classes.count('f') +
                self.arg_classes.count('L')) == len(args_f or ())

    def repr_of_descr(self):
        return '<%s>' % self._clsname


class BaseIntCallDescr(BaseCallDescr):
    # Base class of the various subclasses of descrs corresponding to
    # calls having a return kind of 'int' (including non-gc pointers).
    # The inheritance hierarchy is a bit different than with other Descr
    # classes because of the 'call_stub' attribute, which is of type
    #
    #     lambda func, args_i, args_r, args_f --> int/ref/float/void
    #
    # The purpose of BaseIntCallDescr is to be the parent of all classes
    # in which 'call_stub' has a return kind of 'int'.
    _return_type = history.INT
    call_stub = staticmethod(lambda func, args_i, args_r, args_f: 0)

    _is_result_signed = False      # can be overridden in XxxCallDescr
    def is_result_signed(self):
        return self._is_result_signed

class DynamicIntCallDescr(BaseIntCallDescr):
    """
    calldescr that works for every integer type, by explicitly passing it the
    size of the result. Used only by get_call_descr_dynamic
    """
    _clsname = 'DynamicIntCallDescr'

    def __init__(self, arg_classes, result_size, result_sign, extrainfo=None, ffi_flags=0):
        BaseIntCallDescr.__init__(self, arg_classes, extrainfo, ffi_flags)
        assert isinstance(result_sign, bool)
        self._result_size = chr(result_size)
        self._result_sign = result_sign

    def get_result_size(self, translate_support_code):
        return ord(self._result_size)

    def is_result_signed(self):
        return self._result_sign


class NonGcPtrCallDescr(BaseIntCallDescr):
    _clsname = 'NonGcPtrCallDescr'
    def get_result_size(self, translate_support_code):
        return symbolic.get_size_of_ptr(translate_support_code)

class GcPtrCallDescr(BaseCallDescr):
    _clsname = 'GcPtrCallDescr'
    _return_type = history.REF
    call_stub = staticmethod(lambda func, args_i, args_r, args_f:
                             lltype.nullptr(llmemory.GCREF.TO))
    def get_result_size(self, translate_support_code):
        return symbolic.get_size_of_ptr(translate_support_code)

class FloatCallDescr(BaseCallDescr):
    _clsname = 'FloatCallDescr'
    _return_type = history.FLOAT
    call_stub = staticmethod(lambda func,args_i,args_r,args_f: longlong.ZEROF)
    def get_result_size(self, translate_support_code):
        return symbolic.get_size(lltype.Float, translate_support_code)

class LongLongCallDescr(FloatCallDescr):
    _clsname = 'LongLongCallDescr'
    _return_type = 'L'

class VoidCallDescr(BaseCallDescr):
    _clsname = 'VoidCallDescr'
    _return_type = history.VOID
    call_stub = staticmethod(lambda func, args_i, args_r, args_f: None)
    def get_result_size(self, translate_support_code):
        return 0

_SingleFloatCallDescr = None   # built lazily

def getCallDescrClass(RESULT):
    if RESULT is lltype.Void:
        return VoidCallDescr
    if RESULT is lltype.Float:
        return FloatCallDescr
    if RESULT is lltype.SingleFloat:
        global _SingleFloatCallDescr
        if _SingleFloatCallDescr is None:
            assert rffi.sizeof(rffi.UINT) == rffi.sizeof(RESULT)
            class SingleFloatCallDescr(getCallDescrClass(rffi.UINT)):
                _clsname = 'SingleFloatCallDescr'
                _return_type = 'S'
            _SingleFloatCallDescr = SingleFloatCallDescr
        return _SingleFloatCallDescr
    if is_longlong(RESULT):
        return LongLongCallDescr
    return getDescrClass(RESULT, BaseIntCallDescr, GcPtrCallDescr,
                         NonGcPtrCallDescr, 'Call', 'get_result_size',
                         Ellipsis,  # <= floatattrname should not be used here
                         '_is_result_signed')
getCallDescrClass._annspecialcase_ = 'specialize:memo'

def get_call_descr(gccache, ARGS, RESULT, extrainfo=None):
    arg_classes = []
    for ARG in ARGS:
        kind = getkind(ARG)
        if   kind == 'int':
            if ARG is lltype.SingleFloat:
                arg_classes.append('S')
            else:
                arg_classes.append('i')
        elif kind == 'ref': arg_classes.append('r')
        elif kind == 'float':
            if is_longlong(ARG):
                arg_classes.append('L')
            else:
                arg_classes.append('f')
        else:
            raise NotImplementedError('ARG = %r' % (ARG,))
    arg_classes = ''.join(arg_classes)
    cls = getCallDescrClass(RESULT)
    key = (cls, arg_classes, extrainfo)
    cache = gccache._cache_call
    try:
        return cache[key]
    except KeyError:
        calldescr = cls(arg_classes, extrainfo)
        calldescr.create_call_stub(gccache.rtyper, RESULT)
        cache[key] = calldescr
        return calldescr


# ____________________________________________________________

def getDescrClass(TYPE, BaseDescr, GcPtrDescr, NonGcPtrDescr,
                  nameprefix, methodname, floatattrname, signedattrname,
                  _cache={}):
    if isinstance(TYPE, lltype.Ptr):
        if TYPE.TO._gckind == 'gc':
            return GcPtrDescr
        else:
            return NonGcPtrDescr
    if TYPE is lltype.SingleFloat:
        assert rffi.sizeof(rffi.UINT) == rffi.sizeof(TYPE)
        TYPE = rffi.UINT
    try:
        return _cache[nameprefix, TYPE]
    except KeyError:
        #
        class Descr(BaseDescr):
            _clsname = '%s%sDescr' % (TYPE._name, nameprefix)
        Descr.__name__ = Descr._clsname
        #
        def method(self, translate_support_code):
            return symbolic.get_size(TYPE, translate_support_code)
        setattr(Descr, methodname, method)
        #
        if TYPE is lltype.Float or is_longlong(TYPE):
            setattr(Descr, floatattrname, True)
        elif TYPE is not lltype.Bool and rffi.cast(TYPE, -1) == -1:
            setattr(Descr, signedattrname, True)
        #
        _cache[nameprefix, TYPE] = Descr
        return Descr
