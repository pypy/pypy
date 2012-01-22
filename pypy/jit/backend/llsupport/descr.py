import py
from pypy.rpython.lltypesystem import lltype, rffi, llmemory
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.jit.backend.llsupport import symbolic, support
from pypy.jit.metainterp.history import AbstractDescr, getkind
from pypy.jit.metainterp import history
from pypy.jit.codewriter import heaptracker, longlong
from pypy.jit.codewriter.longlong import is_longlong


class GcCache(object):
    def __init__(self, translate_support_code, rtyper=None):
        self.translate_support_code = translate_support_code
        self.rtyper = rtyper
        self._cache_size = {}
        self._cache_field = {}
        self._cache_array = {}
        self._cache_arraylen = {}
        self._cache_call = {}
        self._cache_interiorfield = {}

    def init_size_descr(self, STRUCT, sizedescr):
        assert isinstance(STRUCT, lltype.GcStruct)

    def init_array_descr(self, ARRAY, arraydescr):
        assert (isinstance(ARRAY, lltype.GcArray) or
                isinstance(ARRAY, lltype.GcStruct) and ARRAY._arrayfld)


# ____________________________________________________________
# SizeDescrs

class SizeDescr(AbstractDescr):
    size = 0      # help translation
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

FLAG_POINTER  = 'P'
FLAG_FLOAT    = 'F'
FLAG_UNSIGNED = 'U'
FLAG_SIGNED   = 'S'
FLAG_STRUCT   = 'X'
FLAG_VOID     = 'V'

class FieldDescr(AbstractDescr):
    name = ''
    offset = 0      # help translation
    field_size = 0
    flag = '\x00'

    def __init__(self, name, offset, field_size, flag):
        self.name = name
        self.offset = offset
        self.field_size = field_size
        self.flag = flag

    def is_pointer_field(self):
        return self.flag == FLAG_POINTER

    def is_float_field(self):
        return self.flag == FLAG_FLOAT

    def is_field_signed(self):
        return self.flag == FLAG_SIGNED

    def sort_key(self):
        return self.offset

    def repr_of_descr(self):
        return '<Field%s %s %s>' % (self.flag, self.name, self.offset)


def get_field_descr(gccache, STRUCT, fieldname):
    cache = gccache._cache_field
    try:
        return cache[STRUCT][fieldname]
    except KeyError:
        offset, size = symbolic.get_field_token(STRUCT, fieldname,
                                                gccache.translate_support_code)
        FIELDTYPE = getattr(STRUCT, fieldname)
        flag = get_type_flag(FIELDTYPE)
        name = '%s.%s' % (STRUCT._name, fieldname)
        fielddescr = FieldDescr(name, offset, size, flag)
        cachedict = cache.setdefault(STRUCT, {})
        cachedict[fieldname] = fielddescr
        return fielddescr

def get_type_flag(TYPE):
    if isinstance(TYPE, lltype.Ptr):
        if TYPE.TO._gckind == 'gc':
            return FLAG_POINTER
        else:
            return FLAG_UNSIGNED
    if isinstance(TYPE, lltype.Struct):
        return FLAG_STRUCT
    if TYPE is lltype.Float or is_longlong(TYPE):
        return FLAG_FLOAT
    if (TYPE is not lltype.Bool and isinstance(TYPE, lltype.Number) and
           rffi.cast(TYPE, -1) == -1):
        return FLAG_SIGNED
    return FLAG_UNSIGNED

def get_field_arraylen_descr(gccache, ARRAY_OR_STRUCT):
    cache = gccache._cache_arraylen
    try:
        return cache[ARRAY_OR_STRUCT]
    except KeyError:
        tsc = gccache.translate_support_code
        (_, _, ofs) = symbolic.get_array_token(ARRAY_OR_STRUCT, tsc)
        size = symbolic.get_size(lltype.Signed, tsc)
        result = FieldDescr("len", ofs, size, get_type_flag(lltype.Signed))
        cache[ARRAY_OR_STRUCT] = result
        return result


# ____________________________________________________________
# ArrayDescrs

class ArrayDescr(AbstractDescr):
    tid = 0
    basesize = 0       # workaround for the annotator
    itemsize = 0
    lendescr = None
    flag = '\x00'

    def __init__(self, basesize, itemsize, lendescr, flag):
        self.basesize = basesize
        self.itemsize = itemsize
        self.lendescr = lendescr    # or None, if no length
        self.flag = flag

    def is_array_of_pointers(self):
        return self.flag == FLAG_POINTER

    def is_array_of_floats(self):
        return self.flag == FLAG_FLOAT

    def is_item_signed(self):
        return self.flag == FLAG_SIGNED

    def is_array_of_structs(self):
        return self.flag == FLAG_STRUCT

    def repr_of_descr(self):
        return '<Array%s %s>' % (self.flag, self.itemsize)


