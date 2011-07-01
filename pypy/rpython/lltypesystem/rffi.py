import py
from pypy.annotation import model as annmodel
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.lltypesystem import ll2ctypes
from pypy.rpython.lltypesystem.llmemory import cast_adr_to_ptr, cast_ptr_to_adr
from pypy.rpython.lltypesystem.llmemory import itemoffsetof, raw_memcopy
from pypy.annotation.model import lltype_to_annotation
from pypy.tool.sourcetools import func_with_new_name
from pypy.rlib.objectmodel import Symbolic, CDefinedIntSymbolic
from pypy.rlib.objectmodel import keepalive_until_here
from pypy.rlib import rarithmetic, rgc
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rlib.unroll import unrolling_iterable
from pypy.rpython.tool.rfficache import platform
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.rpython.annlowlevel import llhelper
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.rstring import StringBuilder, UnicodeBuilder
from pypy.rpython.lltypesystem import llmemory
import os, sys

class CConstant(Symbolic):
    """ A C-level constant, maybe #define, rendered directly.
    """
    def __init__(self, c_name, TP):
        self.c_name = c_name
        self.TP = TP

    def annotation(self):
        return lltype_to_annotation(self.TP)

    def lltype(self):
        return self.TP

def _isfunctype(TP):
    """ Evil hack to get rid of flow objspace inability
    to accept .TO when TP is not a pointer
    """
    return isinstance(TP, lltype.Ptr) and isinstance(TP.TO, lltype.FuncType)
_isfunctype._annspecialcase_ = 'specialize:memo'

def _isllptr(p):
    """ Second evil hack to detect if 'p' is a low-level pointer or not """
    return isinstance(p, lltype._ptr)
class _IsLLPtrEntry(ExtRegistryEntry):
    _about_ = _isllptr
    def compute_result_annotation(self, s_p):
        result = isinstance(s_p, annmodel.SomePtr)
        return self.bookkeeper.immutablevalue(result)
    def specialize_call(self, hop):
        hop.exception_cannot_occur()
        return hop.inputconst(lltype.Bool, hop.s_result.const)

