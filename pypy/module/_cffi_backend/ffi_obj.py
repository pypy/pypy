from pypy.interpreter.error import oefmt
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.interpreter.gateway import interp2app, unwrap_spec, WrappedDefault
from rpython.rlib import jit, rgc

from pypy.module._cffi_backend import parse_c_type, realize_c_type
from pypy.module._cffi_backend import newtype, cerrno, ccallback
from pypy.module._cffi_backend.ctypeobj import W_CType
from pypy.module._cffi_backend.cdataobj import W_CData


ACCEPT_STRING   = 1
ACCEPT_CTYPE    = 2
ACCEPT_CDATA    = 4
ACCEPT_ALL      = ACCEPT_STRING | ACCEPT_CTYPE | ACCEPT_CDATA
CONSIDER_FN_AS_FNPTR  = 8


class W_FFIObject(W_Root):

    def __init__(self, space, src_ctx=parse_c_type.NULL_CTX):
        self.space = space
        self.types_dict = {}
        self.ctxobj = parse_c_type.allocate_ctxobj(src_ctx)
        if src_ctx:
            self.cached_types = [None] * parse_c_type.get_num_types(src_ctx)
        else:
            self.cached_types = None
        w_ffitype = space.gettypefor(W_FFIObject)
        self.w_FFIError = w_ffitype.getdictvalue(space, 'error')

    @rgc.must_be_light_finalizer
    def __del__(self):
        parse_c_type.free_ctxobj(self.ctxobj)

    @jit.elidable
    def parse_string_to_type(self, string, flags):
        try:
            x = self.types_dict[string]
        except KeyError:
            index = parse_c_type.parse_c_type(self.ctxobj.info, string)
            if index < 0:
                xxxx
            x = realize_c_type.realize_c_type_or_func(
                self, self.ctxobj.info.c_output, index)
            self.types_dict[string] = x

        if isinstance(x, W_CType):
            return x
        elif flags & CONSIDER_FN_AS_FNPTR:
            return realize_c_type.unwrap_fn_as_fnptr(x)
        else:
            return realize_c_type.unexpected_fn_type(self, x)

    def ffi_type(self, w_x, accept):
        space = self.space
        if (accept & ACCEPT_STRING) and space.isinstance_w(w_x, space.w_str):
            return self.parse_string_to_type(space.str_w(w_x),
                                             accept & CONSIDER_FN_AS_FNPTR)
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


    def descr_init(self):
        pass       # if any argument is passed, gets a TypeError


    doc_errno = "the value of 'errno' from/to the C calls"

    def get_errno(self, space):
        return cerrno.get_errno(space)

    def set_errno(self, space, errno):
        cerrno.set_errno(space, space.c_int_w(errno))


    def descr_alignof(self, w_arg):
        """\
Return the natural alignment size in bytes of the argument.
It can be a string naming a C type, or a 'cdata' instance."""
        #
        w_ctype = self.ffi_type(w_arg, ACCEPT_ALL)
        align = w_ctype.alignof()
        return self.space.wrap(align)


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
        return self.ffi_type(w_arg, ACCEPT_STRING | ACCEPT_CDATA)


def W_FFIObject___new__(space, w_subtype, __args__):
    r = space.allocate_instance(W_FFIObject, w_subtype)
    r.__init__(space)
    return space.wrap(r)

W_FFIObject.typedef = TypeDef(
        'CompiledFFI',
        __new__     = interp2app(W_FFIObject___new__),
        __init__    = interp2app(W_FFIObject.descr_init),
        errno       = GetSetProperty(W_FFIObject.get_errno,
                                     W_FFIObject.set_errno,
                                     doc=W_FFIObject.doc_errno,
                                     cls=W_FFIObject),
        alignof     = interp2app(W_FFIObject.descr_alignof),
        callback    = interp2app(W_FFIObject.descr_callback),
        new         = interp2app(W_FFIObject.descr_new),
        sizeof      = interp2app(W_FFIObject.descr_sizeof),
        string      = interp2app(W_FFIObject.descr_string),
        typeof      = interp2app(W_FFIObject.descr_typeof),
        )

def _startup(space):
    ctvoidp = newtype.new_pointer_type(space, newtype.new_void_type(space))
    w_NULL = ctvoidp.cast(space.wrap(0))
    w_ffitype = space.gettypefor(W_FFIObject)
    w_ffitype.dict_w['NULL'] = w_NULL
    w_ffitype.dict_w['error'] = space.appexec([], """():
        return type('error', (Exception,), {'__module__': 'ffi'})""")