def get_array_descr(gccache, ARRAY_OR_STRUCT):
    cache = gccache._cache_array
    try:
        return cache[ARRAY_OR_STRUCT]
    except KeyError:
        tsc = gccache.translate_support_code
        basesize, itemsize, _ = symbolic.get_array_token(ARRAY_OR_STRUCT, tsc)
        if isinstance(ARRAY_OR_STRUCT, lltype.Array):
            ARRAY_INSIDE = ARRAY_OR_STRUCT
        else:
            ARRAY_INSIDE = ARRAY_OR_STRUCT._flds[ARRAY_OR_STRUCT._arrayfld]
        if ARRAY_INSIDE._hints.get('nolength', False):
            lendescr = None
        else:
            lendescr = get_field_arraylen_descr(gccache, ARRAY_OR_STRUCT)
        flag = get_type_flag(ARRAY_INSIDE.OF)
        arraydescr = ArrayDescr(basesize, itemsize, lendescr, flag)
        if ARRAY_OR_STRUCT._gckind == 'gc':
            gccache.init_array_descr(ARRAY_OR_STRUCT, arraydescr)
        cache[ARRAY_OR_STRUCT] = arraydescr
        return arraydescr


# ____________________________________________________________
# InteriorFieldDescr

class InteriorFieldDescr(AbstractDescr):
    arraydescr = ArrayDescr(0, 0, None, '\x00')  # workaround for the annotator
    fielddescr = FieldDescr('', 0, 0, '\x00')

    def __init__(self, arraydescr, fielddescr):
        assert arraydescr.flag == FLAG_STRUCT
        self.arraydescr = arraydescr
        self.fielddescr = fielddescr

    def sort_key(self):
        return self.fielddescr.sort_key()

    def is_pointer_field(self):
        return self.fielddescr.is_pointer_field()

    def is_float_field(self):
        return self.fielddescr.is_float_field()

    def repr_of_descr(self):
        return '<InteriorFieldDescr %s>' % self.fielddescr.repr_of_descr()

def get_interiorfield_descr(gc_ll_descr, ARRAY, name):
    cache = gc_ll_descr._cache_interiorfield
    try:
        return cache[(ARRAY, name)]
    except KeyError:
        arraydescr = get_array_descr(gc_ll_descr, ARRAY)
        fielddescr = get_field_descr(gc_ll_descr, ARRAY.OF, name)
        descr = InteriorFieldDescr(arraydescr, fielddescr)
        cache[(ARRAY, name)] = descr
        return descr

def get_dynamic_interiorfield_descr(gc_ll_descr, offset, width, fieldsize,
                                    is_pointer, is_float, is_signed):
    arraydescr = ArrayDescr(0, width, None, FLAG_STRUCT)
    if is_pointer:
        assert not is_float
        flag = FLAG_POINTER
    elif is_float:
        flag = FLAG_FLOAT
    elif is_signed:
        flag = FLAG_SIGNED
    else:
        flag = FLAG_UNSIGNED
    fielddescr = FieldDescr('dynamic', offset, fieldsize, flag)
    return InteriorFieldDescr(arraydescr, fielddescr)


# ____________________________________________________________
# CallDescrs

