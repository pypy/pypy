from pypy.interpreter.error import oefmt
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef, GetSetProperty, ClassAttr
from pypy.interpreter.gateway import interp2app, unwrap_spec, WrappedDefault
from rpython.rlib import jit, rgc
from rpython.rtyper.lltypesystem import rffi

from pypy.module._cffi_backend import parse_c_type, realize_c_type
from pypy.module._cffi_backend import newtype, cerrno, ccallback, ctypearray
from pypy.module._cffi_backend import ctypestruct, ctypeptr, handle
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
            self = jit.promote(self)
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


    def _more_addressof(self, args_w, w_ctype):
        # contains a loop, the JIT doesn't look inside this helper
        offset = 0
        for i in range(len(args_w)):
            w_ctype, ofs1 = w_ctype.direct_typeoffsetof(args_w[i], i > 0)
            offset += ofs1
        return w_ctype, offset

    def descr_addressof(self, w_arg, args_w):
        """\
With a single arg, return the address of a <cdata 'struct-or-union'>.
If 'fields_or_indexes' are given, returns the address of that field or
array item in the structure or array, recursively in case of nested
structures."""
        #
        w_ctype = self.ffi_type(w_arg, ACCEPT_CDATA)
        space = self.space
        if len(args_w) == 0:
            if (not isinstance(w_ctype, ctypestruct.W_CTypeStructOrUnion) and
                not isinstance(w_ctype, ctypearray.W_CTypeArray)):
                raise oefmt(space.w_TypeError,
                            "expected a cdata struct/union/array object")
            offset = 0
        else:
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


    @unwrap_spec(w_arg=W_CData)
    def descr_from_handle(self, w_arg):
        """\
Cast a 'void *' back to a Python object.  Must be used *only* on the
pointers returned by new_handle(), and *only* as long as the exact
cdata object returned by new_handle() is still alive (somewhere else
in the program).  Failure to follow these rules will crash."""
        #
        return handle.from_handle(self.space, w_arg)


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
        return self.space.wrap(result)


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
        return handle._newp_handle(space, newtype.new_voidp_type(space), w_arg)


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
        return self.ffi_type(w_arg, ACCEPT_STRING | ACCEPT_CDATA)


def W_FFIObject___new__(space, w_subtype, __args__):
    r = space.allocate_instance(W_FFIObject, w_subtype)
    r.__init__(space)
    return space.wrap(r)

def make_NULL(space):
    ctvoidp = newtype.new_voidp_type(space)
    w_NULL = ctvoidp.cast(space.wrap(0))
    return w_NULL

def make_error(space):
    return space.appexec([], """():
        return type('error', (Exception,), {'__module__': 'ffi'})""")

W_FFIObject.typedef = TypeDef(
        'CompiledFFI',
        __new__     = interp2app(W_FFIObject___new__),
        __init__    = interp2app(W_FFIObject.descr_init),
        NULL        = ClassAttr(make_NULL),
        error       = ClassAttr(make_error),
        errno       = GetSetProperty(W_FFIObject.get_errno,
                                     W_FFIObject.set_errno,
                                     doc=W_FFIObject.doc_errno,
                                     cls=W_FFIObject),
        addressof   = interp2app(W_FFIObject.descr_addressof),
        alignof     = interp2app(W_FFIObject.descr_alignof),
        callback    = interp2app(W_FFIObject.descr_callback),
        cast        = interp2app(W_FFIObject.descr_cast),
        from_handle = interp2app(W_FFIObject.descr_from_handle),
        getctype    = interp2app(W_FFIObject.descr_getctype),
        new         = interp2app(W_FFIObject.descr_new),
        new_handle  = interp2app(W_FFIObject.descr_new_handle),
        offsetof    = interp2app(W_FFIObject.descr_offsetof),
        sizeof      = interp2app(W_FFIObject.descr_sizeof),
        string      = interp2app(W_FFIObject.descr_string),
        typeof      = interp2app(W_FFIObject.descr_typeof),
        )
