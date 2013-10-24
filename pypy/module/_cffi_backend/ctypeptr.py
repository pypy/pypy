"""
Pointers.
"""

from pypy.interpreter.error import OperationError, operationerrfmt, wrap_oserror

from rpython.rlib import rposix
from rpython.rlib.objectmodel import keepalive_until_here
from rpython.rlib.rarithmetic import ovfcheck
from rpython.rtyper.lltypesystem import lltype, rffi

from pypy.module._cffi_backend import cdataobj, misc, ctypeprim, ctypevoid
from pypy.module._cffi_backend.ctypeobj import W_CType


class W_CTypePtrOrArray(W_CType):
    _attrs_            = ['ctitem', 'can_cast_anything', 'is_struct_ptr',
                          'length']
    _immutable_fields_ = ['ctitem', 'can_cast_anything', 'is_struct_ptr',
                          'length']
    length = -1

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
        return isinstance(self.ctitem, ctypeprim.W_CTypePrimitiveChar)

    def is_unichar_ptr_or_array(self):
        return isinstance(self.ctitem, ctypeprim.W_CTypePrimitiveUniChar)

    def is_char_or_unichar_ptr_or_array(self):
        return isinstance(self.ctitem, ctypeprim.W_CTypePrimitiveCharOrUniChar)

    def aslist_int(self, cdata):
        return None

    def aslist_float(self, cdata):
        return None

    def cast(self, w_ob):
        # cast to a pointer, to a funcptr, or to an array.
        # Note that casting to an array is an extension to the C language,
        # which seems to be necessary in order to sanely get a
        # <cdata 'int[3]'> at some address.
        if self.size < 0:
            return W_CType.cast(self, w_ob)
        space = self.space
        if (isinstance(w_ob, cdataobj.W_CData) and
                isinstance(w_ob.ctype, W_CTypePtrOrArray)):
            value = w_ob._cdata
        else:
            value = misc.as_unsigned_long(space, w_ob, strict=False)
            value = rffi.cast(rffi.CCHARP, value)
        return cdataobj.W_CData(space, value, self)

    def _convert_array_from_list_strategy_maybe(self, cdata, w_ob):
        from rpython.rlib.rarray import copy_list_to_raw_array
        int_list = self.space.listview_int(w_ob)
        float_list = self.space.listview_float(w_ob)
        #
        if self.ctitem.is_long() and int_list is not None:
            cdata = rffi.cast(rffi.LONGP, cdata)
            copy_list_to_raw_array(int_list, cdata)
            return True
        #
        if self.ctitem.is_double() and float_list is not None:
            cdata = rffi.cast(rffi.DOUBLEP, cdata)
            copy_list_to_raw_array(float_list, cdata)
            return True
        #
        return False

    def _convert_array_from_listview(self, cdata, w_ob):
        space = self.space
        lst_w = space.listview(w_ob)
        if self.length >= 0 and len(lst_w) > self.length:
            raise operationerrfmt(space.w_IndexError,
                "too many initializers for '%s' (got %d)",
                                  self.name, len(lst_w))
        ctitem = self.ctitem
        for i in range(len(lst_w)):
            ctitem.convert_from_object(cdata, lst_w[i])
            cdata = rffi.ptradd(cdata, ctitem.size)

    def convert_array_from_object(self, cdata, w_ob):
        space = self.space
        if (space.isinstance_w(w_ob, space.w_list) or
            space.isinstance_w(w_ob, space.w_tuple)):
            #
            if not self._convert_array_from_list_strategy_maybe(cdata, w_ob):
                # continue with the slow path
                self._convert_array_from_listview(cdata, w_ob)
            #
        elif (self.can_cast_anything or
              (self.ctitem.is_primitive_integer and
               self.ctitem.size == rffi.sizeof(lltype.Char))):
            if not space.isinstance_w(w_ob, space.w_str):
                raise self._convert_error("str or list or tuple", w_ob)
            s = space.str_w(w_ob)
            n = len(s)
            if self.length >= 0 and n > self.length:
                raise operationerrfmt(space.w_IndexError,
                                      "initializer string is too long for '%s'"
                                      " (got %d characters)",
                                      self.name, n)
            for i in range(n):
                cdata[i] = s[i]
            if n != self.length:
                cdata[n] = '\x00'
        elif isinstance(self.ctitem, ctypeprim.W_CTypePrimitiveUniChar):
            if not space.isinstance_w(w_ob, space.w_unicode):
                raise self._convert_error("unicode or list or tuple", w_ob)
            s = space.unicode_w(w_ob)
            n = len(s)
            if self.length >= 0 and n > self.length:
                raise operationerrfmt(space.w_IndexError,
                              "initializer unicode string is too long for '%s'"
                                      " (got %d characters)",
                                      self.name, n)
            unichardata = rffi.cast(rffi.CWCHARP, cdata)
            for i in range(n):
                unichardata[i] = s[i]
            if n != self.length:
                unichardata[n] = u'\x00'
        else:
            raise self._convert_error("list or tuple", w_ob)

    def string(self, cdataobj, maxlen):
        space = self.space
        if isinstance(self.ctitem, ctypeprim.W_CTypePrimitive):
            cdata = cdataobj._cdata
            if not cdata:
                raise operationerrfmt(space.w_RuntimeError,
                                      "cannot use string() on %s",
                                      space.str_w(cdataobj.repr()))
            #
            from pypy.module._cffi_backend import ctypearray
            length = maxlen
            if length < 0 and isinstance(self, ctypearray.W_CTypeArray):
                length = cdataobj.get_array_length()
            #
            # pointer to a primitive type of size 1: builds and returns a str
            if self.ctitem.size == rffi.sizeof(lltype.Char):
                if length < 0:
                    s = rffi.charp2str(cdata)
                else:
                    s = rffi.charp2strn(cdata, length)
                keepalive_until_here(cdataobj)
                return space.wrap(s)
            #
            # pointer to a wchar_t: builds and returns a unicode
            if self.is_unichar_ptr_or_array():
                cdata = rffi.cast(rffi.CWCHARP, cdata)
                if length < 0:
                    u = rffi.wcharp2unicode(cdata)
                else:
                    u = rffi.wcharp2unicoden(cdata, length)
                keepalive_until_here(cdataobj)
                return space.wrap(u)
        #
        return W_CType.string(self, cdataobj, maxlen)