class CallDescr(AbstractDescr):
    arg_classes = ''     # <-- annotation hack
    result_type = '\x00'
    result_flag = '\x00'
    ffi_flags = 1
    call_stub_i = staticmethod(lambda func, args_i, args_r, args_f:
                               0)
    call_stub_r = staticmethod(lambda func, args_i, args_r, args_f:
                               lltype.nullptr(llmemory.GCREF.TO))
    call_stub_f = staticmethod(lambda func,args_i,args_r,args_f:
                               longlong.ZEROF)

    def __init__(self, arg_classes, result_type, result_signed, result_size,
                 extrainfo=None, ffi_flags=1):
        """
            'arg_classes' is a string of characters, one per argument:
                'i', 'r', 'f', 'L', 'S'

            'result_type' is one character from the same list or 'v'

            'result_signed' is a boolean True/False
        """
        self.arg_classes = arg_classes
        self.result_type = result_type
        self.result_size = result_size
        self.extrainfo = extrainfo
        self.ffi_flags = ffi_flags
        # NB. the default ffi_flags is 1, meaning FUNCFLAG_CDECL, which
        # makes sense on Windows as it's the one for all the C functions
        # we are compiling together with the JIT.  On non-Windows platforms
        # it is just ignored anyway.
        if result_type == 'v':
            result_flag = FLAG_VOID
        elif result_type == 'i':
            if result_signed:
                result_flag = FLAG_SIGNED
            else:
                result_flag = FLAG_UNSIGNED
        elif result_type == history.REF:
            result_flag = FLAG_POINTER
        elif result_type == history.FLOAT or result_type == 'L':
            result_flag = FLAG_FLOAT
        elif result_type == 'S':
            result_flag = FLAG_UNSIGNED
        else:
            raise NotImplementedError("result_type = '%s'" % (result_type,))
        self.result_flag = result_flag

    def __repr__(self):
        res = 'CallDescr(%s)' % (self.arg_classes,)
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

    def get_result_type(self):
        return self.result_type

    def get_result_size(self):
        return self.result_size

    def is_result_signed(self):
        return self.result_flag == FLAG_SIGNED

    def create_call_stub(self, rtyper, RESULT):
        from pypy.rlib.clibffi import FFI_DEFAULT_ABI
        assert self.get_call_conv() == FFI_DEFAULT_ABI, (
            "%r: create_call_stub() with a non-default call ABI" % (self,))

        def process(c):
            if c == 'L':
                assert longlong.supports_longlong
                c = 'f'
            elif c == 'f' and longlong.supports_longlong:
                return 'longlong.getrealfloat(%s)' % (process('L'),)
            elif c == 'S':
                return 'longlong.int2singlefloat(%s)' % (process('i'),)
            elif c == 'H':
                return 'llop.hide_into_ptr32(llmemory.HiddenGcRef32, %s)' % (
                    process('r'),)
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
            elif arg == 'H':
                return llmemory.HiddenGcRef32
            else:
                raise AssertionError(arg)

        seen = {'i': 0, 'r': 0, 'f': 0}
        args = ", ".join([process(c) for c in self.arg_classes])

        result_type = self.get_result_type()
        if result_type == history.INT:
            result = 'rffi.cast(lltype.Signed, res)'
            category = 'i'
        elif result_type == history.REF:
            assert RESULT == llmemory.GCREF   # should be ensured by the caller
            result = 'lltype.cast_opaque_ptr(llmemory.GCREF, res)'
            category = 'r'
        elif result_type == history.FLOAT:
            result = 'longlong.getfloatstorage(res)'
            category = 'f'
        elif result_type == 'L':
            result = 'rffi.cast(lltype.SignedLongLong, res)'
            category = 'f'
        elif result_type == history.VOID:
            result = '0'
            category = 'i'
        elif result_type == 'S':
            result = 'longlong.singlefloat2int(res)'
            category = 'i'
        elif result_type == 'H':
            result = 'llop.show_from_ptr32(llmemory.GCREF, res)'
            category = 'r'
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
        call_stub = d['call_stub']
        # store the function into one of three attributes, to preserve
        # type-correctness of the return value
        setattr(self, 'call_stub_%s' % category, call_stub)

    def verify_types(self, args_i, args_r, args_f, return_type):
        assert self.result_type in return_type
        assert (self.arg_classes.count('i') +
                self.arg_classes.count('S')) == len(args_i or ())
        assert (self.arg_classes.count('r') +
                self.arg_classes.count('H')) == len(args_r or ())
        assert (self.arg_classes.count('f') +
                self.arg_classes.count('L')) == len(args_f or ())

    def repr_of_descr(self):
        res = 'Call%s %d' % (self.result_type, self.result_size)
        if self.arg_classes:
            res += ' ' + self.arg_classes
        if self.extrainfo:
            res += ' EF=%d' % self.extrainfo.extraeffect
            oopspecindex = self.extrainfo.oopspecindex
            if oopspecindex:
                res += ' OS=%d' % oopspecindex
        return '<%s>' % res


def map_type_to_argclass(ARG, accept_void=False):
    kind = getkind(ARG)
    if   kind == 'int':
        if ARG is lltype.SingleFloat: return 'S'
        else:                         return 'i'
    elif kind == 'ref':               return 'r'
    elif kind == 'float':
        if is_longlong(ARG):          return 'L'
        else:                         return 'f'
    elif kind == 'void':
        if accept_void:               return 'v'
    raise NotImplementedError('ARG = %r' % (ARG,))

def get_call_descr(gccache, ARGS, RESULT, extrainfo=None):
    arg_classes = map(map_type_to_argclass, ARGS)
    arg_classes = ''.join(arg_classes)
    result_type = map_type_to_argclass(RESULT, accept_void=True)
    RESULT_ERASED = RESULT
    if RESULT is lltype.Void:
        result_size = 0
        result_signed = False
    else:
        if isinstance(RESULT, lltype.Ptr) and RESULT != llmemory.HiddenGcRef32:
            # avoid too many CallDescrs
            if result_type == 'r':
                RESULT_ERASED = llmemory.GCREF
            else:
                RESULT_ERASED = llmemory.Address
        result_size = symbolic.get_size(RESULT_ERASED,
                                        gccache.translate_support_code)
        result_signed = get_type_flag(RESULT) == FLAG_SIGNED
    key = (arg_classes, result_type, result_signed, RESULT_ERASED, extrainfo)
    cache = gccache._cache_call
    try:
        calldescr = cache[key]
    except KeyError:
        calldescr = CallDescr(arg_classes, result_type, result_signed,
                              result_size, extrainfo)
        calldescr.create_call_stub(gccache.rtyper, RESULT_ERASED)
        cache[key] = calldescr
    assert repr(calldescr.result_size) == repr(result_size)
    return calldescr
