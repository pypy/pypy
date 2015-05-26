import sys
from pypy.interpreter.error import oefmt
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef, GetSetProperty, ClassAttr
from pypy.interpreter.gateway import interp2app, unwrap_spec, WrappedDefault
from rpython.rlib import jit, rgc
from rpython.rtyper.lltypesystem import lltype, rffi

from pypy.module._cffi_backend import get_dict_rtld_constants
from pypy.module._cffi_backend import parse_c_type, realize_c_type
from pypy.module._cffi_backend import newtype, cerrno, ccallback, ctypearray
from pypy.module._cffi_backend import ctypestruct, ctypeptr, handle
from pypy.module._cffi_backend import cbuffer, func, cgc, wrapper
from pypy.module._cffi_backend import cffi_opcode
from pypy.module._cffi_backend.ctypeobj import W_CType
from pypy.module._cffi_backend.cdataobj import W_CData


ACCEPT_STRING   = 1
ACCEPT_CTYPE    = 2
ACCEPT_CDATA    = 4
ACCEPT_ALL      = ACCEPT_STRING | ACCEPT_CTYPE | ACCEPT_CDATA
CONSIDER_FN_AS_FNPTR  = 8


def get_ffi_error(space):
    w_ffitype = space.gettypefor(W_FFIObject)
    return w_ffitype.getdictvalue(space, 'error')


class FreeCtxObj(object):
    def __init__(self, ctxobj):
        self.ctxobj = ctxobj
        self.free_mems = []       # filled from cdlopen.py

    def __del__(self):
        ctxobj = self.ctxobj
        free_mems = self.free_mems
        parse_c_type.free_ctxobj(ctxobj)
        i = len(free_mems) - 1
        while i >= 0:
            lltype.free(free_mems[i], flavor='raw')
            i -= 1