def llexternal(name, args, result, _callable=None,
               compilation_info=ExternalCompilationInfo(),
               sandboxsafe=False, threadsafe='auto',
               _nowrapper=False, calling_conv='c',
               oo_primitive=None, pure_function=False,
               macro=None):
    """Build an external function that will invoke the C function 'name'
    with the given 'args' types and 'result' type.

    You get by default a wrapper that casts between number types as needed
    to match the arguments.  You can also pass an RPython string when a
    CCHARP argument is expected, and the C function receives a 'const char*'
    pointing to a read-only null-terminated character of arrays, as usual
    for C.

    The C function can have callbacks, but they must be specified explicitly
    as constant RPython functions.  We don't support yet C functions that
    invoke callbacks passed otherwise (e.g. set by a previous C call).

    threadsafe: whether it's ok to release the GIL around the call.
                Default is yes, unless sandboxsafe is set, in which case
                we consider that the function is really short-running and
                don't bother releasing the GIL.  An explicit True or False
                overrides this logic.
    """
    if _callable is not None:
        assert callable(_callable)
    ext_type = lltype.FuncType(args, result)
    if _callable is None:
        if macro is not None:
            if macro is True:
                macro = name
            _callable = generate_macro_wrapper(
                name, macro, ext_type, compilation_info)
        else:
            _callable = ll2ctypes.LL2CtypesCallable(ext_type, calling_conv)
    if pure_function:
        _callable._pure_function_ = True
    kwds = {}
    if oo_primitive:
        kwds['oo_primitive'] = oo_primitive

    has_callback = False
    for ARG in args:
        if _isfunctype(ARG):
            has_callback = True
    if has_callback:
        kwds['_callbacks'] = callbackholder = CallbackHolder()
    else:
        callbackholder = None

    funcptr = lltype.functionptr(ext_type, name, external='C',
                                 compilation_info=compilation_info,
                                 _callable=_callable,
                                 _safe_not_sandboxed=sandboxsafe,
                                 _debugexc=True, # on top of llinterp
                                 canraise=False,
                                 **kwds)
    if isinstance(_callable, ll2ctypes.LL2CtypesCallable):
        _callable.funcptr = funcptr

    if _nowrapper:
        return funcptr

    if threadsafe in (False, True):
        # invoke the around-handlers, which release the GIL, if and only if
        # the C function is thread-safe.
        invoke_around_handlers = threadsafe
    else:
        # default case:
        # invoke the around-handlers only for "not too small" external calls;
        # sandboxsafe is a hint for "too-small-ness" (e.g. math functions).
        invoke_around_handlers = not sandboxsafe

    if invoke_around_handlers:
        # The around-handlers are releasing the GIL in a threaded pypy.
        # We need tons of care to ensure that no GC operation and no
        # exception checking occurs while the GIL is released.

        # The actual call is done by this small piece of non-inlinable
        # generated code in order to avoid seeing any GC pointer:
        # neither '*args' nor the GC objects originally passed in as
        # argument to wrapper(), if any (e.g. RPython strings).

        argnames = ', '.join(['a%d' % i for i in range(len(args))])
        source = py.code.Source("""
            def call_external_function(%(argnames)s):
                before = aroundstate.before
                if before: before()
                # NB. it is essential that no exception checking occurs here!
                res = funcptr(%(argnames)s)
                after = aroundstate.after
                if after: after()
                return res
        """ % locals())
        miniglobals = {'aroundstate': aroundstate,
                       'funcptr':     funcptr,
                       '__name__':    __name__, # for module name propagation
                       }
        exec source.compile() in miniglobals
        call_external_function = miniglobals['call_external_function']
        call_external_function._dont_inline_ = True
        call_external_function._annspecialcase_ = 'specialize:ll'
        call_external_function._gctransformer_hint_close_stack_ = True
        call_external_function = func_with_new_name(call_external_function,
                                                    'ccall_' + name)
        # don't inline, as a hack to guarantee that no GC pointer is alive
        # anywhere in call_external_function
    else:
        # if we don't have to invoke the aroundstate, we can just call
        # the low-level function pointer carelessly
        call_external_function = funcptr

    unrolling_arg_tps = unrolling_iterable(enumerate(args))
    def wrapper(*args):
        # XXX the next line is a workaround for the annotation bug
        # shown in rpython.test.test_llann:test_pbctype.  Remove it
        # when the test is fixed...
        assert isinstance(lltype.Signed, lltype.Number)
        real_args = ()
        to_free = ()
        for i, TARGET in unrolling_arg_tps:
            arg = args[i]
            freeme = None
            if TARGET == CCHARP:
                if arg is None:
                    arg = lltype.nullptr(CCHARP.TO)   # None => (char*)NULL
                    freeme = arg
                elif isinstance(arg, str):
                    arg = str2charp(arg)
                    # XXX leaks if a str2charp() fails with MemoryError
                    # and was not the first in this function
                    freeme = arg
            elif TARGET == CWCHARP:
                if arg is None:
                    arg = lltype.nullptr(CWCHARP.TO)   # None => (wchar_t*)NULL
                    freeme = arg
                elif isinstance(arg, unicode):
                    arg = unicode2wcharp(arg)
                    # XXX leaks if a unicode2wcharp() fails with MemoryError
                    # and was not the first in this function
                    freeme = arg
            elif TARGET is VOIDP:
                if arg is None:
                    arg = lltype.nullptr(VOIDP.TO)
                elif isinstance(arg, str):
                    arg = str2charp(arg)
                    freeme = arg
                elif isinstance(arg, unicode):
                    arg = unicode2wcharp(arg)
                    freeme = arg
            elif _isfunctype(TARGET) and not _isllptr(arg):
                # XXX pass additional arguments
                if invoke_around_handlers:
                    arg = llhelper(TARGET, _make_wrapper_for(TARGET, arg,
                                                             callbackholder,
                                                             aroundstate))
                else:
                    arg = llhelper(TARGET, _make_wrapper_for(TARGET, arg,
                                                             callbackholder))
            else:
                SOURCE = lltype.typeOf(arg)
                if SOURCE != TARGET:
                    if TARGET is lltype.Float:
                        arg = float(arg)
                    elif ((isinstance(SOURCE, lltype.Number)
                           or SOURCE is lltype.Bool)
                      and (isinstance(TARGET, lltype.Number)
                           or TARGET is lltype.Bool)):
                        arg = cast(TARGET, arg)
            real_args = real_args + (arg,)
            to_free = to_free + (freeme,)
        res = call_external_function(*real_args)
        for i, TARGET in unrolling_arg_tps:
            if to_free[i]:
                lltype.free(to_free[i], flavor='raw')
        if rarithmetic.r_int is not r_int:
            if result is INT:
                return cast(lltype.Signed, res)
            elif result is UINT:
                return cast(lltype.Unsigned, res)
        return res
    wrapper._annspecialcase_ = 'specialize:ll'
    wrapper._always_inline_ = True
    # for debugging, stick ll func ptr to that
    wrapper._ptr = funcptr

    return func_with_new_name(wrapper, name)

class CallbackHolder:
    def __init__(self):
        self.callbacks = {}

