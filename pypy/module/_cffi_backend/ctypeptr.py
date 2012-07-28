"""
Pointers.
"""

from pypy.interpreter.error import operationerrfmt
from pypy.rpython.lltypesystem import rffi
from pypy.rlib.objectmodel import keepalive_until_here

from pypy.module._cffi_backend.ctypeobj import W_CType
from pypy.module._cffi_backend import cdataobj, misc


class W_CTypePtrOrArray(W_CType):
    _immutable_ = True

    def __init__(self, space, size, extra, extra_position, ctitem,
                 could_cast_anything=True):
        from pypy.module._cffi_backend.ctypestruct import W_CTypeStructOrUnion
        name, name_position = ctitem.insert_name(extra, extra_position)
        W_CType.__init__(self, space, size, name, name_position)
        # this is the "underlying type":
        #  - for pointers, it is the pointed-to type
        #  - for arrays, it is the array item type
        #  - for functions, it is the return type
        self.ctitem = ctitem
        self.can_cast_anything = could_cast_anything and ctitem.cast_anything
        self.is_struct_ptr = isinstance(ctitem, W_CTypeStructOrUnion)

    def is_char_ptr_or_array(self):
        from pypy.module._cffi_backend import ctypeprim
        return isinstance(self.ctitem, ctypeprim.W_CTypePrimitiveChar)

    def is_unichar_ptr_or_array(self):
        from pypy.module._cffi_backend import ctypeprim
        return isinstance(self.ctitem, ctypeprim.W_CTypePrimitiveUniChar)

    def is_char_or_unichar_ptr_or_array(self):
        from pypy.module._cffi_backend import ctypeprim
        return isinstance(self.ctitem, ctypeprim.W_CTypePrimitiveCharOrUniChar)

    def cast(self, w_ob):
        # cast to a pointer, to a funcptr, or to an array.
        # Note that casting to an array is an extension to the C language,
        # which seems to be necessary in order to sanely get a
        # <cdata 'int[3]'> at some address.
        if self.size < 0:
            return W_CType.cast(self, w_ob)
        space = self.space
        ob = space.interpclass_w(w_ob)
        if (isinstance(ob, cdataobj.W_CData) and
                isinstance(ob.ctype, W_CTypePtrOrArray)):
            value = ob._cdata
        else:
            value = misc.as_unsigned_long_long(space, w_ob, strict=False)
            value = rffi.cast(rffi.CCHARP, value)
        return cdataobj.W_CData(space, value, self)


class W_CTypePtrBase(W_CTypePtrOrArray):
    # base class for both pointers and pointers-to-functions
    _immutable_ = True

    def convert_to_object(self, cdata):
        ptrdata = rffi.cast(rffi.CCHARPP, cdata)[0]
        return cdataobj.W_CData(self.space, ptrdata, self)

    def convert_from_object(self, cdata, w_ob):
        space = self.space
        ob = space.interpclass_w(w_ob)
        if not isinstance(ob, cdataobj.W_CData):
            raise self._convert_error("compatible pointer", w_ob)
        other = ob.ctype
        if not isinstance(other, W_CTypePtrBase):
            from pypy.module._cffi_backend import ctypearray
            if isinstance(other, ctypearray.W_CTypeArray):
                other = other.ctptr
            else:
                raise self._convert_error("compatible pointer", w_ob)
        if self is not other:
            if not (self.can_cast_anything or other.can_cast_anything):
                raise self._convert_error("compatible pointer", w_ob)

        rffi.cast(rffi.CCHARPP, cdata)[0] = ob._cdata

    def _alignof(self):
        from pypy.module._cffi_backend import newtype
        return newtype.alignment_of_pointer


class W_CTypePointer(W_CTypePtrBase):
    _immutable_ = True

    def __init__(self, space, ctitem):
        from pypy.module._cffi_backend import ctypearray
        size = rffi.sizeof(rffi.VOIDP)
        if isinstance(ctitem, ctypearray.W_CTypeArray):
            extra = "(*)"    # obscure case: see test_array_add
        else:
            extra = " *"
        W_CTypePtrBase.__init__(self, space, size, extra, 2, ctitem)

    def str(self, cdataobj):
        if self.is_char_ptr_or_array():
            if not cdataobj._cdata:
                space = self.space
                raise operationerrfmt(space.w_RuntimeError,
                                      "cannot use str() on %s",
                                      space.str_w(cdataobj.repr()))
            s = rffi.charp2str(cdataobj._cdata)
            keepalive_until_here(cdataobj)
            return self.space.wrap(s)
        return W_CTypePtrOrArray.str(self, cdataobj)

    def unicode(self, cdataobj):
        if self.is_unichar_ptr_or_array():
            if not cdataobj._cdata:
                space = self.space
                raise operationerrfmt(space.w_RuntimeError,
                                      "cannot use unicode() on %s",
                                      space.str_w(cdataobj.repr()))
            s = rffi.wcharp2unicode(rffi.cast(rffi.CWCHARP, cdataobj._cdata))
            keepalive_until_here(cdataobj)
            return self.space.wrap(s)
        return W_CTypePtrOrArray.unicode(self, cdataobj)

    def newp(self, w_init):
        from pypy.module._cffi_backend import ctypeprim
        space = self.space
        ctitem = self.ctitem
        datasize = ctitem.size
        if datasize < 0:
            raise operationerrfmt(space.w_TypeError,
                "cannot instantiate ctype '%s' of unknown size",
                                  self.name)
        if self.is_struct_ptr:
            # 'newp' on a struct-or-union pointer: in this case, we return
            # a W_CDataPtrToStruct object which has a strong reference
            # to a W_CDataNewOwning that really contains the structure.
            cdatastruct = cdataobj.W_CDataNewOwning(space, datasize, ctitem)
            cdata = cdataobj.W_CDataPtrToStructOrUnion(space,
                                                       cdatastruct._cdata,
                                                       self, cdatastruct)
        else:
            if self.is_char_or_unichar_ptr_or_array():
                datasize *= 2       # forcefully add a null character
            cdata = cdataobj.W_CDataNewOwning(space, datasize, self)
        #
        if not space.is_w(w_init, space.w_None):
            ctitem.convert_from_object(cdata._cdata, w_init)
            keepalive_until_here(cdata)
        return cdata

    def _check_subscript_index(self, w_cdata, i):
        if isinstance(w_cdata, cdataobj.W_CDataApplevelOwning) and i != 0:
            space = self.space
            raise operationerrfmt(space.w_IndexError,
                                  "cdata '%s' can only be indexed by 0",
                                  self.name)
        return self

    def add(self, cdata, i):
        space = self.space
        ctitem = self.ctitem
        if ctitem.size < 0:
            raise operationerrfmt(space.w_TypeError,
                                  "ctype '%s' points to items of unknown size",
                                  self.name)
        p = rffi.ptradd(cdata, i * self.ctitem.size)
        return cdataobj.W_CData(space, p, self)
