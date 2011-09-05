from pypy.rlib import libffi
from pypy.rlib.rarithmetic import intmask
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app

class W_FFIType(Wrappable):

    _immutable_fields_ = ['name', 'ffitype', 'w_datashape', 'w_pointer_to']

    def __init__(self, name, ffitype, w_datashape=None, w_pointer_to=None):
        self.name = name
        self.ffitype = ffitype
        self.w_datashape = w_datashape
        self.w_pointer_to = w_pointer_to
        if self.is_struct():
            assert w_datashape is not None

    def descr_deref_pointer(self, space):
        if self.w_pointer_to is None:
            return space.w_None
        return self.w_pointer_to

    def descr_sizeof(self, space):
        return space.wrap(self.sizeof())

    def sizeof(self):
        return intmask(self.ffitype.c_size)

    def repr(self, space):
        return space.wrap(self.__repr__())

    def __repr__(self):
        return "<ffi type %s>" % self.name

    def is_signed(self):
        return (self is app_types.slong or
                self is app_types.sint or
                self is app_types.sshort or
                self is app_types.sbyte or
                self is app_types.slonglong)

    def is_unsigned(self):
        return (self is app_types.ulong or
                self is app_types.uint or
                self is app_types.ushort or
                self is app_types.ubyte or
                self is app_types.ulonglong)

    def is_pointer(self):
        return self.ffitype is libffi.types.pointer

    def is_char(self):
        return self is app_types.char

    def is_unichar(self):
        return self is app_types.unichar

    def is_longlong(self):
        return libffi.IS_32_BIT and (self is app_types.slonglong or
                                     self is app_types.ulonglong)

    def is_double(self):
        return self is app_types.double

    def is_singlefloat(self):
        return self is app_types.float

    def is_void(self):
        return self is app_types.void

    def is_struct(self):
        return libffi.types.is_struct(self.ffitype)

    def is_char_p(self):
        return self is app_types.char_p

    def is_unichar_p(self):
        return self is app_types.unichar_p


W_FFIType.typedef = TypeDef(
    'FFIType',
    __repr__ = interp2app(W_FFIType.repr),
    deref_pointer = interp2app(W_FFIType.descr_deref_pointer),
    sizeof = interp2app(W_FFIType.descr_sizeof),
    )


def build_ffi_types():
    types = [
        # note: most of the type name directly come from the C equivalent,
        # with the exception of bytes: in C, ubyte and char are equivalent,
        # but for _ffi the first expects a number while the second a 1-length
        # string
        W_FFIType('slong',     libffi.types.slong),
        W_FFIType('sint',      libffi.types.sint),
        W_FFIType('sshort',    libffi.types.sshort),
        W_FFIType('sbyte',     libffi.types.schar),
        W_FFIType('slonglong', libffi.types.slonglong),
        #
        W_FFIType('ulong',     libffi.types.ulong),
        W_FFIType('uint',      libffi.types.uint),
        W_FFIType('ushort',    libffi.types.ushort),
        W_FFIType('ubyte',     libffi.types.uchar),
        W_FFIType('ulonglong', libffi.types.ulonglong),
        #
        W_FFIType('char',      libffi.types.uchar),
        W_FFIType('unichar',   libffi.types.wchar_t),
        #
        W_FFIType('double',    libffi.types.double),
        W_FFIType('float',     libffi.types.float),
        W_FFIType('void',      libffi.types.void),
        W_FFIType('void_p',    libffi.types.pointer),
        #
        # missing types:

        ## 's' : ffi_type_pointer,
        ## 'z' : ffi_type_pointer,
        ## 'O' : ffi_type_pointer,
        ## 'Z' : ffi_type_pointer,

        ]
    d = dict([(t.name, t) for t in types])
    w_char = d['char']
    w_unichar = d['unichar']
    d['char_p'] = W_FFIType('char_p', libffi.types.pointer, w_pointer_to = w_char)
    d['unichar_p'] = W_FFIType('unichar_p', libffi.types.pointer, w_pointer_to = w_unichar)
    return d

class app_types:
    pass
app_types.__dict__ = build_ffi_types()

def descr_new_pointer(space, w_cls, w_pointer_to):
    try:
        return descr_new_pointer.cache[w_pointer_to]
    except KeyError:
        if w_pointer_to is app_types.char:
            w_result = app_types.char_p
        elif w_pointer_to is app_types.unichar:
            w_result = app_types.unichar_p
        else:
            w_pointer_to = space.interp_w(W_FFIType, w_pointer_to)
            name = '(pointer to %s)' % w_pointer_to.name
            w_result = W_FFIType(name, libffi.types.pointer, w_pointer_to = w_pointer_to)
        descr_new_pointer.cache[w_pointer_to] = w_result
        return w_result
descr_new_pointer.cache = {}

class W_types(Wrappable):
    pass
W_types.typedef = TypeDef(
    'types',
    Pointer = interp2app(descr_new_pointer, as_classmethod=True),
    **app_types.__dict__)
