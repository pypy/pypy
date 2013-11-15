from __future__ import with_statement

from rpython.rlib import jit
from rpython.rlib.objectmodel import keepalive_until_here
from rpython.rlib.rarithmetic import ovfcheck, widen
from rpython.rlib.unroll import unrolling_iterable
from rpython.rtyper.annlowlevel import llstr
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rtyper.lltypesystem.rstr import copy_string_to_raw

from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.buffer import RWBuffer
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.gateway import (
    interp2app, interpindirect2app, unwrap_spec)
from pypy.interpreter.typedef import (
    GetSetProperty, TypeDef, make_weakref_descr)
from pypy.module._file.interp_file import W_File
from pypy.objspace.std.floatobject import W_FloatObject


@unwrap_spec(typecode=str)
def w_array(space, w_cls, typecode, __args__):
    if len(__args__.arguments_w) > 1:
        msg = 'array() takes at most 2 arguments'
        raise OperationError(space.w_TypeError, space.wrap(msg))
    if len(typecode) != 1:
        msg = 'array() argument 1 must be char, not str'
        raise OperationError(space.w_TypeError, space.wrap(msg))
    typecode = typecode[0]

    if space.is_w(w_cls, space.gettypeobject(W_ArrayBase.typedef)):
        if __args__.keywords:
            msg = 'array.array() does not take keyword arguments'
            raise OperationError(space.w_TypeError, space.wrap(msg))

    for tc in unroll_typecodes:
        if typecode == tc:
            a = space.allocate_instance(types[tc].w_class, w_cls)
            a.__init__(space)

            if len(__args__.arguments_w) > 0:
                w_initializer = __args__.arguments_w[0]
                if space.type(w_initializer) is space.w_str:
                    a.descr_fromstring(space, space.str_w(w_initializer))
                elif space.type(w_initializer) is space.w_list:
                    a.descr_fromlist(space, w_initializer)
                else:
                    a.extend(w_initializer, True)
            break
    else:
        msg = 'bad typecode (must be c, b, B, u, h, H, i, I, l, L, f or d)'
        raise OperationError(space.w_ValueError, space.wrap(msg))

    return a


def descr_itemsize(space, self):
    return space.wrap(self.itemsize)


def descr_typecode(space, self):
    return space.wrap(self.typecode)

arr_eq_driver = jit.JitDriver(name='array_eq_driver', greens=['comp_func'],
                              reds='auto')
EQ, NE, LT, LE, GT, GE = range(6)

def compare_arrays(space, arr1, arr2, comp_op):
    if not (isinstance(arr1, W_ArrayBase) and isinstance(arr2, W_ArrayBase)):
        return space.w_NotImplemented
    if comp_op == EQ and arr1.len != arr2.len:
        return space.w_False
    if comp_op == NE and arr1.len != arr2.len:
        return space.w_True
    lgt = min(arr1.len, arr2.len)
    for i in range(lgt):
        arr_eq_driver.jit_merge_point(comp_func=comp_op)
        w_elem1 = arr1.w_getitem(space, i)
        w_elem2 = arr2.w_getitem(space, i)
        if comp_op == EQ:
            res = space.is_true(space.eq(w_elem1, w_elem2))
            if not res:
                return space.w_False
        elif comp_op == NE:
            res = space.is_true(space.ne(w_elem1, w_elem2))
            if res:
                return space.w_True
        elif comp_op == LT or comp_op == GT:
            if comp_op == LT:
                res = space.is_true(space.lt(w_elem1, w_elem2))
            else:
                res = space.is_true(space.gt(w_elem1, w_elem2))
            if res:
                return space.w_True
            elif not space.is_true(space.eq(w_elem1, w_elem2)):
                return space.w_False
        else:
            if comp_op == LE:
                res = space.is_true(space.le(w_elem1, w_elem2))
            else:
                res = space.is_true(space.ge(w_elem1, w_elem2))
            if not res:
                return space.w_False
            elif not space.is_true(space.eq(w_elem1, w_elem2)):
                return space.w_True
    # we have some leftovers
    if comp_op == EQ:
        return space.w_True
    elif comp_op == NE:
        return space.w_False
    if arr1.len == arr2.len:
        if comp_op == LT or comp_op == GT:
            return space.w_False
        return space.w_True
    if comp_op == LT or comp_op == LE:
        if arr1.len < arr2.len:
            return space.w_True
        return space.w_False
    if arr1.len > arr2.len:
        return space.w_True
    return space.w_False

