"""This module defines an object type which can efficiently represent
an array of basic values: characters, integers, floating point
numbers.  Arrays are sequence types and behave very much like lists,
except that the type of objects stored in them is constrained.  The
type is specified at object creation time by using a type code, which
is a single character.  The following type codes are defined:

    Type code   C Type             Minimum size in bytes 
    'c'         character          1 
    'b'         signed integer     1 
    'B'         unsigned integer   1 
    'u'         Unicode character  2 
    'h'         signed integer     2 
    'H'         unsigned integer   2 
    'i'         signed integer     2 
    'I'         unsigned integer   2 
    'l'         signed integer     4 
    'L'         unsigned integer   4 
    'f'         floating point     4 
    'd'         floating point     8 

The constructor is:

array(typecode [, initializer]) -- create a new array
"""
import sys

if sys.maxunicode == 65535:
    UNICODE_SIZE = 2
    UNICODE_FORMAT = "H"
else:
    UNICODE_SIZE = 4
    UNICODE_FORMAT = "I"

def c_type_check(x):
    if not isinstance(x, str) or len(x) != 1:
        raise TypeError("array item must be char")
    return x

def general_int_type_check(x, lower_bound, upper_bound):
    if not (isinstance(x, int) or isinstance(x, long) or isinstance(x, float)):
        raise TypeError("an integer is required")
    x_int = int(x)
    if not (x_int >= lower_bound and x_int <= upper_bound):
        raise OverflowError("integer is not in the allowed range")
    return x_int    

def b_type_check(x):
    return general_int_type_check(x, -128, 127)

def BB_type_check(x):
    return general_int_type_check(x, 0, 255)

def u_type_check(x):
    if isinstance(x, str):
        if len(x) / UNICODE_SIZE == 1:
            # XXX Problem: CPython will gladly accept any unicode codepoint
            # up to 0xFFFFFFFF in UCS-4 builds here, but unichr which is used
            # to implement decode for unicode_internal in PyPy will
            # reject anything above 0x00110000. I don't think there is a
            # way to replicate CPython behaviour without resorting to C.
            x_uni = x[:UNICODE_SIZE].decode("unicode_internal")
        else:
            raise TypeError("array item must be unicode character")
    elif isinstance(x, unicode):
        x_uni = x
    else:
        raise TypeError("array item must be unicode character")
    if len(x_uni) != 1:
        raise TypeError("array item must be unicode character")
    return x_uni

def h_type_check(x):
    return general_int_type_check(x, -32768, 32767)

def HH_type_check(x):
    return general_int_type_check(x, 0, 65535)

def i_type_check(x):
    return general_int_type_check(x, -2147483648, 2147483647)

def general_long_type_check(x, lower_bound, upper_bound):
    if not (isinstance(x, int) or isinstance(x, long) or isinstance(x, float)):
        raise TypeError("an integer is required")
    x_long = long(x)
    if not (x_long >= lower_bound and x_long <= upper_bound):
        raise OverflowError("integer/long is not in the allowed range")
    return x_long

def II_type_check(x):
    return general_long_type_check(x, 0, 4294967295L)

l_type_check = i_type_check

LL_type_check = II_type_check

def f_type_check(x):
    if not (isinstance(x, int) or isinstance(x, long) or isinstance(x, float)):
        raise TypeError("a float is required")
    x_float = float(x)
    # XXX This is not exactly a nice way of checking bounds. Formerly, I tried
    # this: return unpack("f", pack("f", x_float))[0]
    # Which works in CPython, but PyPy struct is not currently intelligent
    # enough to handle this.
    if x_float > 3.4028e38:
        x_float = 3.4028e38
    elif x_float < -3.4028e38:
        x_float = -3.4028e38
    return x_float

def d_type_check(x):
    if not (isinstance(x, int) or isinstance(x, long) or isinstance(x, float)):
        raise TypeError("a float is required")
    return float(x)

def dummy_type_check(x):
    return x

# XXX Assuming fixed sizes of the different types, independent of platform.
# These are the same assumptions that struct makes at the moment.
descriptors = {
    'c' : ('char', 1, c_type_check),
    'b' : ('signed char', 1, b_type_check),
    'B' : ('unsigned char', 1, BB_type_check),
    'u' : ('Py_UNICODE', UNICODE_SIZE, u_type_check),
    'h' : ('signed short', 2, h_type_check),
    'H' : ('unsigned short', 2, HH_type_check),
    'i' : ('signed int', 4, i_type_check),
    'I' : ('unsigned int', 4, II_type_check),
    'l' : ('signed long', 4, l_type_check),
    'L' : ('unsigned long', 4, LL_type_check),
    'f' : ('float', 4, f_type_check),
    'd' : ('double', 8, d_type_check),
}