def _make_wrapper_for(TP, callable, callbackholder=None, aroundstate=None):
    """ Function creating wrappers for callbacks. Note that this is
    cheating as we assume constant callbacks and we just memoize wrappers
    """
    from pypy.rpython.lltypesystem import lltype
    from pypy.rpython.lltypesystem.lloperation import llop
    if hasattr(callable, '_errorcode_'):
        errorcode = callable._errorcode_
    else:
        errorcode = TP.TO.RESULT._defl()
    callable_name = getattr(callable, '__name__', '?')
    if callbackholder is not None:
        callbackholder.callbacks[callable] = True
    args = ', '.join(['a%d' % i for i in range(len(TP.TO.ARGS))])
    source = py.code.Source(r"""
        def wrapper(%s):    # no *args - no GIL for mallocing the tuple
            llop.gc_stack_bottom(lltype.Void)   # marker for trackgcroot.py
            if aroundstate is not None:
                after = aroundstate.after
                if after:
                    after()
            # from now on we hold the GIL
            stackcounter.stacks_counter += 1
            try:
                result = callable(%s)
            except Exception, e:
                os.write(2,
                    "Warning: uncaught exception in callback: %%s %%s\n" %%
                    (callable_name, str(e)))
                if not we_are_translated():
                    import traceback
                    traceback.print_exc()
                result = errorcode
            stackcounter.stacks_counter -= 1
            if aroundstate is not None:
                before = aroundstate.before
                if before:
                    before()
            # here we don't hold the GIL any more. As in the wrapper() produced
            # by llexternal, it is essential that no exception checking occurs
            # after the call to before().
            return result
    """ % (args, args))
    miniglobals = locals().copy()
    miniglobals['Exception'] = Exception
    miniglobals['os'] = os
    miniglobals['we_are_translated'] = we_are_translated
    miniglobals['stackcounter'] = stackcounter
    exec source.compile() in miniglobals
    return miniglobals['wrapper']
_make_wrapper_for._annspecialcase_ = 'specialize:memo'

AroundFnPtr = lltype.Ptr(lltype.FuncType([], lltype.Void))
class AroundState:
    def _freeze_(self):
        self.before = None    # or a regular RPython function
        self.after = None     # or a regular RPython function
        return False
aroundstate = AroundState()
aroundstate._freeze_()

class StackCounter:
    def _freeze_(self):
        self.stacks_counter = 1     # number of "stack pieces": callbacks
        return False                # and threads increase it by one
stackcounter = StackCounter()
stackcounter._freeze_()

def llexternal_use_eci(compilation_info):
    """Return a dummy function that, if called in a RPython program,
    adds the given ExternalCompilationInfo to it."""
    eci = ExternalCompilationInfo(post_include_bits=['#define PYPY_NO_OP()'])
    eci = eci.merge(compilation_info)
    return llexternal('PYPY_NO_OP', [], lltype.Void,
                      compilation_info=eci, sandboxsafe=True, _nowrapper=True,
                      _callable=lambda: None)

def generate_macro_wrapper(name, macro, functype, eci):
    """Wraps a function-like macro inside a real function, and expose
    it with llexternal."""

    # Generate the function call
    from pypy.translator.c.database import LowLevelDatabase
    from pypy.translator.c.support import cdecl
    wrapper_name = 'pypy_macro_wrapper_%s' % (name,)
    argnames = ['arg%d' % (i,) for i in range(len(functype.ARGS))]
    db = LowLevelDatabase()
    implementationtypename = db.gettype(functype, argnames=argnames)
    if functype.RESULT is lltype.Void:
        pattern = '%s { %s(%s); }'
    else:
        pattern = '%s { return %s(%s); }'
    source = pattern % (
        cdecl(implementationtypename, wrapper_name),
        macro, ', '.join(argnames))

    # Now stuff this source into a "companion" eci that will be used
    # by ll2ctypes.  We replace eci._with_ctypes, so that only one
    # shared library is actually compiled (when ll2ctypes calls the
    # first function)
    ctypes_eci = eci.merge(ExternalCompilationInfo(
            separate_module_sources=[source],
            export_symbols=[wrapper_name],
            ))
    if hasattr(eci, '_with_ctypes'):
        ctypes_eci = eci._with_ctypes.merge(ctypes_eci)
    eci._with_ctypes = ctypes_eci
    func = llexternal(wrapper_name, functype.ARGS, functype.RESULT,
                      compilation_info=eci, _nowrapper=True)
    # _nowrapper=True returns a pointer which is not hashable
    return lambda *args: func(*args)

# ____________________________________________________________
# Few helpers for keeping callback arguments alive
# this makes passing opaque objects possible (they don't even pass
# through C, only integer specifying number passes)

_KEEPER_CACHE = {}

def _keeper_for_type(TP):
    try:
        return _KEEPER_CACHE[TP]
    except KeyError:
        tp_str = str(TP) # make annotator happy
        class KeepaliveKeeper(object):
            def __init__(self):
                self.stuff_to_keepalive = []
                self.free_positions = []
        keeper = KeepaliveKeeper()
        _KEEPER_CACHE[TP] = keeper
        return keeper
_keeper_for_type._annspecialcase_ = 'specialize:memo'

def register_keepalive(obj):
    """ Register object obj to be kept alive,
    returns a position for that object
    """
    keeper = _keeper_for_type(lltype.typeOf(obj))
    if len(keeper.free_positions):
        pos = keeper.free_positions.pop()
        keeper.stuff_to_keepalive[pos] = obj
        return pos
    # we don't have any free positions
    pos = len(keeper.stuff_to_keepalive)
    keeper.stuff_to_keepalive.append(obj)
    return pos