UNICODE_ARRAY = lltype.Ptr(lltype.Array(lltype.UniChar,
                                        hints={'nolength': True}))

class W_ArrayBase(W_Root):
    _attrs_ = ('space', 'len', 'allocated', '_lifeline_') # no buffer

    def __init__(self, space):
        self.space = space
        self.len = 0
        self.allocated = 0

    def descr_append(self, space, w_x):
        """ append(x)

        Append new value x to the end of the array.
        """
        raise NotImplementedError

    def descr_extend(self, space, w_x):
        """ extend(array or iterable)

        Append items to the end of the array.
        """
        self.extend(w_x)

    def descr_count(self, space, w_val):
        """ count(x)

        Return number of occurrences of x in the array.
        """
        raise NotImplementedError

    def descr_index(self, space, w_x):
        """ index(x)

        Return index of first occurrence of x in the array.
        """
        raise NotImplementedError

    def descr_reverse(self, space):
        """ reverse()

        Reverse the order of the items in the array.
        """
        raise NotImplementedError

    def descr_remove(self, space, w_val):
        """ remove(x)

        Remove the first occurrence of x in the array.
        """
        raise NotImplementedError

    @unwrap_spec(i=int)
    def descr_pop(self, space, i=-1):
        """ pop([i])

        Return the i-th element and delete it from the array. i defaults to -1.
        """
        raise NotImplementedError

    @unwrap_spec(idx=int)
    def descr_insert(self, space, idx, w_val):
        """ insert(i,x)

        Insert a new item x into the array before position i.
        """
        raise NotImplementedError

    def descr_tolist(self, space):
        """ tolist() -> list

        Convert array to an ordinary list with the same items.
        """
        w_l = space.newlist([])
        for i in range(self.len):
            w_l.append(self.w_getitem(space, i))
        return w_l

    def descr_fromlist(self, space, w_lst):
        """ fromlist(list)

        Append items to array from list.
        """
        if not space.isinstance_w(w_lst, space.w_list):
            raise OperationError(space.w_TypeError,
                                 space.wrap("arg must be list"))
        s = self.len
        try:
            self.fromsequence(w_lst)
        except OperationError:
            self.setlen(s)
            raise

    def descr_tostring(self, space):
        """ tostring() -> string

        Convert the array to an array of machine values and return the string
        representation.
        """
        cbuf = self._charbuf_start()
        s = rffi.charpsize2str(cbuf, self.len * self.itemsize)
        self._charbuf_stop()
        return self.space.wrap(s)

    @unwrap_spec(s=str)
    def descr_fromstring(self, space, s):
        """ fromstring(string)

        Appends items from the string, interpreting it as an array of machine
        values,as if it had been read from a file using the fromfile() method).
        """
        if len(s) % self.itemsize != 0:
            msg = 'string length not a multiple of item size'
            raise OperationError(self.space.w_ValueError, self.space.wrap(msg))
        oldlen = self.len
        new = len(s) / self.itemsize
        self.setlen(oldlen + new)
        cbuf = self._charbuf_start()
        copy_string_to_raw(llstr(s), rffi.ptradd(cbuf, oldlen * self.itemsize),
                           0, len(s))
        self._charbuf_stop()

    @unwrap_spec(w_f=W_File, n=int)
    def descr_fromfile(self, space, w_f, n):
        """ fromfile(f, n)

        Read n objects from the file object f and append them to the end of the
        array.  Also called as read.
        """
        try:
            size = ovfcheck(self.itemsize * n)
        except OverflowError:
            raise MemoryError
        w_item = space.call_method(w_f, 'read', space.wrap(size))
        item = space.str_w(w_item)
        if len(item) < size:
            n = len(item) % self.itemsize
            elems = max(0, len(item) - (len(item) % self.itemsize))
            if n != 0:
                item = item[0:elems]
            self.descr_fromstring(space, item)
            msg = "not enough items in file"
            raise OperationError(space.w_EOFError, space.wrap(msg))
        self.descr_fromstring(space, item)

    @unwrap_spec(w_f=W_File)
    def descr_tofile(self, space, w_f):
        """ tofile(f)

        Write all items (as machine values) to the file object f.  Also
        called as write.
        """
        w_s = self.descr_tostring(space)
        space.call_method(w_f, 'write', w_s)

    def descr_fromunicode(self, space, w_ustr):
        """ fromunicode(ustr)

        Extends this array with data from the unicode string ustr.
        The array must be a type 'u' array; otherwise a ValueError
        is raised.  Use array.fromstring(ustr.decode(...)) to
        append Unicode data to an array of some other type.
        """
        # XXX the following probable bug is not emulated:
        # CPython accepts a non-unicode string or a buffer, and then
        # behaves just like fromstring(), except that it strangely truncate
        # string arguments at multiples of the unicode byte size.
        # Let's only accept unicode arguments for now.
        if self.typecode == 'u':
            self.fromsequence(w_ustr)
        else:
            msg = "fromunicode() may only be called on type 'u' arrays"
            raise OperationError(space.w_ValueError, space.wrap(msg))

    def descr_tounicode(self, space):
        """ tounicode() -> unicode

        Convert the array to a unicode string.  The array must be
        a type 'u' array; otherwise a ValueError is raised.  Use
        array.tostring().decode() to obtain a unicode string from
        an array of some other type.
        """
        if self.typecode == 'u':
            buf = rffi.cast(UNICODE_ARRAY, self._buffer_as_unsigned())
            return space.wrap(rffi.wcharpsize2unicode(buf, self.len))
        else:
            msg = "tounicode() may only be called on type 'u' arrays"
            raise OperationError(space.w_ValueError, space.wrap(msg))

    def descr_buffer_info(self, space):
        """ buffer_info() -> (address, length)

        Return a tuple (address, length) giving the current memory address and
        the length in items of the buffer used to hold array's contents
        The length should be multiplied by the itemsize attribute to calculate
        the buffer length in bytes.
        """
        w_ptr = space.wrap(self._buffer_as_unsigned())
        w_len = space.wrap(self.len)
        return space.newtuple([w_ptr, w_len])

    def descr_reduce(self, space):
        """ Return state information for pickling.
        """
        if self.len > 0:
            w_s = self.descr_tostring(space)
            args = [space.wrap(self.typecode), w_s]
        else:
            args = [space.wrap(self.typecode)]
        try:
            dct = space.getattr(self, space.wrap('__dict__'))
        except OperationError:
            dct = space.w_None
        return space.newtuple([space.type(self), space.newtuple(args), dct])

    def descr_copy(self, space):
        """ copy(array)

        Return a copy of the array.
        """
        w_a = self.constructor(self.space)
        w_a.setlen(self.len, overallocate=False)
        rffi.c_memcpy(
            rffi.cast(rffi.VOIDP, w_a._buffer_as_unsigned()),
            rffi.cast(rffi.VOIDP, self._buffer_as_unsigned()),
            self.len * self.itemsize
        )
        return w_a

    def descr_byteswap(self, space):
        """ byteswap()

        Byteswap all items of the array.  If the items in the array are
        not 1, 2, 4, or 8 bytes in size, RuntimeError is raised.
        """
        if self.itemsize not in [1, 2, 4, 8]:
            msg = "byteswap not supported for this array"
            raise OperationError(space.w_RuntimeError, space.wrap(msg))
        if self.len == 0:
            return
        bytes = self._charbuf_start()
        tmp = [bytes[0]] * self.itemsize
        for start in range(0, self.len * self.itemsize, self.itemsize):
            stop = start + self.itemsize - 1
            for i in range(self.itemsize):
                tmp[i] = bytes[start + i]
            for i in range(self.itemsize):
                bytes[stop - i] = tmp[i]
        self._charbuf_stop()

    def descr_len(self, space):
        return space.wrap(self.len)

    def descr_eq(self, space, w_arr2):
        "x.__eq__(y) <==> x==y"
        return compare_arrays(space, self, w_arr2, EQ)

    def descr_ne(self, space, w_arr2):
        "x.__ne__(y) <==> x!=y"
        return compare_arrays(space, self, w_arr2, NE)

    def descr_lt(self, space, w_arr2):
        "x.__lt__(y) <==> x<y"
        return compare_arrays(space, self, w_arr2, LT)

    def descr_le(self, space, w_arr2):
        "x.__le__(y) <==> x<=y"
        return compare_arrays(space, self, w_arr2, LE)

    def descr_gt(self, space, w_arr2):
        "x.__gt__(y) <==> x>y"
        return compare_arrays(space, self, w_arr2, GT)

    def descr_ge(self, space, w_arr2):
        "x.__ge__(y) <==> x>=y"
        return compare_arrays(space, self, w_arr2, GE)

    # Basic get/set/append/extend methods

    def descr_getitem(self, space, w_idx):
        "x.__getitem__(y) <==> x[y]"
        if not space.isinstance_w(w_idx, space.w_slice):
            idx, stop, step = space.decode_index(w_idx, self.len)
            assert step == 0
            return self.w_getitem(space, idx)
        else:
            return self.getitem_slice(space, w_idx)

    def descr_getslice(self, space, w_i, w_j):
        return space.getitem(self, space.newslice(w_i, w_j, space.w_None))

    def descr_setitem(self, space, w_idx, w_item):
        "x.__setitem__(i, y) <==> x[i]=y"
        if space.isinstance_w(w_idx, space.w_slice):
            self.setitem_slice(space, w_idx, w_item)
        else:
            self.setitem(space, w_idx, w_item)

    def descr_setslice(self, space, w_start, w_stop, w_item):
        self.setitem_slice(space,
                           space.newslice(w_start, w_stop, space.w_None),
                           w_item)

    def descr_delitem(self, space, w_idx):
        start, stop, step, size = self.space.decode_index4(w_idx, self.len)
        if step != 1:
            # I don't care about efficiency of that so far
            w_lst = self.descr_tolist(space)
            space.delitem(w_lst, w_idx)
            self.setlen(0)
            self.fromsequence(w_lst)
            return
        return self.delitem(space, start, stop)

    def descr_delslice(self, space, w_start, w_stop):
        self.descr_delitem(space, space.newslice(w_start, w_stop,
                                                 space.w_None))

    def descr_add(self, space, w_other):
        raise NotImplementedError

    def descr_inplace_add(self, space, w_other):
        raise NotImplementedError

    def descr_mul(self, space, w_repeat):
        raise NotImplementedError

    def descr_inplace_mul(self, space, w_repeat):
        raise NotImplementedError

    def descr_radd(self, space, w_other):
        return self.descr_add(space, w_other)

    def descr_rmul(self, space, w_repeat):
        return self.descr_mul(space, w_repeat)

    # Misc methods

    def descr_buffer(self, space):
        return space.wrap(ArrayBuffer(self))

    def descr_repr(self, space):
        if self.len == 0:
            return space.wrap("array('%s')" % self.typecode)
        elif self.typecode == "c":
            r = space.repr(self.descr_tostring(space))
            s = "array('%s', %s)" % (self.typecode, space.str_w(r))
            return space.wrap(s)
        elif self.typecode == "u":
            r = space.repr(self.descr_tounicode(space))
            s = "array('%s', %s)" % (self.typecode, space.str_w(r))
            return space.wrap(s)
        else:
            r = space.repr(self.descr_tolist(space))
            s = "array('%s', %s)" % (self.typecode, space.str_w(r))
            return space.wrap(s)