class array(object):
    """array(typecode [, initializer]) -> array
    
    Return a new array whose items are restricted by typecode, and
    initialized from the optional initializer value, which must be a list,
    string. or iterable over elements of the appropriate type.
    
    Arrays represent basic values and behave very much like lists, except
    the type of objects stored in them is constrained.
    
    Methods:
    
    append() -- append a new item to the end of the array
    buffer_info() -- return information giving the current memory info
    byteswap() -- byteswap all the items of the array
    count() -- return number of occurences of an object
    extend() -- extend array by appending multiple elements from an iterable
    fromfile() -- read items from a file object
    fromlist() -- append items from the list
    fromstring() -- append items from the string
    index() -- return index of first occurence of an object
    insert() -- insert a new item into the array at a provided position
    pop() -- remove and return item (default last)
    read() -- DEPRECATED, use fromfile()
    remove() -- remove first occurence of an object
    reverse() -- reverse the order of the items in the array
    tofile() -- write all items to a file object
    tolist() -- return the array converted to an ordinary list
    tostring() -- return the array converted to a string
    write() -- DEPRECATED, use tofile()
    
    Attributes:
    
    typecode -- the typecode character used to create the array
    itemsize -- the length in bytes of one array item
    """
    __slots__ = ["typecode", "itemsize", "_data", "_descriptor", "__weakref__"]

    def __new__(cls, typecode, initializer=[]):
        self = object.__new__(cls)
        if not isinstance(typecode, str) or len(typecode) != 1:
            raise TypeError(
                     "array() argument 1 must be char, not %s" % type(typecode))
        if not descriptors.has_key(typecode):
            raise ValueError(
                  "bad typecode (must be c, b, B, u, h, H, i, I, l, L, f or d)")
        self._descriptor = descriptors[typecode]
        self._data = []
        self.typecode = typecode
        self.itemsize = self._descriptor[1]
        if isinstance(initializer, list):
            self.fromlist(initializer)
        elif isinstance(initializer, str):
            self.fromstring(initializer)
        elif isinstance(initializer, unicode) and self.typecode == "u":
            self.fromunicode(initializer)
        else:
            self.extend(initializer)
        return self

    ##### array-specific operations

    def fromfile(self, f, n):
        """Read n objects from the file object f and append them to the end of
        the array. Also called as read."""
        if not isinstance(f, file):
            raise TypeError("arg1 must be open file")
        for i in range(n):
            item = f.read(self.itemsize)
            if len(item) < self.itemsize:
                raise EOFError("not enough items in file")
            self.fromstring(item)

    def fromlist(self, l):
        """Append items to array from list."""
        if not isinstance(l, list):
            raise TypeError("arg must be list")
        self._fromiterable(l)
        
    def fromstring(self, s):
        from struct import pack, unpack
        """Appends items from the string, interpreting it as an array of machine
        values, as if it had been read from a file using the fromfile()
        method)."""
        if isinstance(s, unicode):
            s = str(s)
        if not (isinstance(s, str) or isinstance(s, buffer)):
            raise TypeError(
                   "fromstring() argument 1 must be string or read-only buffer")
        if len(s) % self.itemsize != 0:
            raise ValueError("string length not a multiple of item size")
        items = []
        if self.typecode == "u":
            for i in range(0, len(s), self.itemsize):
                items.append(u_type_check(s[i:i + self.itemsize]))
        else:
            for i in range(0, len(s), self.itemsize):
                item = unpack(self.typecode, s[i:i + self.itemsize])[0]
                # the item needn't be type checked if unpack succeeded
                items.append(item)
        self._data.extend(items)

    def fromunicode(self, ustr):
        """Extends this array with data from the unicode string ustr. The array
        must be a type 'u' array; otherwise a ValueError is raised. Use
        array.fromstring(ustr.encode(...)) to append Unicode data to an array of
        some other type."""
        if not self.typecode == "u":
            raise ValueError(
                          "fromunicode() may only be called on type 'u' arrays")
        if isinstance(ustr, unicode):
            self._fromiterable(ustr)
        elif isinstance(ustr, str) or isinstance(ustr, buffer):
            # CPython strangely truncates string arguments at multiples of the
            # unicode byte size ...
            trunc_s = ustr[:len(ustr) - (len(ustr) % self.itemsize)]
            self.fromstring(trunc_s)
        else:
            raise TypeError(
                  "fromunicode() argument 1 must be string or read-only buffer")

    def tofile(self, f):
        """Write all items (as machine values) to the file object f.  Also
        called as write."""
        if not isinstance(f, file):
            raise TypeError("arg must be open file")
        f.write(self.tostring())
        
    def tolist(self):
        """Convert array to an ordinary list with the same items."""
        return self._data[:]

    def tostring(self):
        from struct import pack, unpack
        """Convert the array to an array of machine values and return the string
        representation."""
        if self.typecode == "u":
            return u"".join(self._data).encode("unicode_internal")
        else:
            strings = []
            for item in self._data:
                strings.append(pack(self.typecode, item))
            return "".join(strings)

    def tounicode(self):
        """Convert the array to a unicode string. The array must be a type 'u'
        array; otherwise a ValueError is raised. Use array.tostring().decode()
        to obtain a unicode string from an array of some other type."""
        if self.typecode != "u":
            raise ValueError("tounicode() may only be called on type 'u' arrays")
        return u"".join(self._data)

    def byteswap(self):
        """Byteswap all items of the array.  If the items in the array are not
        1, 2, 4, or 8 bytes in size, RuntimeError is raised."""
        if self.itemsize not in [1, 2, 4, 8]:
            raise RuntimeError("byteswap not supported for this array")
        bytes = self.tostring()
        swapped = []
        for offset in range(0, len(self._data) * self.itemsize, self.itemsize):
            l = list(bytes[offset:offset + self.itemsize])
            l.reverse()
            swapped += l
        self._data = []
        self.fromstring("".join(swapped))

    def buffer_info(self):
        """Return a tuple (address, length) giving the current memory address
        and the length in items of the buffer used to hold array's contents. The
        length should be multiplied by the itemsize attribute to calculate the
        buffer length in bytes. In PyPy the return values are not really
        meaningful."""
        return (0, len(self._data))
    
    read = fromfile

    write = tofile

    ##### general object protocol
    
    def __repr__(self):
        if len(self._data) == 0:
            return "array('%s')" % self.typecode
        elif self.typecode == "c":
            return "array('%s', %s)" % (self.typecode, repr(self.tostring()))
        elif self.typecode == "u":
            return "array('%s', %s)" % (self.typecode, repr(self.tounicode()))
        else:
            return "array('%s', %s)" % (self.typecode, repr(self.tolist()))

    def __copy__(self):
        a = array(self.typecode)
        a._data = self._data[:]
        return a

    def __eq__(self, other):
        if not isinstance(other, array):
            return NotImplemented
        return self._data == other._data

    def __ne__(self, other):
        if not isinstance(other, array):
            return NotImplemented
        return self._data != other._data

    def __lt__(self, other):
        if not isinstance(other, array):
            return NotImplemented
        return self._data < other._data

    def __gt__(self, other):
        if not isinstance(other, array):
            return NotImplemented
        return self._data > other._data

    def __le__(self, other):
        if not isinstance(other, array):
            return NotImplemented
        return self._data <= other._data

    def __ge__(self, other):
        if not isinstance(other, array):
            return NotImplemented
        return self._data >= other._data

    ##### list methods
    
    def append(self, x):
        """Append new value x to the end of the array."""
        x_checked = self._type_check(x)
        self._data.append(x_checked)

    def count(self, x):
        """Return number of occurences of x in the array."""
        return self._data.count(x)

    def extend(self, iterable):
        """Append items to the end of the array."""
        if isinstance(iterable, array) \
                                    and not self.typecode == iterable.typecode:
            raise TypeError("can only extend with array of same kind")
        self._fromiterable(iterable)

    def index(self, x):
        """Return index of first occurence of x in the array."""
        return self._data.index(x)
    
    def insert(self, i, x):
        """Insert a new item x into the array before position i."""
        x_checked = self._type_check(x)
        self._data.insert(i, x_checked)
        
    def pop(self, i=-1):
        """Return the i-th element and delete it from the array. i defaults to
        -1."""
        return self._data.pop(i)
        
    def remove(self, x):
        """Remove the first occurence of x in the array."""
        self._data.remove(x)
        
    def reverse(self):
        """Reverse the order of the items in the array."""
        self._data.reverse()

    ##### list protocol
    
    def __len__(self):
        return len(self._data)
    
    def __add__(self, other):
        if not isinstance(other, array):
            raise TypeError("can only append array to array")
        if self.typecode != other.typecode:
            raise TypeError("bad argument type for built-in operation")
        return array(self.typecode, self._data + other._data)

    def __mul__(self, repeat):
        return array(self.typecode, self._data * repeat)

    __rmul__ = __mul__

    def __getitem__(self, i):
        if isinstance(i, slice):
            sliced = array(self.typecode)
            sliced._data = self._data[i]
            return sliced
        return self._data[i]

    def __getslice__(self, i, j):
        return self.__getitem__(slice(i, j))

    def __setitem__(self, i, x):
        if isinstance(i, slice):
            if not isinstance(x, array):
                raise TypeError("can only assign array to array slice")
            if x.typecode != self.typecode:
                raise TypeError("bad argument type for built-in operation")
            self._data[i] = x._data
            return
        if not (isinstance(i, int) or isinstance(i, long)):
            raise TypeError("list indices must be integers")
        if i >= len(self._data) or i < -len(self._data):
            raise IndexError("array assignment index out of range")
        x_checked = self._type_check(x)
        self._data[i] = x_checked

    def __setslice__(self, i, j, x):
        self.__setitem__(slice(i, j), x)

    def __delitem__(self, i):
        del self._data[i]

    def __delslice__(self, i, j):
        self.__delitem__(slice(i, j))

    def __contains__(self, item):
        return item in self._data

    def __iadd__(self, other):
        if not isinstance(other, array):
            raise TypeError("can only extend array with array")
        self.extend(other)
        return self

    def __imul__(self, repeat):
        self._data *= repeat
        return self

    def __iter__(self):
        return iter(self._data)

    ##### internal methods
    
    def _type_check(self, x):
        return self._descriptor[2](x)

    def _fromiterable(self, iterable):
        items = []
        for item in iterable:
            item_checked = self._type_check(item)
            items.append(item_checked)
        self._data.extend(items)

ArrayType = array