register_keepalive._annspecialcase_ = 'specialize:argtype(0)'

def get_keepalive_object(pos, TP):
    keeper = _keeper_for_type(TP)
    return keeper.stuff_to_keepalive[pos]
get_keepalive_object._annspecialcase_ = 'specialize:arg(1)'

def unregister_keepalive(pos, TP):
    """ Unregister an object of type TP, stored at position
    pos (position previously returned by register_keepalive)
    """
    keeper = _keeper_for_type(TP)
    keeper.stuff_to_keepalive[pos] = None
    keeper.free_positions.append(pos)
unregister_keepalive._annspecialcase_ = 'specialize:arg(1)'

# ____________________________________________________________

TYPES = []
for _name in 'short int long'.split():
    for name in (_name, 'unsigned ' + _name):
        TYPES.append(name)
TYPES += ['signed char', 'unsigned char',
          'long long', 'unsigned long long',
          'size_t', 'time_t', 'wchar_t']
if os.name != 'nt':
    TYPES.append('mode_t')
    TYPES.append('pid_t')
    TYPES.append('ssize_t')
else:
    MODE_T = lltype.Signed
    PID_T = lltype.Signed
    SSIZE_T = lltype.Signed

def populate_inttypes():
    names = []
    populatelist = []
    for name in TYPES:
        c_name = name
        if name.startswith('unsigned'):
            name = 'u' + name[9:]
            signed = False
        else:
            signed = (name != 'size_t')
        name = name.replace(' ', '')
        names.append(name)
        populatelist.append((name.upper(), c_name, signed))
    platform.populate_inttypes(populatelist)
    return names

def setup():
    """ creates necessary c-level types
    """
    names = populate_inttypes()
    result = []
    for name in names:
        tp = platform.types[name.upper()]
        globals()['r_' + name] = platform.numbertype_to_rclass[tp]
        globals()[name.upper()] = tp
        tpp = lltype.Ptr(lltype.Array(tp, hints={'nolength': True}))
        globals()[name.upper()+'P'] = tpp
        result.append(tp)
    return result

NUMBER_TYPES = setup()
platform.numbertype_to_rclass[lltype.Signed] = int     # avoid "r_long" for common cases
r_int_real = rarithmetic.build_int("r_int_real", r_int.SIGN, r_int.BITS, True)
INT_real = lltype.build_number("INT", r_int_real)
platform.numbertype_to_rclass[INT_real] = r_int_real
NUMBER_TYPES.append(INT_real)

# ^^^ this creates at least the following names:
# --------------------------------------------------------------------
#        Type           RPython integer class doing wrap-around
# --------------------------------------------------------------------
#        SIGNEDCHAR     r_signedchar
#        UCHAR          r_uchar
#        SHORT          r_short
#        USHORT         r_ushort
#        INT            r_int
#        UINT           r_uint
#        LONG           r_long
#        ULONG          r_ulong
#        LONGLONG       r_longlong
#        ULONGLONG      r_ulonglong
#        WCHAR_T        r_wchar_t
#        SIZE_T         r_size_t
#        SSIZE_T        r_ssize_t
#        TIME_T         r_time_t
# --------------------------------------------------------------------
# Note that rffi.r_int is not necessarily the same as
# rarithmetic.r_int, etc!  rffi.INT/r_int correspond to the C-level
# 'int' type, whereas rarithmetic.r_int corresponds to the
# Python-level int type (which is a C long).  Fun.

def CStruct(name, *fields, **kwds):
    """ A small helper to create external C structure, not the
    pypy one
    """
    hints = kwds.get('hints', {})
    hints = hints.copy()
    kwds['hints'] = hints
    hints['external'] = 'C'
    hints['c_name'] = name
    # Hack: prefix all attribute names with 'c_' to cope with names starting
    # with '_'.  The genc backend removes the 'c_' prefixes...
    c_fields = [('c_' + key, value) for key, value in fields]
    return lltype.Struct(name, *c_fields, **kwds)

def CStructPtr(*args, **kwds):
    return lltype.Ptr(CStruct(*args, **kwds))

def CFixedArray(tp, size):
    return lltype.FixedSizeArray(tp, size)
CFixedArray._annspecialcase_ = 'specialize:memo'

def CArray(tp):
    return lltype.Array(tp, hints={'nolength': True})
CArray._annspecialcase_ = 'specialize:memo'

def CArrayPtr(tp):
    return lltype.Ptr(CArray(tp))
CArrayPtr._annspecialcase_ = 'specialize:memo'

def CCallback(args, res):
    return lltype.Ptr(lltype.FuncType(args, res))
CCallback._annspecialcase_ = 'specialize:memo'