class W_FFIObject(W_Root):
    w_gc_wref_remove = None

    @jit.dont_look_inside
    def __init__(self, space, src_ctx):
        self.space = space
        self.types_dict = {}
        self.ctxobj = parse_c_type.allocate_ctxobj(src_ctx)
        self.is_static = bool(src_ctx)
        self.is_nonempty = bool(src_ctx)
        self._finalizer = FreeCtxObj(self.ctxobj)
        if src_ctx:
            self.cached_types = [None] * parse_c_type.get_num_types(src_ctx)
        else:
            self.cached_types = None
        self.w_FFIError = get_ffi_error(space)
        #
        # list of (W_FFIObject, W_LibObject) included in this ffi,
        # where the lib object may be None
        self.included_ffis_libs = []

    def fetch_int_constant(self, name):
        index = parse_c_type.search_in_globals(self.ctxobj.ctx, name)
        if index >= 0:
            g = self.ctxobj.ctx.c_globals[index]
            op = realize_c_type.getop(g.c_type_op)
            if (op == cffi_opcode.OP_CONSTANT_INT or
                  op == cffi_opcode.OP_ENUM):
                return realize_c_type.realize_global_int(self, g, index)
            raise oefmt(self.w_FFIError,
                        "function, global variable or non-integer constant "
                        "'%s' must be fetched from its original 'lib' "
                        "object", name)

        for ffi1, _ in self.included_ffis_libs:
            w_result = ffi1.fetch_int_constant(name)
            if w_result is not None:
                return w_result
        return None

    @jit.elidable_promote()
    def get_string_to_type(self, string, consider_fn_as_fnptr):
        x = self.types_dict[string]     # KeyError if not found
        if isinstance(x, W_CType):
            return x
        else:
            assert isinstance(x, realize_c_type.W_RawFuncType)
            if consider_fn_as_fnptr:
                return x.unwrap_as_fnptr_in_elidable()
            else:
                raise KeyError    # don't handle this error case here

    @jit.dont_look_inside
    def parse_string_to_type(self, string, consider_fn_as_fnptr):
        # This cannot be made @elidable because it calls general space
        # functions (indirectly, e.g. via the new_xxx_type() functions).
        # The get_string_to_type() function above is elidable, and we
        # hope that in almost all cases, get_string_to_type() has already
        # found an answer.
        try:
            x = self.types_dict[string]
        except KeyError:
            info = self.ctxobj.info
            index = parse_c_type.parse_c_type(info, string)
            if index < 0:
                num_spaces = rffi.getintfield(info, 'c_error_location')
                raise oefmt(self.w_FFIError, "%s\n%s\n%s^",
                            rffi.charp2str(info.c_error_message),
                            string,
                            " " * num_spaces)
            x = realize_c_type.realize_c_type_or_func(
                self, self.ctxobj.info.c_output, index)
            assert x is not None
            if isinstance(x, realize_c_type.W_RawFuncType):
                x.unwrap_as_fnptr(self)      # force it here
            self.types_dict[string] = x
        #
        if isinstance(x, W_CType):
            return x
        else:
            assert isinstance(x, realize_c_type.W_RawFuncType)
            if consider_fn_as_fnptr:
                return x.unwrap_as_fnptr_in_elidable()
            else:
                raise x.unexpected_fn_type(self)

    def ffi_type(self, w_x, accept):
        space = self.space
        if (accept & ACCEPT_STRING) and (
                space.isinstance_w(w_x, space.w_basestring)):
            string = space.str_w(w_x)
            consider_fn_as_fnptr = (accept & CONSIDER_FN_AS_FNPTR) != 0
            if jit.isconstant(string):
                try:
                    return self.get_string_to_type(string, consider_fn_as_fnptr)
                except KeyError:
                    pass
            return self.parse_string_to_type(string, consider_fn_as_fnptr)
        if (accept & ACCEPT_CTYPE) and isinstance(w_x, W_CType):
            return w_x
        if (accept & ACCEPT_CDATA) and isinstance(w_x, W_CData):
            return w_x.ctype
        #
        m1 = "string" if accept & ACCEPT_STRING else ""
        m2 = "ctype object" if accept & ACCEPT_CTYPE else ""
        m3 = "cdata object" if accept & ACCEPT_CDATA else ""
        s12 = " or " if m1 and (m2 or m3) else ""
        s23 = " or " if m2 and m3 else ""
        raise oefmt(space.w_TypeError, "expected a %s%s%s%s%s, got '%T'",
                    m1, s12, m2, s23, m3, w_x)


    @unwrap_spec(module_name=str, _version=int, _types=str)
    def descr_init(self, module_name='?', _version=-1, _types='',
                   w__globals=None, w__struct_unions=None, w__enums=None,
                   w__typenames=None, w__includes=None):
        from pypy.module._cffi_backend import cdlopen
        #
        space = self.space
        if self.is_nonempty:
            raise oefmt(space.w_ValueError,
                        "cannot call FFI.__init__() more than once")
        self.is_nonempty = True
        #
        cdlopen.ffiobj_init(self, module_name, _version, _types,
                            w__globals, w__struct_unions, w__enums,
                            w__typenames, w__includes)


    doc_errno = "the value of 'errno' from/to the C calls"

    def get_errno(self, space):
        return cerrno.get_errno(space)

    def set_errno(self, space, errno):
        cerrno.set_errno(space, space.c_int_w(errno))


    def _more_addressof(self, args_w, w_ctype):
        # contains a loop, the JIT doesn't look inside this helper
        offset = 0
        for i in range(len(args_w)):
            w_ctype, ofs1 = w_ctype.direct_typeoffsetof(args_w[i], i > 0)
            offset += ofs1
        return w_ctype, offset

    def descr_addressof(self, w_arg, args_w):
        """\
Limited equivalent to the '&' operator in C:

1. ffi.addressof(<cdata 'struct-or-union'>) returns a cdata that is a
pointer to this struct or union.

2. ffi.addressof(<cdata>, field-or-index...) returns the address of a
field or array item inside the given structure or array, recursively
in case of nested structures or arrays.

3. ffi.addressof(<library>, "name") returns the address of the named
function or global variable."""
        #
        from pypy.module._cffi_backend.lib_obj import W_LibObject
        space = self.space
        if isinstance(w_arg, W_LibObject) and len(args_w) == 1:
            # case 3 in the docstring
            return w_arg.address_of_func_or_global_var(space.str_w(args_w[0]))
        #
        w_ctype = self.ffi_type(w_arg, ACCEPT_CDATA)
        if len(args_w) == 0:
            # case 1 in the docstring
            if (not isinstance(w_ctype, ctypestruct.W_CTypeStructOrUnion) and
                not isinstance(w_ctype, ctypearray.W_CTypeArray)):
                raise oefmt(space.w_TypeError,
                            "expected a cdata struct/union/array object")
            offset = 0
        else:
            # case 2 in the docstring
            if (not isinstance(w_ctype, ctypestruct.W_CTypeStructOrUnion) and
                not isinstance(w_ctype, ctypearray.W_CTypeArray) and
                not isinstance(w_ctype, ctypeptr.W_CTypePointer)):
                raise oefmt(space.w_TypeError,
                        "expected a cdata struct/union/array/pointer object")
            if len(args_w) == 1:
                w_ctype, offset = w_ctype.direct_typeoffsetof(args_w[0], False)
            else:
                w_ctype, offset = self._more_addressof(args_w, w_ctype)
        #
        assert isinstance(w_arg, W_CData)
        cdata = w_arg.unsafe_escaping_ptr()
        cdata = rffi.ptradd(cdata, offset)
        w_ctypeptr = newtype.new_pointer_type(space, w_ctype)
        return W_CData(space, cdata, w_ctypeptr)


    def descr_alignof(self, w_arg):
        """\
Return the natural alignment size in bytes of the argument.
It can be a string naming a C type, or a 'cdata' instance."""
        #
        w_ctype = self.ffi_type(w_arg, ACCEPT_ALL)
        align = w_ctype.alignof()
        return self.space.wrap(align)


    @unwrap_spec(w_cdata=W_CData, size=int)
    def descr_buffer(self, w_cdata, size=-1):
        """\
Return a read-write buffer object that references the raw C data
ointed to by the given 'cdata'.  The 'cdata' must be a pointer or an
array.  Can be passed to functions expecting a buffer, or directly
manipulated with:

    buf[:]          get a copy of it in a regular string, or
    buf[idx]        as a single character
    buf[:] = ...
    buf[idx] = ...  change the content"""
        #
        return cbuffer.buffer(self.space, w_cdata, size)


    @unwrap_spec(w_python_callable=WrappedDefault(None),
                 w_error=WrappedDefault(None))
    def descr_callback(self, w_cdecl, w_python_callable, w_error):
        """\
Return a callback object or a decorator making such a callback object.
'cdecl' must name a C function pointer type.  The callback invokes the
specified 'python_callable' (which may be provided either directly or
via a decorator).  Important: the callback object must be manually
kept alive for as long as the callback may be invoked from the C code."""
        #
        w_ctype = self.ffi_type(w_cdecl, ACCEPT_STRING | ACCEPT_CTYPE |
                                         CONSIDER_FN_AS_FNPTR)
        space = self.space
        if not space.is_none(w_python_callable):
            return ccallback.W_CDataCallback(space, w_ctype,
                                             w_python_callable, w_error)
        else:
            # decorator mode: returns a single-argument function
            return space.appexec([w_ctype, w_error],
            """(ctype, error):
                import _cffi_backend
                return lambda python_callable: (
                    _cffi_backend.callback(ctype, python_callable, error))""")


    def descr_cast(self, w_arg, w_ob):
        """\
Similar to a C cast: returns an instance of the named C
type initialized with the given 'source'.  The source is
casted between integers or pointers of any type."""
        #
        w_ctype = self.ffi_type(w_arg, ACCEPT_STRING | ACCEPT_CTYPE)
        return w_ctype.cast(w_ob)


    def descr_from_buffer(self, w_python_buffer):
        """\
Return a <cdata 'char[]'> that points to the data of the given Python
object, which must support the buffer interface.  Note that this is
not meant to be used on the built-in types str, unicode, or bytearray
(you can build 'char[]' arrays explicitly) but only on objects
containing large quantities of raw data in some other format, like
'array.array' or numpy arrays."""
        #
        w_ctchara = newtype._new_chara_type(self.space)
        return func.from_buffer(self.space, w_ctchara, w_python_buffer)


    @unwrap_spec(w_arg=W_CData)
    def descr_from_handle(self, w_arg):
        """\
Cast a 'void *' back to a Python object.  Must be used *only* on the
pointers returned by new_handle(), and *only* as long as the exact
cdata object returned by new_handle() is still alive (somewhere else
in the program).  Failure to follow these rules will crash."""
        #
        return handle.from_handle(self.space, w_arg)


    @unwrap_spec(w_cdata=W_CData)
    def descr_gc(self, w_cdata, w_destructor):
        """\
Return a new cdata object that points to the same data.
Later, when this new cdata object is garbage-collected,
'destructor(old_cdata_object)' will be called."""
        #
        return cgc.gc_weakrefs_build(self, w_cdata, w_destructor)

    def descr___gc_wref_remove(self, w_ref):
        return cgc.gc_wref_remove(self, w_ref)


    @unwrap_spec(replace_with=str)
    def descr_getctype(self, w_cdecl, replace_with=''):
        """\
Return a string giving the C type 'cdecl', which may be itself a
string or a <ctype> object.  If 'replace_with' is given, it gives
extra text to append (or insert for more complicated C types), like a
variable name, or '*' to get actually the C type 'pointer-to-cdecl'."""
        #
        w_ctype = self.ffi_type(w_cdecl, ACCEPT_STRING | ACCEPT_CTYPE)
        replace_with = replace_with.strip(' ')
        if len(replace_with) == 0:
            result = w_ctype.name
        else:
            add_paren = (replace_with[0] == '*' and
                         isinstance(w_ctype, ctypearray.W_CTypeArray))
            add_space = (not add_paren and replace_with[0] != '['
                                       and replace_with[0] != '(')
            #
            result = w_ctype.name[:w_ctype.name_position]
            if add_paren:
                result += '('
            if add_space:
                result += ' '
            result += replace_with
            if add_paren:
                result += ')'
            result += w_ctype.name[w_ctype.name_position:]
        # Python 3: bytes -> unicode string
        return self.space.wrap(result)


    @unwrap_spec(code=int)
    def descr_getwinerror(self, code=-1):
        """\
Return either the GetLastError() or the error number given by the
optional 'code' argument, as a tuple '(code, message)'."""
        #
        return cerrno.getwinerror(self.space, code)


    @unwrap_spec(w_init=WrappedDefault(None))
    def descr_new(self, w_arg, w_init):
        """\
Allocate an instance according to the specified C type and return a
pointer to it.  The specified C type must be either a pointer or an
array: ``new('X *')`` allocates an X and returns a pointer to it,
whereas ``new('X[n]')`` allocates an array of n X'es and returns an
array referencing it (which works mostly like a pointer, like in C).
You can also use ``new('X[]', n)`` to allocate an array of a
non-constant length n.

The memory is initialized following the rules of declaring a global
variable in C: by default it is zero-initialized, but an explicit
initializer can be given which can be used to fill all or part of the
memory.

When the returned <cdata> object goes out of scope, the memory is
freed.  In other words the returned <cdata> object has ownership of
the value of type 'cdecl' that it points to.  This means that the raw
data can be used as long as this object is kept alive, but must not be
used for a longer time.  Be careful about that when copying the
pointer to the memory somewhere else, e.g. into another structure."""
        #
        w_ctype = self.ffi_type(w_arg, ACCEPT_STRING | ACCEPT_CTYPE)
        return w_ctype.newp(w_init)


    def descr_new_handle(self, w_arg):
        """\
Return a non-NULL cdata of type 'void *' that contains an opaque
reference to the argument, which can be any Python object.  To cast it
back to the original object, use from_handle().  You must keep alive
the cdata object returned by new_handle()!"""
        #
        space = self.space
        return handle._newp_handle(space, newtype._new_voidp_type(space), w_arg)


    def _more_offsetof(self, w_ctype, w_arg0, args_w):
        # contains a loop, the JIT doesn't look inside this helper
        w_ctype, offset = w_ctype.direct_typeoffsetof(w_arg0, False)
        for i in range(len(args_w)):
            w_ctype, ofs1 = w_ctype.direct_typeoffsetof(args_w[i], True)
            offset += ofs1
        return offset

    def descr_offsetof(self, w_arg, w_field_or_array, args_w):
        """\
Return the offset of the named field inside the given structure or
array, which must be given as a C type name.  You can give several
field names in case of nested structures.  You can also give numeric
values which correspond to array items, in case of an array type."""
        #
        w_ctype = self.ffi_type(w_arg, ACCEPT_STRING | ACCEPT_CTYPE)
        if len(args_w) == 0:
            _, offset = w_ctype.direct_typeoffsetof(w_field_or_array, False)
        else:
            offset = self._more_offsetof(w_ctype, w_field_or_array, args_w)
        return self.space.wrap(offset)


    @unwrap_spec(w_cdata=W_CData, maxlen=int)
    def descr_string(self, w_cdata, maxlen=-1):
        """\
Return a Python string (or unicode string) from the 'cdata'.  If
'cdata' is a pointer or array of characters or bytes, returns the
null-terminated string.  The returned string extends until the first
null character, or at most 'maxlen' characters.  If 'cdata' is an
array then 'maxlen' defaults to its length.

If 'cdata' is a pointer or array of wchar_t, returns a unicode string
following the same rules.

If 'cdata' is a single character or byte or a wchar_t, returns it as a
string or unicode string.

If 'cdata' is an enum, returns the value of the enumerator as a
string, or 'NUMBER' if the value is out of range."""
        #
        return w_cdata.ctype.string(w_cdata, maxlen)


    def descr_sizeof(self, w_arg):
        """\
Return the size in bytes of the argument.
It can be a string naming a C type, or a 'cdata' instance."""
        #
        if isinstance(w_arg, W_CData):
            size = w_arg._sizeof()
        else:
            w_ctype = self.ffi_type(w_arg, ACCEPT_ALL)
            size = w_ctype.size
            if size < 0:
                raise oefmt(self.w_FFIError,
                            "don't know the size of ctype '%s'", w_ctype.name)
        return self.space.wrap(size)


    def descr_typeof(self, w_arg):
        """\
Parse the C type given as a string and return the
corresponding <ctype> object.
It can also be used on 'cdata' instance to get its C type."""
        #
        if isinstance(w_arg, wrapper.W_FunctionWrapper):
            return w_arg.typeof(self)
        return self.ffi_type(w_arg, ACCEPT_STRING | ACCEPT_CDATA)


    @unwrap_spec(filename="str_or_None", flags=int)
    def descr_dlopen(self, filename, flags=0):
        """\
Load and return a dynamic library identified by 'name'.  The standard
C library can be loaded by passing None.

Note that functions and types declared with 'ffi.cdef()' are not
linked to a particular library, just like C headers.  In the library
we only look for the actual (untyped) symbols at the time of their
first access."""
        #
        from pypy.module._cffi_backend import cdlopen
        return cdlopen.W_DlOpenLibObject(self, filename, flags)


    def descr_dlclose(self, w_lib):
        """\
Close a library obtained with ffi.dlopen().  After this call, access to
"functions or variables from the library will fail (possibly with a
segmentation fault)."""
        #
        from pypy.module._cffi_backend.lib_obj import W_LibObject
        lib = self.space.interp_w(W_LibObject, w_lib)
        lib.cdlopen_close()


    @unwrap_spec(name=str)
    def descr_integer_const(self, name):
        """\
Get the value of an integer constant.

'ffi.integer_const(\"xxx\")' is equivalent to 'lib.xxx' if xxx names an
integer constant.  The point of this function is limited to use cases
where you have an 'ffi' object but not any associated 'lib' object."""
        #
        w_result = self.fetch_int_constant(name)
        if w_result is None:
            raise oefmt(self.space.w_AttributeError,
                        "integer constant '%s' not found", name)
        return w_result


