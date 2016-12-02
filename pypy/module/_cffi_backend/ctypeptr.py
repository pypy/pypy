"""
Pointers.
"""

from rpython.rlib import rposix
from rpython.rlib.rarithmetic import ovfcheck
from rpython.rtyper.annlowlevel import llstr, llunicode
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rtyper.lltypesystem.rstr import copy_string_to_raw, copy_unicode_to_raw

from pypy.interpreter.error import OperationError, oefmt, wrap_oserror
from pypy.module._cffi_backend import cdataobj, misc, ctypeprim, ctypevoid
from pypy.module._cffi_backend.ctypeobj import W_CType


class W_CTypePtrOrArray(W_CType):
    _attrs_            = ['ctitem', 'accept_str', 'length']
    _immutable_fields_ = ['ctitem', 'accept_str', 'length']
    length = -1

    def __init__(self, space, size, extra, extra_position, ctitem):
        name, name_position = ctitem.insert_name(extra, extra_position)
        W_CType.__init__(self, space, size, name, name_position)
        # this is the "underlying type":
        #  - for pointers, it is the pointed-to type
        #  - for arrays, it is the array item type
        #  - for functions, it is the return type
        self.ctitem = ctitem
        self.accept_str = (self.is_nonfunc_pointer_or_array and
                (isinstance(ctitem, ctypevoid.W_CTypeVoid) or
                 isinstance(ctitem, ctypeprim.W_CTypePrimitiveChar) or
                 (ctitem.is_primitive_integer and
                  ctitem.size == rffi.sizeof(lltype.Char))))

    def is_unichar_ptr_or_array(self):
        return isinstance(self.ctitem, ctypeprim.W_CTypePrimitiveUniChar)

    def is_char_or_unichar_ptr_or_array(self):
        return isinstance(self.ctitem, ctypeprim.W_CTypePrimitiveCharOrUniChar)

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
            value = w_ob.unsafe_escaping_ptr()
        else:
            value = misc.as_unsigned_long(space, w_ob, strict=False)
            value = rffi.cast(rffi.CCHARP, value)
        return cdataobj.W_CData(space, value, self)

    def _convert_array_from_listview(self, cdata, lst_w):
        space = self.space
        if self.length >= 0 and len(lst_w) > self.length:
            raise oefmt(space.w_IndexError,
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
            if self.ctitem.pack_list_of_items(cdata, w_ob):   # fast path
                pass
            else:
                self._convert_array_from_listview(cdata, space.listview(w_ob))
        elif self.accept_str:
            if not space.isinstance_w(w_ob, space.w_bytes):
                raise self._convert_error("str or list or tuple", w_ob)
            s = space.bytes_w(w_ob)
            n = len(s)
            if self.length >= 0 and n > self.length:
                raise oefmt(space.w_IndexError,
                            "initializer string is too long for '%s' (got %d "
                            "characters)", self.name, n)
            copy_string_to_raw(llstr(s), cdata, 0, n)
            if n != self.length:
                cdata[n] = '\x00'
        elif isinstance(self.ctitem, ctypeprim.W_CTypePrimitiveUniChar):
            if not space.isinstance_w(w_ob, space.w_unicode):
                raise self._convert_error("unicode or list or tuple", w_ob)
            s = space.unicode_w(w_ob)
            n = len(s)
            if self.length >= 0 and n > self.length:
                raise oefmt(space.w_IndexError,
                            "initializer unicode string is too long for '%s' "
                            "(got %d characters)", self.name, n)
            unichardata = rffi.cast(rffi.CWCHARP, cdata)
            copy_unicode_to_raw(llunicode(s), unichardata, 0, n)
            if n != self.length:
                unichardata[n] = u'\x00'
        else:
            raise self._convert_error("list or tuple", w_ob)

    def string(self, cdataobj, maxlen):
        space = self.space
        if isinstance(self.ctitem, ctypeprim.W_CTypePrimitive):
            with cdataobj as ptr:
                if not ptr:
                    raise oefmt(space.w_RuntimeError,
                                "cannot use string() on %R",
                                cdataobj)
                #
                from pypy.module._cffi_backend import ctypearray
                length = maxlen
                if length < 0 and isinstance(self, ctypearray.W_CTypeArray):
                    length = cdataobj.get_array_length()
                #
                # pointer to a primitive type of size 1: builds and returns a str
                if self.ctitem.size == rffi.sizeof(lltype.Char):
                    if length < 0:
                        s = rffi.charp2str(ptr)
                    else:
                        s = rffi.charp2strn(ptr, length)
                    return space.newbytes(s)
                #
                # pointer to a wchar_t: builds and returns a unicode
                if self.is_unichar_ptr_or_array():
                    cdata = rffi.cast(rffi.CWCHARP, ptr)
                    if length < 0:
                        u = rffi.wcharp2unicode(cdata)
                    else:
                        u = rffi.wcharp2unicoden(cdata, length)
                    return space.newunicode(u)
        #
        return W_CType.string(self, cdataobj, maxlen)


class W_CTypePtrBase(W_CTypePtrOrArray):
    # base class for both pointers and pointers-to-functions
    _attrs_ = ['is_void_ptr', 'is_voidchar_ptr']
    _immutable_fields_ = ['is_void_ptr', 'is_voidchar_ptr']
    is_void_ptr = False
    is_voidchar_ptr = False

    def convert_to_object(self, cdata):
        ptrdata = rffi.cast(rffi.CCHARPP, cdata)[0]
        return cdataobj.W_CData(self.space, ptrdata, self)

    def convert_from_object(self, cdata, w_ob):
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
            if self.is_void_ptr or other.is_void_ptr:
                pass     # cast from or to 'void *'
            elif self.is_voidchar_ptr or other.is_voidchar_ptr:
                space = self.space
                msg = ("implicit cast from '%s' to '%s' "
                    "will be forbidden in the future (check that the types "
                    "are as you expect; use an explicit ffi.cast() if they "
                    "are correct)" % (other.name, self.name))
                space.warn(space.newtext(msg), space.w_UserWarning)
            else:
                raise self._convert_error("compatible pointer", w_ob)

        rffi.cast(rffi.CCHARPP, cdata)[0] = w_ob.unsafe_escaping_ptr()

    def _alignof(self):
        from pypy.module._cffi_backend import newtype
        return newtype.alignment_of_pointer


class W_CTypePointer(W_CTypePtrBase):
    _attrs_ = ['is_file', 'cache_array_type', '_array_types']
    _immutable_fields_ = ['is_file', 'cache_array_type?']
    kind = "pointer"
    cache_array_type = None
    is_nonfunc_pointer_or_array = True

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
        self.is_voidchar_ptr = (self.is_void_ptr or
                           isinstance(ctitem, ctypeprim.W_CTypePrimitiveChar))
        W_CTypePtrBase.__init__(self, space, size, extra, 2, ctitem)

    def newp(self, w_init, allocator):
        from pypy.module._cffi_backend.ctypestruct import W_CTypeStructOrUnion
        space = self.space
        ctitem = self.ctitem
        datasize = ctitem.size
        if datasize < 0:
            raise oefmt(space.w_TypeError,
                        "cannot instantiate ctype '%s' of unknown size",
                        self.name)
        if isinstance(ctitem, W_CTypeStructOrUnion):
            # 'newp' on a struct-or-union pointer: in this case, we return
            # a W_CDataPtrToStruct object which has a strong reference
            # to a W_CDataNewOwning that really contains the structure.
            #
            varsize_length = -1
            ctitem.force_lazy_struct()
            if ctitem._with_var_array:
                if not space.is_w(w_init, space.w_None):
                    datasize = ctitem.convert_struct_from_object(
                        lltype.nullptr(rffi.CCHARP.TO), w_init, datasize)
                varsize_length = datasize
            #
            cdatastruct = allocator.allocate(space, datasize, ctitem,
                                             length=varsize_length)
            ptr = cdatastruct.unsafe_escaping_ptr()
            cdata = cdataobj.W_CDataPtrToStructOrUnion(space, ptr,
                                                       self, cdatastruct)
        else:
            if self.is_char_or_unichar_ptr_or_array():
                datasize *= 2       # forcefully add a null character
            cdata = allocator.allocate(space, datasize, self)
        #
        if not space.is_w(w_init, space.w_None):
            with cdata as ptr:
                ctitem.convert_from_object(ptr, w_init)
        return cdata

    def _check_subscript_index(self, w_cdata, i):
        if (isinstance(w_cdata, cdataobj.W_CDataNewOwning) or
            isinstance(w_cdata, cdataobj.W_CDataPtrToStructOrUnion)):
            if i != 0:
                raise oefmt(self.space.w_IndexError,
                            "cdata '%s' can only be indexed by 0", self.name)
        else:
            if not w_cdata.unsafe_escaping_ptr():
                raise oefmt(self.space.w_RuntimeError,
                            "cannot dereference null pointer from cdata '%s'",
                            self.name)
        return self

    def _check_slice_index(self, w_cdata, start, stop):
        return self

    def add(self, cdata, i):
        space = self.space
        ctitem = self.ctitem
        itemsize = ctitem.size
        if ctitem.size < 0:
            if self.is_void_ptr:
                itemsize = 1
            else:
                raise oefmt(space.w_TypeError,
                            "ctype '%s' points to items of unknown size",
                            self.name)
        p = rffi.ptradd(cdata, i * itemsize)
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

    def _prepare_pointer_call_argument(self, w_init, cdata, keepalives, i):
        space = self.space
        if self.accept_str and space.isinstance_w(w_init, space.w_bytes):
            # special case to optimize strings passed to a "char *" argument
            value = space.bytes_w(w_init)
            keepalives[i] = value
            buf, buf_flag = rffi.get_nonmovingbuffer_final_null(value)
            rffi.cast(rffi.CCHARPP, cdata)[0] = buf
            return ord(buf_flag)    # 4, 5 or 6
        #
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
            raise oefmt(space.w_OverflowError,
                        "array size would overflow a ssize_t")
        result = lltype.malloc(rffi.CCHARP.TO, datasize,
                               flavor='raw', zero=True)
        try:
            self.convert_array_from_object(result, w_init)
        except Exception:
            lltype.free(result, flavor='raw')
            raise
        rffi.cast(rffi.CCHARPP, cdata)[0] = result
        return 1

    def convert_argument_from_object(self, cdata, w_ob, keepalives, i):
        from pypy.module._cffi_backend.ctypefunc import set_mustfree_flag
        result = (not isinstance(w_ob, cdataobj.W_CData) and
                  self._prepare_pointer_call_argument(w_ob, cdata,
                                                      keepalives, i))
        if result == 0:
            self.convert_from_object(cdata, w_ob)
        set_mustfree_flag(cdata, result)
        return result

    def getcfield(self, attr):
        return self.ctitem.getcfield(attr)

    def typeoffsetof_field(self, fieldname, following):
        if following == 0:
            return self.ctitem.typeoffsetof_field(fieldname, -1)
        return W_CTypePtrBase.typeoffsetof_field(self, fieldname, following)

    def typeoffsetof_index(self, index):
        space = self.space
        ctitem = self.ctitem
        if ctitem.size < 0:
            raise oefmt(space.w_TypeError, "pointer to opaque")
        try:
            offset = ovfcheck(index * ctitem.size)
        except OverflowError:
            raise oefmt(space.w_OverflowError,
                        "array offset would overflow a ssize_t")
        return ctitem, offset

    def rawaddressof(self, cdata, offset):
        from pypy.module._cffi_backend.ctypestruct import W_CTypeStructOrUnion
        space = self.space
        ctype2 = cdata.ctype
        if (isinstance(ctype2, W_CTypeStructOrUnion) or
                isinstance(ctype2, W_CTypePtrOrArray)):
            ptr = cdata.unsafe_escaping_ptr()
            ptr = rffi.ptradd(ptr, offset)
            return cdataobj.W_CData(space, ptr, self)
        else:
            raise oefmt(space.w_TypeError,
                        "expected a cdata struct/union/array/pointer object")

    def _fget(self, attrchar):
        if attrchar == 'i':     # item
            return self.ctitem
        return W_CTypePtrBase._fget(self, attrchar)

# ____________________________________________________________


FILEP = rffi.COpaquePtr("FILE")
rffi_fdopen = rffi.llexternal("fdopen", [rffi.INT, rffi.CCHARP], FILEP,
                              save_err=rffi.RFFI_SAVE_ERRNO)
rffi_setbuf = rffi.llexternal("setbuf", [FILEP, rffi.CCHARP], lltype.Void)
rffi_fclose = rffi.llexternal("fclose", [FILEP], rffi.INT)

class CffiFileObj(object):
    _immutable_ = True

    def __init__(self, fd, mode):
        self.llf = rffi_fdopen(fd, mode)
        if not self.llf:
            raise OSError(rposix.get_saved_errno(), "fdopen failed")
        rffi_setbuf(self.llf, lltype.nullptr(rffi.CCHARP.TO))

    def close(self):
        rffi_fclose(self.llf)


def prepare_file_argument(space, w_fileobj):
    w_fileobj.direct_flush()
    if w_fileobj.cffi_fileobj is None:
        fd = w_fileobj.direct_fileno()
        if fd < 0:
            raise oefmt(space.w_ValueError, "file has no OS file descriptor")
        try:
            w_fileobj.cffi_fileobj = CffiFileObj(fd, w_fileobj.mode)
        except OSError as e:
            raise wrap_oserror(space, e)
    return rffi.cast(rffi.CCHARP, w_fileobj.cffi_fileobj.llf)