def COpaque(name=None, ptr_typedef=None, hints=None, compilation_info=None):
    if compilation_info is None:
        compilation_info = ExternalCompilationInfo()
    if hints is None:
        hints = {}
    else:
        hints = hints.copy()
    hints['external'] = 'C'
    if name is not None:
        hints['c_name'] = name
    if ptr_typedef is not None:
        hints['c_pointer_typedef'] = ptr_typedef
    def lazy_getsize(cache={}):
        from pypy.rpython.tool import rffi_platform
        try:
            return cache[name]
        except KeyError:
            val = rffi_platform.sizeof(name, compilation_info)
            cache[name] = val
            return val

    hints['getsize'] = lazy_getsize
    return lltype.OpaqueType(name, hints)

def COpaquePtr(*args, **kwds):
    typedef = kwds.pop('typedef', None)
    return lltype.Ptr(COpaque(ptr_typedef=typedef, *args, **kwds))

def CExternVariable(TYPE, name, eci, _CConstantClass=CConstant,
                    sandboxsafe=False, _nowrapper=False,
                    c_type=None):
    """Return a pair of functions - a getter and a setter - to access
    the given global C variable.
    """
    from pypy.translator.c.primitive import PrimitiveType
    from pypy.translator.tool.cbuild import ExternalCompilationInfo
    # XXX we cannot really enumerate all C types here, do it on a case-by-case
    #     basis
    if c_type is None:
        if TYPE == CCHARPP:
            c_type = 'char **'
        elif TYPE == CCHARP:
            c_type = 'char *'
        elif TYPE == INT or TYPE == LONG:
            assert False, "ambiguous type on 32-bit machines: give a c_type"
        else:
            c_type = PrimitiveType[TYPE]
            assert c_type.endswith(' @')
            c_type = c_type[:-2] # cut the trailing ' @'

    getter_name = 'get_' + name
    setter_name = 'set_' + name
    getter_prototype = "%(c_type)s %(getter_name)s ();" % locals()
    setter_prototype = "void %(setter_name)s (%(c_type)s v);" % locals()
    c_getter = "%(c_type)s %(getter_name)s () { return %(name)s; }" % locals()
    c_setter = "void %(setter_name)s (%(c_type)s v) { %(name)s = v; }" % locals()

    lines = ["#include <%s>" % i for i in eci.includes]
    if sys.platform != 'win32':
        lines.append('extern %s %s;' % (c_type, name))
    lines.append(c_getter)
    lines.append(c_setter)
    sources = ('\n'.join(lines),)
    new_eci = eci.merge(ExternalCompilationInfo(
        separate_module_sources = sources,
        post_include_bits = [getter_prototype, setter_prototype],
        export_symbols = [getter_name, setter_name],
    ))

    getter = llexternal(getter_name, [], TYPE, compilation_info=new_eci,
                        sandboxsafe=sandboxsafe, _nowrapper=_nowrapper)
    setter = llexternal(setter_name, [TYPE], lltype.Void,
                        compilation_info=new_eci, sandboxsafe=sandboxsafe,
                        _nowrapper=_nowrapper)
    return getter, setter

# char, represented as a Python character
# (use SIGNEDCHAR or UCHAR for the small integer types)
CHAR = lltype.Char

INTPTR_T = SSIZE_T

# double
DOUBLE = lltype.Float
LONGDOUBLE = lltype.LongFloat

# float - corresponds to pypy.rlib.rarithmetic.r_float, and supports no
#         operation except rffi.cast() between FLOAT and DOUBLE
FLOAT = lltype.SingleFloat
r_singlefloat = rarithmetic.r_singlefloat

# void *   - for now, represented as char *
VOIDP = lltype.Ptr(lltype.Array(lltype.Char, hints={'nolength': True, 'render_as_void': True}))
NULL = None

# void **
VOIDPP = CArrayPtr(VOIDP)

# char *
CCHARP = lltype.Ptr(lltype.Array(lltype.Char, hints={'nolength': True}))

# wchar_t *
CWCHARP = lltype.Ptr(lltype.Array(lltype.UniChar, hints={'nolength': True}))

# int *, unsigned int *, etc.
#INTP = ...    see setup() above

# double *
DOUBLEP = lltype.Ptr(lltype.Array(DOUBLE, hints={'nolength': True}))

# float *
FLOATP = lltype.Ptr(lltype.Array(FLOAT, hints={'nolength': True}))

# various type mapping

