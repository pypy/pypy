#
# This module is a pure Python version of pypy.module.struct.
# It is only imported if the vastly faster pypy.module.struct is not
# compiled in.  For now we keep this version for reference and
# because pypy.module.struct is not ootype-backend-friendly yet.
#

"""Functions to convert between Python values and C structs.
Python strings are used to hold the data representing the C struct
and also as format strings to describe the layout of data in the C struct.

The optional first format char indicates byte order, size and alignment:
 @: native order, size & alignment (default)
 =: native order, std. size & alignment
 <: little-endian, std. size & alignment
 >: big-endian, std. size & alignment
 !: same as >

The remaining chars indicate types of args and must match exactly;
these can be preceded by a decimal repeat count:
   x: pad byte (no data);
   c:char;
   b:signed byte;
   B:unsigned byte;
   h:short;
   H:unsigned short;
   i:int;
   I:unsigned int;
   l:long;
   L:unsigned long;
   f:float;
   d:double.
Special cases (preceding decimal count indicates length):
   s:string (array of char); p: pascal string (with count byte).
Special case (only available in native format):
   P:an integer type that is wide enough to hold a pointer.
Special case (not in native mode unless 'long long' in platform C):
   q:long long;
   Q:unsigned long long
Whitespace between formats is ignored.

The variable struct.error is an exception raised on errors."""

import math, sys

# TODO: XXX Find a way to get information on native sizes and alignments
class StructError(Exception):
    pass
error = StructError
def unpack_int(data,index,size,le):
    bytes = [ord(b) for b in data[index:index+size]]
    if le == 'little':
        bytes.reverse()
    number = 0L
    for b in bytes:
        number = number << 8 | b
    return int(number)

def unpack_signed_int(data,index,size,le):
    number = unpack_int(data,index,size,le)
    max = 2**(size*8)
    if number > 2**(size*8 - 1) - 1:
        number = int(-1*(max - number))
    return number

INFINITY = 1e200 * 1e200
NAN = INFINITY / INFINITY

def unpack_float(data,index,size,le):
    bytes = [ord(b) for b in data[index:index+size]]
    if len(bytes) != size:
        raise StructError,"Not enough data to unpack"
    if max(bytes) == 0:
        return 0.0
    if le == 'big':
        bytes.reverse()
    if size == 4:
        bias = 127
        exp = 8
        prec = 23
    else:
        bias = 1023
        exp = 11
        prec = 52
    mantissa = long(bytes[size-2] & (2**(15-exp)-1))
    for b in bytes[size-3::-1]:
        mantissa = mantissa << 8 | b
    mantissa = 1 + (1.0*mantissa)/(2**(prec))
    mantissa /= 2
    e = (bytes[-1] & 0x7f) << (exp - 7)
    e += (bytes[size-2] >> (15 - exp)) & (2**(exp - 7) -1)
    e -= bias
    e += 1
    sign = bytes[-1] & 0x80
    if e == bias + 2:
        if mantissa == 0.5:
            number = INFINITY
        else:
            return NAN
    else:
        number = math.ldexp(mantissa,e)
    if sign : number *= -1
    return number

def unpack_char(data,index,size,le):
    return data[index:index+size]

def pack_int(number,size,le):
    x=number
    res=[]
    for i in range(size):
        res.append(chr(x&0xff))
        x >>= 8
    if le == 'big':
        res.reverse()
    return ''.join(res)

def pack_signed_int(number,size,le):
    if not isinstance(number, (int,long)):
        raise StructError,"argument for i,I,l,L,q,Q,h,H must be integer"
    if  number > 2**(8*size-1)-1 or number < -1*2**(8*size-1):
        raise OverflowError,"Number:%i too large to convert" % number
    return pack_int(number,size,le)

def pack_unsigned_int(number,size,le):
    if not isinstance(number, (int,long)):
        raise StructError,"argument for i,I,l,L,q,Q,h,H must be integer"
    if number < 0:
        raise TypeError,"can't convert negative long to unsigned"
    if number > 2**(8*size)-1:
        raise OverflowError,"Number:%i too large to convert" % number
    return pack_int(number,size,le)