@jit.dont_look_inside
def W_FFIObject___new__(space, w_subtype, __args__):
    r = space.allocate_instance(W_FFIObject, w_subtype)
    # get in 'src_ctx' a NULL which translation doesn't consider to be constant
    src_ctx = rffi.cast(parse_c_type.PCTX, 0)
    r.__init__(space, src_ctx)
    return space.wrap(r)

def make_CData(space):
    return space.gettypefor(W_CData)

def make_CType(space):
    return space.gettypefor(W_CType)

def make_NULL(space):
    ctvoidp = newtype._new_voidp_type(space)
    w_NULL = ctvoidp.cast(space.wrap(0))
    return w_NULL

def make_error(space):
    return space.appexec([], """():
        return type('error', (Exception,), {'__module__': 'ffi'})""")

_extras = get_dict_rtld_constants()
if sys.platform == 'win32':
    _extras['getwinerror'] = interp2app(W_FFIObject.descr_getwinerror)


W_FFIObject.typedef = TypeDef(
        'CompiledFFI',
        __new__     = interp2app(W_FFIObject___new__),
        __init__    = interp2app(W_FFIObject.descr_init),
        CData       = ClassAttr(make_CData),
        CType       = ClassAttr(make_CType),
        NULL        = ClassAttr(make_NULL),
        error       = ClassAttr(make_error),
        errno       = GetSetProperty(W_FFIObject.get_errno,
                                     W_FFIObject.set_errno,
                                     doc=W_FFIObject.doc_errno,
                                     cls=W_FFIObject),
        __gc_wref_remove = interp2app(W_FFIObject.descr___gc_wref_remove),
        addressof   = interp2app(W_FFIObject.descr_addressof),
        alignof     = interp2app(W_FFIObject.descr_alignof),
        buffer      = interp2app(W_FFIObject.descr_buffer),
        callback    = interp2app(W_FFIObject.descr_callback),
        cast        = interp2app(W_FFIObject.descr_cast),
        dlclose     = interp2app(W_FFIObject.descr_dlclose),
        dlopen      = interp2app(W_FFIObject.descr_dlopen),
        from_buffer = interp2app(W_FFIObject.descr_from_buffer),
        from_handle = interp2app(W_FFIObject.descr_from_handle),
        gc          = interp2app(W_FFIObject.descr_gc),
        getctype    = interp2app(W_FFIObject.descr_getctype),
        integer_const = interp2app(W_FFIObject.descr_integer_const),
        new         = interp2app(W_FFIObject.descr_new),
        new_handle  = interp2app(W_FFIObject.descr_new_handle),
        offsetof    = interp2app(W_FFIObject.descr_offsetof),
        sizeof      = interp2app(W_FFIObject.descr_sizeof),
        string      = interp2app(W_FFIObject.descr_string),
        typeof      = interp2app(W_FFIObject.descr_typeof),
        **_extras)