# conversions between str and char*
# conversions between unicode and wchar_t*
def make_string_mappings(strtype):

    if strtype is str:
        from pypy.rpython.lltypesystem.rstr import STR as STRTYPE
        from pypy.rpython.annlowlevel import llstr as llstrtype
        from pypy.rpython.annlowlevel import hlstr as hlstrtype
        TYPEP = CCHARP
        ll_char_type = lltype.Char
        lastchar = '\x00'
        builder_class = StringBuilder
    else:
        from pypy.rpython.lltypesystem.rstr import UNICODE as STRTYPE
        from pypy.rpython.annlowlevel import llunicode as llstrtype
        from pypy.rpython.annlowlevel import hlunicode as hlstrtype
        TYPEP = CWCHARP
        ll_char_type = lltype.UniChar
        lastchar = u'\x00'
        builder_class = UnicodeBuilder

    # str -> char*
    def str2charp(s):
        """ str -> char*
        """
        array = lltype.malloc(TYPEP.TO, len(s) + 1, flavor='raw')
        i = len(s)
        array[i] = lastchar
        i -= 1
        while i >= 0:
            array[i] = s[i]
            i -= 1
        return array
    str2charp._annenforceargs_ = [strtype]

    def free_charp(cp):
        lltype.free(cp, flavor='raw')

    # char* -> str
    # doesn't free char*
    def charp2str(cp):
        b = builder_class()
        i = 0
        while cp[i] != lastchar:
            b.append(cp[i])
            i += 1
        return b.build()

    # str -> char*
    def get_nonmovingbuffer(data):
        """
        Either returns a non-moving copy or performs neccessary pointer
        arithmetic to return a pointer to the characters of a string if the
        string is already nonmovable.  Must be followed by a
        free_nonmovingbuffer call.
        """
        if rgc.can_move(data):
            count = len(data)
            buf = lltype.malloc(TYPEP.TO, count, flavor='raw')
            for i in range(count):
                buf[i] = data[i]
            return buf
        else:
            data_start = cast_ptr_to_adr(llstrtype(data)) + \
                offsetof(STRTYPE, 'chars') + itemoffsetof(STRTYPE.chars, 0)
            return cast(TYPEP, data_start)
    get_nonmovingbuffer._annenforceargs_ = [strtype]

    # (str, char*) -> None
    def free_nonmovingbuffer(data, buf):
        """
        Either free a non-moving buffer or keep the original storage alive.
        """
        # We cannot rely on rgc.can_move(data) here, because its result
        # might have changed since get_nonmovingbuffer().  Instead we check
        # if 'buf' points inside 'data'.  This is only possible if we
        # followed the 2nd case in get_nonmovingbuffer(); in the first case,
        # 'buf' points to its own raw-malloced memory.
        data = llstrtype(data)
        data_start = cast_ptr_to_adr(data) + \
            offsetof(STRTYPE, 'chars') + itemoffsetof(STRTYPE.chars, 0)
        followed_2nd_path = (buf == cast(TYPEP, data_start))
        keepalive_until_here(data)
        if not followed_2nd_path:
            lltype.free(buf, flavor='raw')
    free_nonmovingbuffer._annenforceargs_ = [strtype, None]

    # int -> (char*, str)
    def alloc_buffer(count):
        """
        Returns a (raw_buffer, gc_buffer) pair, allocated with count bytes.
        The raw_buffer can be safely passed to a native function which expects
        it to not move. Call str_from_buffer with the returned values to get a
        safe high-level string. When the garbage collector cooperates, this
        allows for the process to be performed without an extra copy.
        Make sure to call keep_buffer_alive_until_here on the returned values.
        """
        raw_buf = lltype.malloc(TYPEP.TO, count, flavor='raw')
        return raw_buf, lltype.nullptr(STRTYPE)
    alloc_buffer._always_inline_ = True # to get rid of the returned tuple
    alloc_buffer._annenforceargs_ = [int]

    # (char*, str, int, int) -> None
    def str_from_buffer(raw_buf, gc_buf, allocated_size, needed_size):
        """
        Converts from a pair returned by alloc_buffer to a high-level string.
        The returned string will be truncated to needed_size.
        """
        assert allocated_size >= needed_size

        if gc_buf and (allocated_size == needed_size):
            return hlstrtype(gc_buf)

        new_buf = lltype.malloc(STRTYPE, needed_size)
        try:
            str_chars_offset = (offsetof(STRTYPE, 'chars') + \
                                itemoffsetof(STRTYPE.chars, 0))
            if gc_buf:
                src = cast_ptr_to_adr(gc_buf) + str_chars_offset
            else:
                src = cast_ptr_to_adr(raw_buf) + itemoffsetof(TYPEP.TO, 0)
            dest = cast_ptr_to_adr(new_buf) + str_chars_offset
            ## FIXME: This is bad, because dest could potentially move
            ## if there are threads involved.
            raw_memcopy(src, dest,
                        llmemory.sizeof(ll_char_type) * needed_size)
            return hlstrtype(new_buf)
        finally:
            keepalive_until_here(new_buf)

    # (char*, str) -> None
    def keep_buffer_alive_until_here(raw_buf, gc_buf):
        """
        Keeps buffers alive or frees temporary buffers created by alloc_buffer.
        This must be called after a call to alloc_buffer, usually in a
        try/finally block.
        """
        if gc_buf:
            keepalive_until_here(gc_buf)
        elif raw_buf:
            lltype.free(raw_buf, flavor='raw')

    # char* -> str, with an upper bound on the length in case there is no \x00
    def charp2strn(cp, maxlen):
        b = builder_class(maxlen)
        i = 0
        while i < maxlen and cp[i] != lastchar:
            b.append(cp[i])
            i += 1
        return b.build()

    # char* and size -> str (which can contain null bytes)
    def charpsize2str(cp, size):
        b = builder_class(size)
        for i in xrange(size):
            b.append(cp[i])
        return b.build()
    charpsize2str._annenforceargs_ = [None, int]

    return (str2charp, free_charp, charp2str,
            get_nonmovingbuffer, free_nonmovingbuffer,
            alloc_buffer, str_from_buffer, keep_buffer_alive_until_here,
            charp2strn, charpsize2str,
            )