def pack_char(char,size,le):
    return str(char)

def isinf(x):
    return x != 0.0 and x / 2 == x
def isnan(v):
    return v != v*1.0 or (v == 1.0 and v == 2.0)

def pack_float(number, size, le):
    if size == 4:
        bias = 127
        exp = 8
        prec = 23
    else:
        bias = 1023
        exp = 11
        prec = 52

    if isnan(number):
        sign = 0x80
        man, e = 1.5, bias + 1
    else:
        if number < 0:
            sign = 0x80
            number *= -1
        elif number == 0.0:
            return '\x00' * size
        else:
            sign = 0x00
        if isinf(number):
            man, e = 1.0, bias + 1
        else:
            man, e = math.frexp(number)

    result = []
    if 0.5 <= man and man < 1.0:
        man *= 2
        e -= 1
    man -= 1
    e += bias
    power_of_two = 1 << prec
    mantissa = int(power_of_two * man + 0.5)
    if mantissa >> prec :
        mantissa = 0
        e += 1

    for i in range(size-2):
        result.append(chr(mantissa & 0xff))
        mantissa >>= 8
    x = (mantissa & ((1<<(15-exp))-1)) | ((e & ((1<<(exp-7))-1))<<(15-exp))
    result.append(chr(x))
    x = sign | e >> (exp - 7)
    result.append(chr(x))
    if le == 'big':
        result.reverse()
    return ''.join(result)

big_endian_format = {
    'x':{ 'size' : 1, 'alignment' : 0, 'pack' : None, 'unpack' : None},
    'b':{ 'size' : 1, 'alignment' : 0, 'pack' : pack_signed_int, 'unpack' : unpack_signed_int},
    'B':{ 'size' : 1, 'alignment' : 0, 'pack' : pack_unsigned_int, 'unpack' : unpack_int},
    'c':{ 'size' : 1, 'alignment' : 0, 'pack' : pack_char, 'unpack' : unpack_char},
    's':{ 'size' : 1, 'alignment' : 0, 'pack' : None, 'unpack' : None},
    'p':{ 'size' : 1, 'alignment' : 0, 'pack' : None, 'unpack' : None},
    'h':{ 'size' : 2, 'alignment' : 0, 'pack' : pack_signed_int, 'unpack' : unpack_signed_int},
    'H':{ 'size' : 2, 'alignment' : 0, 'pack' : pack_unsigned_int, 'unpack' : unpack_int},
    'i':{ 'size' : 4, 'alignment' : 0, 'pack' : pack_signed_int, 'unpack' : unpack_signed_int},
    'I':{ 'size' : 4, 'alignment' : 0, 'pack' : pack_unsigned_int, 'unpack' : unpack_int},
    'l':{ 'size' : 4, 'alignment' : 0, 'pack' : pack_signed_int, 'unpack' : unpack_signed_int},
    'L':{ 'size' : 4, 'alignment' : 0, 'pack' : pack_unsigned_int, 'unpack' : unpack_int},
    'q':{ 'size' : 8, 'alignment' : 0, 'pack' : pack_signed_int, 'unpack' : unpack_signed_int},
    'Q':{ 'size' : 8, 'alignment' : 0, 'pack' : pack_unsigned_int, 'unpack' : unpack_int},
    'f':{ 'size' : 4, 'alignment' : 0, 'pack' : pack_float, 'unpack' : unpack_float},
    'd':{ 'size' : 8, 'alignment' : 0, 'pack' : pack_float, 'unpack' : unpack_float},
    }
default = big_endian_format
formatmode={ '<' : (default, 'little'),
             '>' : (default, 'big'),
             '!' : (default, 'big'),
             '=' : (default, sys.byteorder),
             '@' : (default, sys.byteorder)
            }

def getmode(fmt):
    try:
        formatdef,endianness = formatmode[fmt[0]]
        index = 1
    except KeyError:
        formatdef,endianness = formatmode['@']
        index = 0
    return formatdef,endianness,index