W_ArrayBase.typedef = TypeDef(
    'array',
    __new__ = interp2app(w_array),
    __module__ = 'array',

    __len__ = interp2app(W_ArrayBase.descr_len),
    __eq__ = interp2app(W_ArrayBase.descr_eq),
    __ne__ = interp2app(W_ArrayBase.descr_ne),
    __lt__ = interp2app(W_ArrayBase.descr_lt),
    __le__ = interp2app(W_ArrayBase.descr_le),
    __gt__ = interp2app(W_ArrayBase.descr_gt),
    __ge__ = interp2app(W_ArrayBase.descr_ge),

    __getitem__ = interp2app(W_ArrayBase.descr_getitem),
    __getslice__ = interp2app(W_ArrayBase.descr_getslice),
    __setitem__ = interp2app(W_ArrayBase.descr_setitem),
    __setslice__ = interp2app(W_ArrayBase.descr_setslice),
    __delitem__ = interp2app(W_ArrayBase.descr_delitem),
    __delslice__ = interp2app(W_ArrayBase.descr_delslice),

    __add__ = interpindirect2app(W_ArrayBase.descr_add),
    __iadd__ = interpindirect2app(W_ArrayBase.descr_inplace_add),
    __mul__ = interpindirect2app(W_ArrayBase.descr_mul),
    __imul__ = interpindirect2app(W_ArrayBase.descr_inplace_mul),
    __radd__ = interp2app(W_ArrayBase.descr_radd),
    __rmul__ = interp2app(W_ArrayBase.descr_rmul),

    __buffer__ = interp2app(W_ArrayBase.descr_buffer),
    __repr__ = interp2app(W_ArrayBase.descr_repr),

    itemsize = GetSetProperty(descr_itemsize),
    typecode = GetSetProperty(descr_typecode),
    __weakref__ = make_weakref_descr(W_ArrayBase),
    append = interpindirect2app(W_ArrayBase.descr_append),
    extend = interp2app(W_ArrayBase.descr_extend),
    count = interpindirect2app(W_ArrayBase.descr_count),
    index = interpindirect2app(W_ArrayBase.descr_index),
    reverse = interpindirect2app(W_ArrayBase.descr_reverse),
    remove = interpindirect2app(W_ArrayBase.descr_remove),
    pop = interpindirect2app(W_ArrayBase.descr_pop),
    insert = interpindirect2app(W_ArrayBase.descr_insert),

    tolist = interp2app(W_ArrayBase.descr_tolist),
    fromlist = interp2app(W_ArrayBase.descr_fromlist),
    tostring = interp2app(W_ArrayBase.descr_tostring),
    fromstring = interp2app(W_ArrayBase.descr_fromstring),
    tofile = interp2app(W_ArrayBase.descr_tofile),
    fromfile = interp2app(W_ArrayBase.descr_fromfile),
    fromunicode = interp2app(W_ArrayBase.descr_fromunicode),
    tounicode = interp2app(W_ArrayBase.descr_tounicode),

    buffer_info = interp2app(W_ArrayBase.descr_buffer_info),
    __copy__ = interp2app(W_ArrayBase.descr_copy),
    __reduce__ = interp2app(W_ArrayBase.descr_reduce),
    byteswap = interp2app(W_ArrayBase.descr_byteswap),
)