(str2charp, free_charp, charp2str,
 get_nonmovingbuffer, free_nonmovingbuffer,
 alloc_buffer, str_from_buffer, keep_buffer_alive_until_here,
 charp2strn, charpsize2str,
 ) = make_string_mappings(str)

(unicode2wcharp, free_wcharp, wcharp2unicode,
 get_nonmoving_unicodebuffer, free_nonmoving_unicodebuffer,
 alloc_unicodebuffer, unicode_from_buffer, keep_unicodebuffer_alive_until_here,
 wcharp2unicoden, wcharpsize2unicode,
 ) = make_string_mappings(unicode)

# char**
CCHARPP = lltype.Ptr(lltype.Array(CCHARP, hints={'nolength': True}))

def liststr2charpp(l):
    """ list[str] -> char**, NULL terminated
    """
    array = lltype.malloc(CCHARPP.TO, len(l) + 1, flavor='raw')
    for i in range(len(l)):
        array[i] = str2charp(l[i])
    array[len(l)] = lltype.nullptr(CCHARP.TO)
    return array

def free_charpp(ref):
    """ frees list of char**, NULL terminated
    """
    i = 0
    while ref[i]:
        free_charp(ref[i])
        i += 1
    lltype.free(ref, flavor='raw')

def charpp2liststr(p):
    """ char** NULL terminated -> list[str].  No freeing is done.
    """
    result = []
    i = 0
    while p[i]:
        result.append(charp2str(p[i]))
        i += 1
    return result

cast = ll2ctypes.force_cast      # a forced, no-checking cast

ptradd = ll2ctypes.force_ptradd  # equivalent of "ptr + n" in C.
                                 # the ptr must point to an array.

def size_and_sign(tp):
    size = sizeof(tp)
    try:
        unsigned = not tp._type.SIGNED
    except AttributeError:
        if tp in [lltype.Char, lltype.Float, lltype.Signed] or\
               isinstance(tp, lltype.Ptr):
            unsigned = False
        else:
            unsigned = False
    return size, unsigned

def sizeof(tp):
    """Similar to llmemory.sizeof() but tries hard to return a integer
    instead of a symbolic value.
    """
    if isinstance(tp, lltype.Typedef):
        tp = tp.OF
    if isinstance(tp, lltype.FixedSizeArray):
        return sizeof(tp.OF) * tp.length
    if isinstance(tp, lltype.Struct):
        # the hint is present in structures probed by rffi_platform.
        size = tp._hints.get('size')
        if size is None:
            size = llmemory.sizeof(tp)    # a symbolic result in this case
        return size
    if isinstance(tp, lltype.Ptr):
        tp = ULONG     # XXX!
    if tp is lltype.Char or tp is lltype.Bool:
        return 1
    if tp is lltype.UniChar:
        return r_wchar_t.BITS/8
    if tp is lltype.Float:
        return 8
    if tp is lltype.SingleFloat:
        return 4
    assert isinstance(tp, lltype.Number)
    if tp is lltype.Signed:
        return ULONG._type.BITS/8
    return tp._type.BITS/8
sizeof._annspecialcase_ = 'specialize:memo'

def offsetof(STRUCT, fieldname):
    """Similar to llmemory.offsetof() but tries hard to return a integer
    instead of a symbolic value.
    """
    # the hint is present in structures probed by rffi_platform.
    fieldoffsets = STRUCT._hints.get('fieldoffsets')
    if fieldoffsets is not None:
        # a numeric result when known
        for index, name in enumerate(STRUCT._names):
            if name == fieldname:
                return fieldoffsets[index]
    # a symbolic result as a fallback
    return llmemory.offsetof(STRUCT, fieldname)
offsetof._annspecialcase_ = 'specialize:memo'

# check that we have a sane configuration
# temporary hack for tricking win64
try:
    maxint = sys.orig_maxint
except AttributeError:
    maxint = sys.maxint
assert maxint == (1 << (8 * sizeof(lltype.Signed) - 1)) - 1, (
    "Mixed configuration of the word size of the machine:\n\t"
    "the underlying Python was compiled with maxint=%d,\n\t"
    "but the C compiler says that 'long' is %d bytes" % (
    maxint, sizeof(lltype.Signed)))

# ********************** some helpers *******************

def make(STRUCT, **fields):
    """ Malloc a structure and populate it's fields
    """
    ptr = lltype.malloc(STRUCT, flavor='raw')
    for name, value in fields.items():
        setattr(ptr, name, value)
    return ptr

