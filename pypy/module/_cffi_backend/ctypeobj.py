from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.typedef import make_weakref_descr
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.rlib.objectmodel import we_are_translated

from pypy.module._cffi_backend import cdataobj


class W_CType(Wrappable):
    _attrs_   = ['space', 'size',  'name', 'name_position', '_lifeline_']
    _immutable_fields_ = ['size?', 'name', 'name_position']
    # note that 'size' is not strictly immutable, because it can change
    # from -1 to the real value in the W_CTypeStruct subclass.

    cast_anything = False
    is_primitive_integer = False

    def __init__(self, space, size, name, name_position):
        self.space = space
        self.size = size     # size of instances, or -1 if unknown
        self.name = name     # the name of the C type as a string
        self.name_position = name_position
        # 'name_position' is the index in 'name' where it must be extended,
        # e.g. with a '*' or a variable name.

    def repr(self):
        space = self.space
        return space.wrap("<ctype '%s'>" % (self.name,))

    def extra_repr(self, cdata):
        if cdata:
            return '0x%x' % rffi.cast(lltype.Unsigned, cdata)
        else:
            return 'NULL'

    def is_char_ptr_or_array(self):
        return False

    def is_unichar_ptr_or_array(self):
        return False

    def newp(self, w_init):
        space = self.space
        raise operationerrfmt(space.w_TypeError,
                              "expected a pointer or array ctype, got '%s'",
                              self.name)

    def cast(self, w_ob):
        space = self.space
        raise operationerrfmt(space.w_TypeError,
                              "cannot cast to '%s'", self.name)

    def int(self, cdata):
        space = self.space
        raise operationerrfmt(space.w_TypeError,
                              "int() not supported on cdata '%s'", self.name)

    def float(self, cdata):
        space = self.space
        raise operationerrfmt(space.w_TypeError,
                              "float() not supported on cdata '%s'", self.name)

    def convert_to_object(self, cdata):
        space = self.space
        raise operationerrfmt(space.w_TypeError,
                              "cannot return a cdata '%s'", self.name)

    def convert_from_object(self, cdata, w_ob):
        space = self.space
        raise operationerrfmt(space.w_TypeError,
                              "cannot initialize cdata '%s'", self.name)

    def convert_argument_from_object(self, cdata, w_ob):
        self.convert_from_object(cdata, w_ob)
        return False

    def _convert_error(self, expected, w_got):
        space = self.space
        ob = space.interpclass_w(w_got)
        if isinstance(ob, cdataobj.W_CData):
            return operationerrfmt(space.w_TypeError,
                                   "initializer for ctype '%s' must be a %s, "
                                   "not cdata '%s'", self.name, expected,
                                   ob.ctype.name)
        else:
            return operationerrfmt(space.w_TypeError,
                                   "initializer for ctype '%s' must be a %s, "
                                   "not %s", self.name, expected,
                                   space.type(w_got).getname(space))

    def _check_subscript_index(self, w_cdata, i):
        space = self.space
        raise operationerrfmt(space.w_TypeError,
                              "cdata of type '%s' cannot be indexed",
                              self.name)

    def string(self, cdataobj, maxlen):
        space = self.space
        raise operationerrfmt(space.w_TypeError,
                              "string(): unexpected cdata '%s' argument",
                              self.name)

    def add(self, cdata, i):
        space = self.space
        raise operationerrfmt(space.w_TypeError,
                              "cannot add a cdata '%s' and a number",
                              self.name)

    def insert_name(self, extra, extra_position):
        name = '%s%s%s' % (self.name[:self.name_position],
                           extra,
                           self.name[self.name_position:])
        name_position = self.name_position + extra_position
        return name, name_position

    def alignof(self):
        align = self._alignof()
        if not we_are_translated():
            # obscure hack when untranslated, maybe, approximate, don't use
            if isinstance(align, llmemory.FieldOffset):
                align = rffi.sizeof(align.TYPE.y)
        else:
            # a different hack when translated, to avoid seeing constants
            # of a symbolic integer type
            align = llmemory.raw_malloc_usage(align)
        return align

    def _alignof(self):
        space = self.space
        raise operationerrfmt(space.w_TypeError,
                              "ctype '%s' is of unknown alignment",
                              self.name)

    def typeoffsetof(self, fieldname):
        space = self.space
        if fieldname is None:
            msg = "expected a struct or union ctype"
        else:
            msg = "expected a struct or union ctype, or a pointer to one"
        raise OperationError(space.w_TypeError, space.wrap(msg))

    def _getfields(self):
        return None

    def rawaddressof(self, cdata, offset):
        space = self.space
        raise OperationError(space.w_TypeError,
                             space.wrap("expected a pointer ctype"))

    def call(self, funcaddr, args_w):
        space = self.space
        raise operationerrfmt(space.w_TypeError,
                              "cdata '%s' is not callable", self.name)

    def iter(self, cdata):
        space = self.space
        raise operationerrfmt(space.w_TypeError,
                              "cdata '%s' does not support iteration",
                              self.name)

    def get_vararg_type(self):
        return self

    def getcfield(self, attr):
        space = self.space
        raise operationerrfmt(space.w_AttributeError,
                              "cdata '%s' has no attribute '%s'",
                              self.name, attr)

    def copy_and_convert_to_object(self, cdata):
        return self.convert_to_object(cdata)


W_CType.typedef = TypeDef(
    'CTypeDescr',
    __module__ = '_cffi_backend',
    __repr__ = interp2app(W_CType.repr),
    __weakref__ = make_weakref_descr(W_CType),
    )
W_CType.typedef.acceptable_as_base_class = False