class TypeCode(object):
    def __init__(self, itemtype, unwrap, canoverflow=False, signed=False,
                 method='__int__'):
        self.itemtype = itemtype
        self.bytes = rffi.sizeof(itemtype)
        self.arraytype = lltype.Array(itemtype, hints={'nolength': True})
        self.unwrap = unwrap
        self.signed = signed
        self.canoverflow = canoverflow
        self.w_class = None
        self.method = method

        if self.canoverflow:
            assert self.bytes <= rffi.sizeof(rffi.ULONG)
            if self.bytes == rffi.sizeof(rffi.ULONG) and not signed and \
                    self.unwrap == 'int_w':
                # Treat this type as a ULONG
                self.unwrap = 'bigint_w'
                self.canoverflow = False

    def _freeze_(self):
        # hint for the annotator: track individual constant instances
        return True

types = {
    'c': TypeCode(lltype.Char,        'str_w', method=''),
    'u': TypeCode(lltype.UniChar,     'unicode_w', method=''),
    'b': TypeCode(rffi.SIGNEDCHAR,    'int_w', True, True),
    'B': TypeCode(rffi.UCHAR,         'int_w', True),
    'h': TypeCode(rffi.SHORT,         'int_w', True, True),
    'H': TypeCode(rffi.USHORT,        'int_w', True),
    'i': TypeCode(rffi.INT,           'int_w', True, True),
    'I': TypeCode(rffi.UINT,          'int_w', True),
    'l': TypeCode(rffi.LONG,          'int_w', True, True),
    'L': TypeCode(rffi.ULONG,         'bigint_w'),  # Overflow handled by
                                                    # rbigint.touint() which
                                                    # corresponds to the
                                                    # C-type unsigned long
    'f': TypeCode(lltype.SingleFloat, 'float_w', method='__float__'),
    'd': TypeCode(lltype.Float,       'float_w', method='__float__'),
    }