def getNum(fmt,i):
    num=None
    cur = fmt[i]
    while ('0'<= cur ) and ( cur <= '9'):
        if num == None:
            num = int(cur)
        else:
            num = 10*num + int(cur)
        i += 1
        cur = fmt[i]
    return num,i

def calcsize(fmt):
    """calcsize(fmt) -> int
    Return size of C struct described by format string fmt.
    See struct.__doc__ for more on format strings."""

    formatdef,endianness,i = getmode(fmt)
    num = 0
    result = 0
    while i<len(fmt):
        num,i = getNum(fmt,i)
        cur = fmt[i]
        try:
            format = formatdef[cur]
        except KeyError:
            raise StructError,"%s is not a valid format"%cur
        if num != None :
            result += num*format['size']
        else:
            result += format['size']
        num = 0
        i += 1
    return result

def pack(fmt,*args):
    """pack(fmt, v1, v2, ...) -> string
       Return string containing values v1, v2, ... packed according to fmt.
       See struct.__doc__ for more on format strings."""
    formatdef,endianness,i = getmode(fmt)
    args = list(args)
    n_args = len(args)
    result = []
    while i<len(fmt):
        num,i = getNum(fmt,i)
        cur = fmt[i]
        try:
            format = formatdef[cur]
        except KeyError:
            raise StructError,"%s is not a valid format"%cur
        if num == None :
            num_s = 0
            num = 1
        else:
            num_s = num

        if cur == 'x':
            result += ['\0'*num]
        elif cur == 's':
            if isinstance(args[0], str):
                padding = num - len(args[0])
                result += [args[0][:num] + '\0'*padding]
                args.pop(0)
            else:
                raise StructError,"arg for string format not a string"
        elif cur == 'p':
            if isinstance(args[0], str):
                padding = num - len(args[0]) - 1

                if padding > 0:
                    result += [chr(len(args[0])) + args[0][:num-1] + '\0'*padding]
                else:
                    if num<255:
                        result += [chr(num-1) + args[0][:num-1]]
                    else:
                        result += [chr(255) + args[0][:num-1]]
                args.pop(0)
            else:
                raise StructError,"arg for string format not a string"

        else:
            if len(args) < num:
                raise StructError,"insufficient arguments to pack"
            for var in args[:num]:
                result += [format['pack'](var,format['size'],endianness)]
            args=args[num:]
        num = None
        i += 1
    if len(args) != 0:
        raise StructError,"too many arguments for pack format"
    return ''.join(result)

def unpack(fmt,data):
    """unpack(fmt, string) -> (v1, v2, ...)
       Unpack the string, containing packed C structure data, according
       to fmt.  Requires len(string)==calcsize(fmt).
       See struct.__doc__ for more on format strings."""
    formatdef,endianness,i = getmode(fmt)
    j = 0
    num = 0
    result = []
    length= calcsize(fmt)
    if length != len (data):
        raise StructError,"unpack str size does not match format"
    while i<len(fmt):
        num,i=getNum(fmt,i)
        cur = fmt[i]
        i += 1
        try:
            format = formatdef[cur]
        except KeyError:
            raise StructError,"%s is not a valid format"%cur

        if not num :
            num = 1

        if cur == 'x':
            j += num
        elif cur == 's':
            result.append(data[j:j+num])
            j += num
        elif cur == 'p':
            n=ord(data[j])
            if n >= num:
                n = num-1
            result.append(data[j+1:j+n+1])
            j += num
        else:
            for n in range(num):
                result += [format['unpack'](data,j,format['size'],endianness)]
                j += format['size']

    return tuple(result)

def pack_into(fmt, buf, offset, *args):
    data = pack(fmt, *args)
    buffer(buf)[offset:offset+len(data)] = data

def unpack_from(fmt, buf, offset=0):
    size = calcsize(fmt)
    data = buffer(buf)[offset:offset+size]
    if len(data) != size:
        raise error("unpack_from requires a buffer of at least %d bytes"
                    % (size,))
    return unpack(fmt, data)