class W_CTypePtrBase(W_CTypePtrOrArray):
    # base class for both pointers and pointers-to-functions
    _attrs_ = []

    def convert_to_object(self, cdata):
        ptrdata = rffi.cast(rffi.CCHARPP, cdata)[0]
        return cdataobj.W_CData(self.space, ptrdata, self)

    def convert_from_object(self, cdata, w_ob):
        space = self.space
        if not isinstance(w_ob, cdataobj.W_CData):
            raise self._convert_error("cdata pointer", w_ob)
        other = w_ob.ctype
        if not isinstance(other, W_CTypePtrBase):
            from pypy.module._cffi_backend import ctypearray
            if isinstance(other, ctypearray.W_CTypeArray):
                other = other.ctptr
            else:
                raise self._convert_error("compatible pointer", w_ob)
        if self is not other:
            if not (self.can_cast_anything or other.can_cast_anything):
                raise self._convert_error("compatible pointer", w_ob)

        rffi.cast(rffi.CCHARPP, cdata)[0] = w_ob._cdata

    def _alignof(self):
        from pypy.module._cffi_backend import newtype
        return newtype.alignment_of_pointer


class W_CTypePointer(W_CTypePtrBase):
    _attrs_ = ['is_file', 'cache_array_type', 'is_void_ptr']
    _immutable_fields_ = ['is_file', 'cache_array_type?', 'is_void_ptr']
    kind = "pointer"
    cache_array_type = None

    def __init__(self, space, ctitem):
        from pypy.module._cffi_backend import ctypearray
        size = rffi.sizeof(rffi.VOIDP)
        if isinstance(ctitem, ctypearray.W_CTypeArray):
            extra = "(*)"    # obscure case: see test_array_add
        else:
            extra = " *"
        self.is_file = (ctitem.name == "struct _IO_FILE" or
                        ctitem.name == "FILE")
        self.is_void_ptr = isinstance(ctitem, ctypevoid.W_CTypeVoid)
        W_CTypePtrBase.__init__(self, space, size, extra, 2, ctitem)

    def newp(self, w_init):
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
        if (isinstance(w_cdata, cdataobj.W_CDataNewOwning) or
            isinstance(w_cdata, cdataobj.W_CDataPtrToStructOrUnion)):
            if i != 0:
                space = self.space
                raise operationerrfmt(space.w_IndexError,
                                      "cdata '%s' can only be indexed by 0",
                                      self.name)
        return self

    def _check_slice_index(self, w_cdata, start, stop):
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

    def cast(self, w_ob):
        if self.is_file:
            value = self.prepare_file(w_ob)
            if value:
                return cdataobj.W_CData(self.space, value, self)
        return W_CTypePtrBase.cast(self, w_ob)

    def prepare_file(self, w_ob):
        from pypy.module._file.interp_file import W_File
        if isinstance(w_ob, W_File):
            return prepare_file_argument(self.space, w_ob)
        else:
            return lltype.nullptr(rffi.CCHARP.TO)

    def _prepare_pointer_call_argument(self, w_init, cdata):
        space = self.space
        if (space.isinstance_w(w_init, space.w_list) or
            space.isinstance_w(w_init, space.w_tuple)):
            length = space.int_w(space.len(w_init))
        elif space.isinstance_w(w_init, space.w_basestring):
            # from a string, we add the null terminator
            length = space.int_w(space.len(w_init)) + 1
        elif self.is_file:
            result = self.prepare_file(w_init)
            if result:
                rffi.cast(rffi.CCHARPP, cdata)[0] = result
                return 2
            return 0
        else:
            return 0
        itemsize = self.ctitem.size
        if itemsize <= 0:
            if isinstance(self.ctitem, ctypevoid.W_CTypeVoid):
                itemsize = 1
            else:
                return 0
        try:
            datasize = ovfcheck(length * itemsize)
        except OverflowError:
            raise OperationError(space.w_OverflowError,
                space.wrap("array size would overflow a ssize_t"))
        result = lltype.malloc(rffi.CCHARP.TO, datasize,
                               flavor='raw', zero=True)
        try:
            self.convert_array_from_object(result, w_init)
        except Exception:
            lltype.free(result, flavor='raw')
            raise
        rffi.cast(rffi.CCHARPP, cdata)[0] = result
        return 1

    def convert_argument_from_object(self, cdata, w_ob):
        from pypy.module._cffi_backend.ctypefunc import set_mustfree_flag
        space = self.space
        result = (not isinstance(w_ob, cdataobj.W_CData) and
                  self._prepare_pointer_call_argument(w_ob, cdata))
        if result == 0:
            self.convert_from_object(cdata, w_ob)
        set_mustfree_flag(cdata, result)
        return result

    def getcfield(self, attr):
        return self.ctitem.getcfield(attr)

    def typeoffsetof(self, fieldname):
        if fieldname is None:
            return W_CTypePtrBase.typeoffsetof(self, fieldname)
        else:
            return self.ctitem.typeoffsetof(fieldname)

    def rawaddressof(self, cdata, offset):
        from pypy.module._cffi_backend.ctypestruct import W_CTypeStructOrUnion
        space = self.space
        ctype2 = cdata.ctype
        if (isinstance(ctype2, W_CTypeStructOrUnion) or
            (isinstance(ctype2, W_CTypePtrOrArray) and ctype2.is_struct_ptr)):
            ptrdata = rffi.ptradd(cdata._cdata, offset)
            return cdataobj.W_CData(space, ptrdata, self)
        else:
            raise OperationError(space.w_TypeError,
                     space.wrap("expected a 'cdata struct-or-union' object"))

    def _fget(self, attrchar):
        if attrchar == 'i':     # item
            return self.space.wrap(self.ctitem)
        return W_CTypePtrBase._fget(self, attrchar)

# ____________________________________________________________


rffi_fdopen = rffi.llexternal("fdopen", [rffi.INT, rffi.CCHARP], rffi.CCHARP)
rffi_setbuf = rffi.llexternal("setbuf", [rffi.CCHARP, rffi.CCHARP], lltype.Void)
rffi_fclose = rffi.llexternal("fclose", [rffi.CCHARP], rffi.INT)

class CffiFileObj(object):
    _immutable_ = True

    def __init__(self, fd, mode):
        self.llf = rffi_fdopen(fd, mode)
        if not self.llf:
            raise OSError(rposix.get_errno(), "fdopen failed")
        rffi_setbuf(self.llf, lltype.nullptr(rffi.CCHARP.TO))

    def close(self):
        rffi_fclose(self.llf)


def prepare_file_argument(space, fileobj):
    fileobj.direct_flush()
    if fileobj.cffi_fileobj is None:
        fd = fileobj.direct_fileno()
        if fd < 0:
            raise OperationError(space.w_ValueError,
                                 space.wrap("file has no OS file descriptor"))
        try:
            fileobj.cffi_fileobj = CffiFileObj(fd, fileobj.mode)
        except OSError, e:
            raise wrap_oserror(space, e)
    return fileobj.cffi_fileobj.llf