for k, v in types.items():
    v.typecode = k
unroll_typecodes = unrolling_iterable(types.keys())

class ArrayBuffer(RWBuffer):
    def __init__(self, array):
        self.array = array

    def getlength(self):
        return self.array.len * self.array.itemsize

    def getitem(self, index):
        array = self.array
        data = array._charbuf_start()
        char = data[index]
        array._charbuf_stop()
        return char

    def setitem(self, index, char):
        array = self.array
        data = array._charbuf_start()
        data[index] = char
        array._charbuf_stop()

    def get_raw_address(self):
        return self.array._charbuf_start()

def make_array(mytype):
    W_ArrayBase = globals()['W_ArrayBase']

    class W_Array(W_ArrayBase):
        itemsize = mytype.bytes
        typecode = mytype.typecode

        _attrs_ = ('space', 'len', 'allocated', '_lifeline_', 'buffer')

        def __init__(self, space):
            W_ArrayBase.__init__(self, space)
            self.buffer = lltype.nullptr(mytype.arraytype)

        def item_w(self, w_item):
            space = self.space
            unwrap = getattr(space, mytype.unwrap)
            try:
                item = unwrap(w_item)
            except OperationError, e:
                if isinstance(w_item, W_FloatObject):
                    # Odd special case from cpython
                    raise
                if mytype.method != '' and e.match(space, space.w_TypeError):
                    try:
                        item = unwrap(space.call_method(w_item, mytype.method))
                    except OperationError:
                        msg = 'array item must be ' + mytype.unwrap[:-2]
                        raise operationerrfmt(space.w_TypeError, msg)
                else:
                    raise
            if mytype.unwrap == 'bigint_w':
                try:
                    item = item.touint()
                except (ValueError, OverflowError):
                    msg = 'unsigned %d-byte integer out of range' % \
                          mytype.bytes
                    raise OperationError(space.w_OverflowError,
                                         space.wrap(msg))
                return rffi.cast(mytype.itemtype, item)
            if mytype.unwrap == 'str_w' or mytype.unwrap == 'unicode_w':
                if len(item) != 1:
                    msg = 'array item must be char'
                    raise OperationError(space.w_TypeError, space.wrap(msg))
                item = item[0]
                return rffi.cast(mytype.itemtype, item)
            #
            # "regular" case: it fits in an rpython integer (lltype.Signed)
            result = rffi.cast(mytype.itemtype, item)
            if mytype.canoverflow:
                if rffi.cast(lltype.Signed, result) != item:
                    # overflow.  build the correct message
                    if item < 0:
                        msg = ('signed %d-byte integer is less than minimum' %
                               mytype.bytes)
                    else:
                        msg = ('signed %d-byte integer is greater than maximum'
                               % mytype.bytes)
                    if not mytype.signed:
                        msg = 'un' + msg      # 'signed' => 'unsigned'
                    raise OperationError(space.w_OverflowError,
                                         space.wrap(msg))
            return result

        def __del__(self):
            # note that we don't call clear_all_weakrefs here because
            # an array with freed buffer is ok to see - it's just empty with 0
            # length
            self.setlen(0)

        def setlen(self, size, zero=False, overallocate=True):
            if size > 0:
                if size > self.allocated or size < self.allocated / 2:
                    if overallocate:
                        if size < 9:
                            some = 3
                        else:
                            some = 6
                        some += size >> 3
                    else:
                        some = 0
                    self.allocated = size + some
                    if zero:
                        new_buffer = lltype.malloc(
                            mytype.arraytype, self.allocated, flavor='raw',
                            add_memory_pressure=True, zero=True)
                    else:
                        new_buffer = lltype.malloc(
                            mytype.arraytype, self.allocated, flavor='raw',
                            add_memory_pressure=True)
                        for i in range(min(size, self.len)):
                            new_buffer[i] = self.buffer[i]
                else:
                    self.len = size
                    return
            else:
                assert size == 0
                self.allocated = 0
                new_buffer = lltype.nullptr(mytype.arraytype)

            if self.buffer:
                lltype.free(self.buffer, flavor='raw')
            self.buffer = new_buffer
            self.len = size

        def fromsequence(self, w_seq):
            space = self.space
            oldlen = self.len
            try:
                new = space.len_w(w_seq)
                self.setlen(self.len + new)
            except OperationError:
                pass

            i = 0
            try:
                if mytype.typecode == 'u':
                    myiter = space.unpackiterable
                else:
                    myiter = space.listview
                for w_i in myiter(w_seq):
                    if oldlen + i >= self.len:
                        self.setlen(oldlen + i + 1)
                    self.buffer[oldlen + i] = self.item_w(w_i)
                    i += 1
            except OperationError:
                self.setlen(oldlen + i)
                raise
            self.setlen(oldlen + i)

        def extend(self, w_iterable, accept_different_array=False):
            space = self.space
            if isinstance(w_iterable, W_Array):
                oldlen = self.len
                new = w_iterable.len
                self.setlen(self.len + new)
                i = 0
                while i < new:
                    if oldlen + i >= self.len:
                        self.setlen(oldlen + i + 1)
                    self.buffer[oldlen + i] = w_iterable.buffer[i]
                    i += 1
                self.setlen(oldlen + i)
            elif (not accept_different_array
                  and isinstance(w_iterable, W_ArrayBase)):
                msg = "can only extend with array of same kind"
                raise OperationError(space.w_TypeError, space.wrap(msg))
            else:
                self.fromsequence(w_iterable)

        def _charbuf_start(self):
            return rffi.cast(rffi.CCHARP, self.buffer)

        def _buffer_as_unsigned(self):
            return rffi.cast(lltype.Unsigned, self.buffer)

        def _charbuf_stop(self):
            keepalive_until_here(self)

        def w_getitem(self, space, idx):
            item = self.buffer[idx]
            if mytype.typecode in 'bBhHil':
                item = rffi.cast(lltype.Signed, item)
            elif mytype.typecode == 'f':
                item = float(item)
            return space.wrap(item)

        # interface

        def descr_append(self, space, w_x):
            x = self.item_w(w_x)
            self.setlen(self.len + 1)
            self.buffer[self.len - 1] = x

        # List interface
        def descr_count(self, space, w_val):
            cnt = 0
            for i in range(self.len):
                # XXX jitdriver
                w_item = self.w_getitem(space, i)
                if space.is_true(space.eq(w_item, w_val)):
                    cnt += 1
            return space.wrap(cnt)

        def descr_index(self, space, w_val):
            for i in range(self.len):
                w_item = self.w_getitem(space, i)
                if space.is_true(space.eq(w_item, w_val)):
                    return space.wrap(i)
            msg = 'array.index(x): x not in list'
            raise OperationError(space.w_ValueError, space.wrap(msg))

        def descr_reverse(self, space):
            b = self.buffer
            for i in range(self.len / 2):
                b[i], b[self.len - i - 1] = b[self.len - i - 1], b[i]

        def descr_pop(self, space, i):
            if i < 0:
                i += self.len
            if i < 0 or i >= self.len:
                msg = 'pop index out of range'
                raise OperationError(space.w_IndexError, space.wrap(msg))
            w_val = self.w_getitem(space, i)
            while i < self.len - 1:
                self.buffer[i] = self.buffer[i + 1]
                i += 1
            self.setlen(self.len - 1)
            return w_val

        def descr_remove(self, space, w_val):
            w_idx = self.descr_index(space, w_val)
            self.descr_pop(space, space.int_w(w_idx))

        def descr_insert(self, space, idx, w_val):
            if idx < 0:
                idx += self.len
            if idx < 0:
                idx = 0
            if idx > self.len:
                idx = self.len

            val = self.item_w(w_val)
            self.setlen(self.len + 1)
            i = self.len - 1
            while i > idx:
                self.buffer[i] = self.buffer[i - 1]
                i -= 1
            self.buffer[i] = val

        def getitem_slice(self, space, w_idx):
            start, stop, step, size = space.decode_index4(w_idx, self.len)
            w_a = mytype.w_class(self.space)
            w_a.setlen(size, overallocate=False)
            assert step != 0
            j = 0
            for i in range(start, stop, step):
                w_a.buffer[j] = self.buffer[i]
                j += 1
            return w_a

        def setitem(self, space, w_idx, w_item):
            idx, stop, step = space.decode_index(w_idx, self.len)
            if step != 0:
                msg = 'can only assign array to array slice'
                raise OperationError(self.space.w_TypeError,
                                     self.space.wrap(msg))
            item = self.item_w(w_item)
            self.buffer[idx] = item

        def setitem_slice(self, space, w_idx, w_item):
            if not isinstance(w_item, W_Array):
                raise OperationError(space.w_TypeError, space.wrap(
                    "can only assign to a slice array"))
            start, stop, step, size = self.space.decode_index4(w_idx, self.len)
            assert step != 0
            if w_item.len != size or self is w_item:
                # XXX this is a giant slow hack
                w_lst = self.descr_tolist(space)
                w_item = space.call_method(w_item, 'tolist')
                space.setitem(w_lst, w_idx, w_item)
                self.setlen(0)
                self.fromsequence(w_lst)
            else:
                j = 0
                for i in range(start, stop, step):
                    self.buffer[i] = w_item.buffer[j]
                    j += 1

        def delitem(self, space, i, j):
            if i < 0:
                i += self.len
            if i < 0:
                i = 0
            if j < 0:
                j += self.len
            if j < 0:
                j = 0
            if j > self.len:
                j = self.len
            if i >= j:
                return None
            oldbuffer = self.buffer
            self.buffer = lltype.malloc(
                mytype.arraytype, max(self.len - (j - i), 0), flavor='raw',
                add_memory_pressure=True)
            if i:
                rffi.c_memcpy(
                    rffi.cast(rffi.VOIDP, self.buffer),
                    rffi.cast(rffi.VOIDP, oldbuffer),
                    i * mytype.bytes
                )
            if j < self.len:
                rffi.c_memcpy(
                    rffi.cast(rffi.VOIDP, rffi.ptradd(self.buffer, i)),
                    rffi.cast(rffi.VOIDP, rffi.ptradd(oldbuffer, j)),
                    (self.len - j) * mytype.bytes
                )
            self.len -= j - i
            self.allocated = self.len
            if oldbuffer:
                lltype.free(oldbuffer, flavor='raw')

        # Add and mul methods
        def descr_add(self, space, w_other):
            if not isinstance(w_other, W_Array):
                return space.w_NotImplemented
            a = mytype.w_class(space)
            a.setlen(self.len + w_other.len, overallocate=False)
            if self.len:
                rffi.c_memcpy(
                    rffi.cast(rffi.VOIDP, a.buffer),
                    rffi.cast(rffi.VOIDP, self.buffer),
                    self.len * mytype.bytes
                )
            if w_other.len:
                rffi.c_memcpy(
                    rffi.cast(rffi.VOIDP, rffi.ptradd(a.buffer, self.len)),
                    rffi.cast(rffi.VOIDP, w_other.buffer),
                    w_other.len * mytype.bytes
                )
            return a

        def descr_inplace_add(self, space, w_other):
            if not isinstance(w_other, W_Array):
                return space.w_NotImplemented
            oldlen = self.len
            otherlen = w_other.len
            self.setlen(oldlen + otherlen)
            if otherlen:
                rffi.c_memcpy(
                    rffi.cast(rffi.VOIDP, rffi.ptradd(self.buffer, oldlen)),
                    rffi.cast(rffi.VOIDP, w_other.buffer),
                    otherlen * mytype.bytes
                )
            return self

        def descr_mul(self, space, w_repeat):
            return _mul_helper(space, self, w_repeat, False)

        def descr_inplace_mul(self, space, w_repeat):
            return _mul_helper(space, self, w_repeat, True)

    def _mul_helper(space, self, w_repeat, is_inplace):
        try:
            repeat = space.getindex_w(w_repeat, space.w_OverflowError)
        except OperationError, e:
            if e.match(space, space.w_TypeError):
                return space.w_NotImplemented
            raise
        repeat = max(repeat, 0)
        try:
            newlen = ovfcheck(self.len * repeat)
        except OverflowError:
            raise MemoryError
        oldlen = self.len
        if is_inplace:
            a = self
            start = 1
        else:
            a = mytype.w_class(space)
            start = 0
        # <a performance hack>
        if oldlen == 1:
            if mytype.unwrap == 'str_w' or mytype.unwrap == 'unicode_w':
                zero = not ord(self.buffer[0])
            elif mytype.unwrap == 'int_w' or mytype.unwrap == 'bigint_w':
                zero = not widen(self.buffer[0])
            #elif mytype.unwrap == 'float_w':
            #    value = ...float(self.buffer[0])  xxx handle the case of -0.0
            else:
                zero = False
            if zero:
                a.setlen(newlen, zero=True, overallocate=False)
                return a
            a.setlen(newlen, overallocate=False)
            item = self.buffer[0]
            for r in range(start, repeat):
                a.buffer[r] = item
            return a
        # </a performance hack>
        a.setlen(newlen, overallocate=False)
        for r in range(start, repeat):
            for i in range(oldlen):
                a.buffer[r * oldlen + i] = self.buffer[i]
        return a

    mytype.w_class = W_Array
    W_Array.constructor = W_Array
    name = 'ArrayType' + mytype.typecode
    W_Array.__name__ = 'W_' + name

for mytype in types.values():
    make_array(mytype)
del mytype