class MakeEntry(ExtRegistryEntry):
    _about_ = make

    def compute_result_annotation(self, s_type, **s_fields):
        TP = s_type.const
        if not isinstance(TP, lltype.Struct):
            raise TypeError("make called with %s instead of Struct as first argument" % TP)
        return annmodel.SomePtr(lltype.Ptr(TP))

    def specialize_call(self, hop, **fields):
        assert hop.args_s[0].is_constant()
        vlist = [hop.inputarg(lltype.Void, arg=0)]
        flags = {'flavor':'raw'}
        vlist.append(hop.inputconst(lltype.Void, flags))
        hop.has_implicit_exception(MemoryError)   # record that we know about it
        hop.exception_is_here()
        v_ptr = hop.genop('malloc', vlist, resulttype=hop.r_result.lowleveltype)
        for name, i in fields.items():
            name = name[2:]
            v_arg = hop.inputarg(hop.args_r[i], arg=i)
            v_name = hop.inputconst(lltype.Void, name)
            hop.genop('setfield', [v_ptr, v_name, v_arg])
        return v_ptr


def structcopy(pdst, psrc):
    """Copy all the fields of the structure given by 'psrc'
    into the structure given by 'pdst'.
    """
    copy_fn = _get_structcopy_fn(lltype.typeOf(pdst), lltype.typeOf(psrc))
    copy_fn(pdst, psrc)
structcopy._annspecialcase_ = 'specialize:ll'

def _get_structcopy_fn(PDST, PSRC):
    assert PDST == PSRC
    if isinstance(PDST.TO, lltype.Struct):
        STRUCT = PDST.TO
        padding = STRUCT._hints.get('padding', ())
        fields = [(name, STRUCT._flds[name]) for name in STRUCT._names
                                             if name not in padding]
        unrollfields = unrolling_iterable(fields)

        def copyfn(pdst, psrc):
            for name, TYPE in unrollfields:
                if isinstance(TYPE, lltype.ContainerType):
                    structcopy(getattr(pdst, name), getattr(psrc, name))
                else:
                    setattr(pdst, name, getattr(psrc, name))

        return copyfn
    else:
        raise NotImplementedError('structcopy: type %r' % (PDST.TO,))
_get_structcopy_fn._annspecialcase_ = 'specialize:memo'


def setintfield(pdst, fieldname, value):
    """Maybe temporary: a helper to set an integer field into a structure,
    transparently casting between the various integer types.
    """
    STRUCT = lltype.typeOf(pdst).TO
    TSRC = lltype.typeOf(value)
    TDST = getattr(STRUCT, fieldname)
    assert isinstance(TSRC, lltype.Number)
    assert isinstance(TDST, lltype.Number)
    setattr(pdst, fieldname, cast(TDST, value))
setintfield._annspecialcase_ = 'specialize:ll_and_arg(1)'

def getintfield(pdst, fieldname):
    """As temporary as previous: get integer from a field in structure,
    casting it to lltype.Signed
    """
    return cast(lltype.Signed, getattr(pdst, fieldname))
getintfield._annspecialcase_ = 'specialize:ll_and_arg(1)'

class scoped_str2charp:
    def __init__(self, value):
        if value is not None:
            self.buf = str2charp(value)
        else:
            self.buf = lltype.nullptr(CCHARP.TO)
    def __enter__(self):
        return self.buf
    def __exit__(self, *args):
        if self.buf:
            free_charp(self.buf)


class scoped_unicode2wcharp:
    def __init__(self, value):
        if value is not None:
            self.buf = unicode2wcharp(value)
        else:
            self.buf = lltype.nullptr(CWCHARP.TO)
    def __enter__(self):
        return self.buf
    def __exit__(self, *args):
        if self.buf:
            free_wcharp(self.buf)


class scoped_nonmovingbuffer:
    def __init__(self, data):
        self.data = data
    def __enter__(self):
        self.buf = get_nonmovingbuffer(self.data)
        return self.buf
    def __exit__(self, *args):
        free_nonmovingbuffer(self.data, self.buf)


class scoped_nonmoving_unicodebuffer:
    def __init__(self, data):
        self.data = data
    def __enter__(self):
        self.buf = get_nonmoving_unicodebuffer(self.data)
        return self.buf
    def __exit__(self, *args):
        free_nonmoving_unicodebuffer(self.data, self.buf)

class scoped_alloc_buffer:
    def __init__(self, size):
        self.size = size
    def __enter__(self):
        self.raw, self.gc_buf = alloc_buffer(self.size)
        return self
    def __exit__(self, *args):
        keep_buffer_alive_until_here(self.raw, self.gc_buf)
    def str(self, length):
        return str_from_buffer(self.raw, self.gc_buf, self.size, length)

class scoped_alloc_unicodebuffer:
    def __init__(self, size):
        self.size = size
    def __enter__(self):
        self.raw, self.gc_buf = alloc_unicodebuffer(self.size)
        return self
    def __exit__(self, *args):
        keep_unicodebuffer_alive_until_here(self.raw, self.gc_buf)
    def str(self, length):
        return unicode_from_buffer(self.raw, self.gc_buf, self.size, length)
