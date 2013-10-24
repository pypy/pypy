from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef, make_weakref_descr, GetSetProperty

from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.rlib.objectmodel import we_are_translated

from pypy.module._cffi_backend import cdataobj


class W_CType(W_Root):
    _attrs_ = ['space', 'size',  'name', 'name_position', '_lifeline_']
    _immutable_fields_ = ['size?', 'name', 'name_position']
    # note that 'size' is not strictly immutable, because it can change
    # from -1 to the real value in the W_CTypeStruct subclass.

    cast_anything = False
    is_primitive_integer = False
    kind = "?"

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

    def is_long(self):
        return False

    def is_double(self):
        return False

    def aslist_int(self, w_ob):
        return None

    def aslist_float(self, w_ob):
        return None

    def newp(self, w_init):
        space = self.space
        raise operationerrfmt(space.w_TypeError,
                              "expected a pointer or array ctype, got '%s'",
                              self.name)

    def cast(self, w_ob):
        space = self.space
        raise operationerrfmt(space.w_TypeError,
                              "cannot cast to '%s'", self.name)

    def cast_to_int(self, cdata):
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
        if isinstance(w_got, cdataobj.W_CData):
            return operationerrfmt(space.w_TypeError,
                                   "initializer for ctype '%s' must be a %s, "
                                   "not cdata '%s'", self.name, expected,
                                   w_got.ctype.name)
        else:
            return operationerrfmt(space.w_TypeError,
                                   "initializer for ctype '%s' must be a %s, "
                                   "not %T", self.name, expected, w_got)

    def _cannot_index(self):
        space = self.space
        raise operationerrfmt(space.w_TypeError,
                              "cdata of type '%s' cannot be indexed",
                              self.name)

    def _check_subscript_index(self, w_cdata, i):
        raise self._cannot_index()

    def _check_slice_index(self, w_cdata, start, stop):
        raise self._cannot_index()

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
        raise operationerrfmt(space.w_ValueError,
                              "ctype '%s' is of unknown alignment",
                              self.name)

    def typeoffsetof(self, fieldname):
        space = self.space
        if fieldname is None:
            msg = "expected a struct or union ctype"
        else:
            msg = "expected a struct or union ctype, or a pointer to one"
        raise OperationError(space.w_TypeError, space.wrap(msg))

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

    def unpackiterable_int(self, cdata):
        return None

    def get_vararg_type(self):
        return self

    def getcfield(self, attr):
        space = self.space
        raise operationerrfmt(space.w_AttributeError,
                              "cdata '%s' has no attribute '%s'",
                              self.name, attr)

    def copy_and_convert_to_object(self, cdata):
        return self.convert_to_object(cdata)

    # __________ app-level attributes __________
    def dir(self):
        space = self.space
        w_self = space.wrap(self)
        lst = [space.wrap(name)
                  for name in _name_of_attributes
                  if space.findattr(w_self, space.wrap(name)) is not None]
        return space.newlist(lst)

    def _fget(self, attrchar):
        space = self.space
        if attrchar == 'k':     # kind
            return space.wrap(self.kind)      # class attribute
        if attrchar == 'c':     # cname
            return space.wrap(self.name)
        raise operationerrfmt(space.w_AttributeError,
                              "ctype '%s' has no such attribute",
                              self.name)

    def fget_kind(self, space):     return self._fget('k')
    def fget_cname(self, space):    return self._fget('c')
    def fget_item(self, space):     return self._fget('i')
    def fget_length(self, space):   return self._fget('l')
    def fget_fields(self, space):   return self._fget('f')
    def fget_args(self, space):     return self._fget('a')
    def fget_result(self, space):   return self._fget('r')
    def fget_ellipsis(self, space): return self._fget('E')
    def fget_abi(self, space):      return self._fget('A')
    def fget_elements(self, space): return self._fget('e')
    def fget_relements(self, space):return self._fget('R')


W_CType.typedef = TypeDef(
    'CTypeDescr',
    __module__ = '_cffi_backend',
    __repr__ = interp2app(W_CType.repr),
    __weakref__ = make_weakref_descr(W_CType),
    kind = GetSetProperty(W_CType.fget_kind, doc="kind"),
    cname = GetSetProperty(W_CType.fget_cname, doc="C name"),
    item = GetSetProperty(W_CType.fget_item, doc="pointer to, or array of"),
    length = GetSetProperty(W_CType.fget_length, doc="array length or None"),
    fields = GetSetProperty(W_CType.fget_fields, doc="struct or union fields"),
    args = GetSetProperty(W_CType.fget_args, doc="function argument types"),
    result = GetSetProperty(W_CType.fget_result, doc="function result type"),
    ellipsis = GetSetProperty(W_CType.fget_ellipsis, doc="function has '...'"),
    abi = GetSetProperty(W_CType.fget_abi, doc="function ABI"),
    elements = GetSetProperty(W_CType.fget_elements, doc="enum elements"),
    relements = GetSetProperty(W_CType.fget_relements,
                               doc="enum elements, reversed"),
    __dir__ = interp2app(W_CType.dir),
    )
W_CType.typedef.acceptable_as_base_class = False

_name_of_attributes = [name for name in W_CType.typedef.rawdict
                            if not name.startswith('_')]
_name_of_attributes.sort()
