"""
Struct and unions.
"""

from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef, interp_attrproperty
from pypy.rlib.objectmodel import keepalive_until_here

from pypy.module._cffi_backend.ctypeobj import W_CType
from pypy.module._cffi_backend import cdataobj


class W_CTypeStructOrUnion(W_CType):
    # fields added by complete_struct_or_union():
    alignment = -1
    fields_list = None
    fields_dict = None
    custom_field_pos = False

    def __init__(self, space, name):
        name = '%s %s' % (self.kind, name)
        W_CType.__init__(self, space, -1, name, len(name))

    def check_complete(self):
        if self.fields_dict is None:
            space = self.space
            raise operationerrfmt(space.w_TypeError,
                                  "'%s' is not completed yet", self.name)

    def _alignof(self):
        self.check_complete()
        return self.alignment

    def _getfields(self):
        if self.size < 0:
            return None
        space = self.space
        result = [None] * len(self.fields_list)
        for fname, field in self.fields_dict.iteritems():
            i = self.fields_list.index(field)
            result[i] = space.newtuple([space.wrap(fname),
                                        space.wrap(field)])
        return space.newlist(result)

    def convert_to_object(self, cdata):
        space = self.space
        self.check_complete()
        return cdataobj.W_CData(space, cdata, self)

    def copy_and_convert_to_object(self, cdata):
        space = self.space
        self.check_complete()
        ob = cdataobj.W_CDataNewOwning(space, self.size, self)
        # push push push at the llmemory interface (with hacks that
        # are all removed after translation)
        zero = llmemory.itemoffsetof(rffi.CCHARP.TO, 0)
        llmemory.raw_memcopy(
            llmemory.cast_ptr_to_adr(cdata) + zero,
            llmemory.cast_ptr_to_adr(ob._cdata) + zero,
            self.size * llmemory.sizeof(lltype.Char))
        return ob

    def offsetof(self, fieldname):
        self.check_complete()
        try:
            cfield = self.fields_dict[fieldname]
        except KeyError:
            space = self.space
            raise OperationError(space.w_KeyError, space.wrap(fieldname))
        return cfield.offset

    def _copy_from_same(self, cdata, w_ob):
        space = self.space
        ob = space.interpclass_w(w_ob)
        if isinstance(ob, cdataobj.W_CData):
            if ob.ctype is self and self.size >= 0:
                # push push push at the llmemory interface (with hacks that
                # are all removed after translation)
                zero = llmemory.itemoffsetof(rffi.CCHARP.TO, 0)
                llmemory.raw_memcopy(
                    llmemory.cast_ptr_to_adr(ob._cdata) + zero,
                    llmemory.cast_ptr_to_adr(cdata) + zero,
                    self.size * llmemory.sizeof(lltype.Char))
                keepalive_until_here(ob)
                return True
        return False

    def _check_only_one_argument_for_union(self, w_ob):
        pass

    def convert_from_object(self, cdata, w_ob):
        space = self.space
        if self._copy_from_same(cdata, w_ob):
            return

        self._check_only_one_argument_for_union(w_ob)

        if (space.isinstance_w(w_ob, space.w_list) or
            space.isinstance_w(w_ob, space.w_tuple)):
            lst_w = space.listview(w_ob)
            if len(lst_w) > len(self.fields_list):
                raise operationerrfmt(space.w_ValueError,
                        "too many initializers for '%s' (got %d)",
                                      self.name, len(lst_w))
            for i in range(len(lst_w)):
                self.fields_list[i].write(cdata, lst_w[i])

        elif space.isinstance_w(w_ob, space.w_dict):
            lst_w = space.fixedview(w_ob)
            for i in range(len(lst_w)):
                w_key = lst_w[i]
                key = space.str_w(w_key)
                try:
                    cf = self.fields_dict[key]
                except KeyError:
                    space.raise_key_error(w_key)
                    assert 0
                cf.write(cdata, space.getitem(w_ob, w_key))

        else:
            raise self._convert_error("list or tuple or dict or struct-cdata",
                                      w_ob)


class W_CTypeStruct(W_CTypeStructOrUnion):
    kind = "struct"

class W_CTypeUnion(W_CTypeStructOrUnion):
    kind = "union"

    def _check_only_one_argument_for_union(self, w_ob):
        space = self.space
        if space.int_w(space.len(w_ob)) > 1:
            raise operationerrfmt(space.w_ValueError,
                                  "initializer for '%s': %d items given, but "
                                  "only one supported (use a dict if needed)",
                                  self.name, n)


class W_CField(Wrappable):
    _immutable_ = True
    def __init__(self, ctype, offset, bitshift, bitsize):
        self.ctype = ctype
        self.offset = offset
        self.bitshift = bitshift
        self.bitsize = bitsize

    def is_bitfield(self):
        return self.bitshift >= 0

    def read(self, cdata):
        cdata = rffi.ptradd(cdata, self.offset)
        if self.is_bitfield():
            xxx
        else:
            return self.ctype.convert_to_object(cdata)

    def write(self, cdata, w_ob):
        cdata = rffi.ptradd(cdata, self.offset)
        if self.is_bitfield():
            xxx
        else:
            self.ctype.convert_from_object(cdata, w_ob)



W_CField.typedef = TypeDef(
    '_cffi_backend.CField',
    type = interp_attrproperty('ctype', W_CField),
    offset = interp_attrproperty('offset', W_CField),
    bitshift = interp_attrproperty('bitshift', W_CField),
    bitsize = interp_attrproperty('bitsize', W_CField),
    )
W_CField.typedef.acceptable_as_base_class = False
