import py
from pypy.rpython.lltypesystem import lltype, rffi, llmemory, rclass
from pypy.jit.backend.llsupport import symbolic, support
from pypy.jit.metainterp.history import AbstractDescr, getkind, BoxInt, BoxPtr
from pypy.jit.metainterp.history import BasicFailDescr, LoopToken, BoxFloat
from pypy.jit.metainterp import history
from pypy.jit.metainterp.resoperation import ResOperation, rop
from pypy.jit.codewriter import heaptracker

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


# ____________________________________________________________
# SizeDescrs

class SizeDescr(AbstractDescr):
    size = 0      # help translation

    def __init__(self, size):
        self.size = size

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
        if heaptracker.has_gcstruct_a_vtable(STRUCT):
            sizedescr = SizeDescrWithVTable(size)
        else:
            sizedescr = SizeDescr(size)
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

    def is_pointer_field(self):
        return self._is_pointer_field

    def is_float_field(self):
        return self._is_float_field

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
                         '_is_float_field')

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


class BaseArrayDescr(AbstractDescr):
    _clsname = ''

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

    def is_array_of_pointers(self):
        return self._is_array_of_pointers

    def is_array_of_floats(self):
        return self._is_array_of_floats

    def repr_of_descr(self):
        return '<%s>' % self._clsname

class NonGcPtrArrayDescr(BaseArrayDescr):
    _clsname = 'NonGcPtrArrayDescr'
    def get_item_size(self, translate_support_code):
        return symbolic.get_size_of_ptr(translate_support_code)

class GcPtrArrayDescr(NonGcPtrArrayDescr):
    _clsname = 'GcPtrArrayDescr'
    _is_array_of_pointers = True

_CA = rffi.CArray(lltype.Signed)

class BaseArrayNoLengthDescr(BaseArrayDescr):
    def get_base_size(self, translate_support_code):
        basesize, _, _ = symbolic.get_array_token(_CA, translate_support_code)
        return basesize

    def get_ofs_length(self, translate_support_code):
        _, _, ofslength = symbolic.get_array_token(_CA, translate_support_code)
        return ofslength

class NonGcPtrArrayNoLengthDescr(BaseArrayNoLengthDescr):
    _clsname = 'NonGcPtrArrayNoLengthDescr'
    def get_item_size(self, translate_support_code):
        return symbolic.get_size_of_ptr(translate_support_code)

class GcPtrArrayNoLengthDescr(NonGcPtrArrayNoLengthDescr):
    _clsname = 'GcPtrArrayNoLengthDescr'
    _is_array_of_pointers = True

def getArrayDescrClass(ARRAY):
    return getDescrClass(ARRAY.OF, BaseArrayDescr, GcPtrArrayDescr,
                         NonGcPtrArrayDescr, 'Array', 'get_item_size',
                         '_is_array_of_floats')

def getArrayNoLengthDescrClass(ARRAY):
    return getDescrClass(ARRAY.OF, BaseArrayNoLengthDescr, GcPtrArrayNoLengthDescr,
                         NonGcPtrArrayNoLengthDescr, 'ArrayNoLength', 'get_item_size',
                         '_is_array_of_floats')

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

    def __init__(self, arg_classes, extrainfo=None):
        self.arg_classes = arg_classes    # string of "r" and "i" (ref/int)
        self.extrainfo = extrainfo

    def get_extra_info(self):
        return self.extrainfo

    def get_arg_types(self):
        return self.arg_classes

    def get_return_type(self):
        return self._return_type

    def get_result_size(self, translate_support_code):
        raise NotImplementedError

    def create_call_stub(self, rtyper, RESULT):
        def process(c):
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

        seen = {'i': 0, 'r': 0, 'f': 0}
        args = ", ".join([process(c) for c in self.arg_classes])

        if self.get_return_type() == history.INT:
            result = 'rffi.cast(lltype.Signed, res)'
        elif self.get_return_type() == history.REF:
            result = 'lltype.cast_opaque_ptr(llmemory.GCREF, res)'
        elif self.get_return_type() == history.FLOAT:
            result = 'res'
        elif self.get_return_type() == history.VOID:
            result = 'None'
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
        d = locals().copy()
        d.update(globals())
        exec source.compile() in d
        self.call_stub = d['call_stub']

    def verify_types(self, args_i, args_r, args_f, return_type):
        assert self._return_type == return_type
        assert self.arg_classes.count('i') == len(args_i or ())
        assert self.arg_classes.count('r') == len(args_r or ())
        assert self.arg_classes.count('f') == len(args_f or ())

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

class DynamicIntCallDescr(BaseIntCallDescr):
    """
    calldescr that works for every integer type, by explicitly passing it the
    size of the result. Used only by get_call_descr_dynamic
    """
    _clsname = 'DynamicIntCallDescr'

    def __init__(self, arg_classes, result_size, extrainfo=None):
        BaseIntCallDescr.__init__(self, arg_classes, extrainfo)
        self._result_size = result_size

    def get_result_size(self, translate_support_code):
        return self._result_size


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
    call_stub = staticmethod(lambda func, args_i, args_r, args_f: 0.0)
    def get_result_size(self, translate_support_code):
        return symbolic.get_size(lltype.Float, translate_support_code)

class VoidCallDescr(BaseCallDescr):
    _clsname = 'VoidCallDescr'
    _return_type = history.VOID
    call_stub = staticmethod(lambda func, args_i, args_r, args_f: None)
    def get_result_size(self, translate_support_code):
        return 0

def getCallDescrClass(RESULT):
    if RESULT is lltype.Void:
        return VoidCallDescr
    if RESULT is lltype.Float:
        return FloatCallDescr
    return getDescrClass(RESULT, BaseIntCallDescr, GcPtrCallDescr,
                         NonGcPtrCallDescr, 'Call', 'get_result_size',
                         Ellipsis)  # <= floatattrname should not be used here

def get_call_descr(gccache, ARGS, RESULT, extrainfo=None):
    arg_classes = []
    for ARG in ARGS:
        kind = getkind(ARG)
        if   kind == 'int': arg_classes.append('i')
        elif kind == 'ref': arg_classes.append('r')
        elif kind == 'float': arg_classes.append('f')
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
                  nameprefix, methodname, floatattrname, _cache={}):
    if isinstance(TYPE, lltype.Ptr):
        if TYPE.TO._gckind == 'gc':
            return GcPtrDescr
        else:
            return NonGcPtrDescr
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
        if TYPE is lltype.Float:
            setattr(Descr, floatattrname, True)
        #
        _cache[nameprefix, TYPE] = Descr
        return Descr
