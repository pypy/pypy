"""
Native type codes.
The table 'native_fmttable' is also used by pypy.module.array.interp_array.
"""
import struct
from pypy.rlib.rstruct import standardfmttable as std
from pypy.rlib.rstruct.error import StructError
from pypy.rpython.tool import rffi_platform
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib.rarithmetic import r_singlefloat
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.rlib.objectmodel import specialize

native_is_bigendian = struct.pack("=i", 1) == struct.pack(">i", 1)

native_fmttable = {
    'x': std.standard_fmttable['x'],
    'c': std.standard_fmttable['c'],
    's': std.standard_fmttable['s'],
    'p': std.standard_fmttable['p'],
    }

# ____________________________________________________________

double_buf = lltype.malloc(rffi.DOUBLEP.TO, 1, flavor='raw', immortal=True)
float_buf = lltype.malloc(rffi.FLOATP.TO, 1, flavor='raw', immortal=True)

def pack_double(fmtiter):
    doubleval = fmtiter.accept_float_arg()
    double_buf[0] = doubleval
    p = rffi.cast(rffi.CCHARP, double_buf)
    for i in range(sizeof_double):
        fmtiter.result.append(p[i])

@specialize.argtype(0)
def unpack_double(fmtiter):
    input = fmtiter.read(sizeof_double)
    p = rffi.cast(rffi.CCHARP, double_buf)
    for i in range(sizeof_double):
        p[i] = input[i]
    doubleval = double_buf[0]
    fmtiter.appendobj(doubleval)

def pack_float(fmtiter):
    doubleval = fmtiter.accept_float_arg()
    floatval = r_singlefloat(doubleval)
    float_buf[0] = floatval
    p = rffi.cast(rffi.CCHARP, float_buf)
    for i in range(sizeof_float):
        fmtiter.result.append(p[i])

@specialize.argtype(0)
def unpack_float(fmtiter):
    input = fmtiter.read(sizeof_float)
    p = rffi.cast(rffi.CCHARP, float_buf)
    for i in range(sizeof_float):
        p[i] = input[i]
    floatval = float_buf[0]
    doubleval = float(floatval)
    fmtiter.appendobj(doubleval)

# ____________________________________________________________
#
# Use rffi_platform to get the native sizes and alignments from the C compiler

def setup():
    INSPECT = {'b': 'signed char',
               'h': 'signed short',
               'i': 'signed int',
               'l': 'signed long',
               'q': 'signed long long',
               'B': 'unsigned char',
               'H': 'unsigned short',
               'I': 'unsigned int',
               'L': 'unsigned long',
               'Q': 'unsigned long long',
               'P': 'char *',
               'f': 'float',
               'd': 'double',
               '?': '_Bool',
               }

    pre_include_bits = ["""
        #ifdef _MSC_VER
        #define _Bool char
        #endif"""]
    field_names = dict.fromkeys(INSPECT)
    for fmtchar, ctype in INSPECT.iteritems():
        field_name = ctype.replace(" ", "_").replace("*", "star")
        field_names[fmtchar] = field_name
        pre_include_bits.append("""
            struct about_%s {
                char pad;
                %s field;
            };
        """ % (field_name, ctype))

    class CConfig:
        _compilation_info_ = ExternalCompilationInfo(
            pre_include_bits = pre_include_bits
        )

    for fmtchar, ctype in INSPECT.items():
        setattr(CConfig, field_names[fmtchar], rffi_platform.Struct(
            "struct about_%s" % (field_names[fmtchar],),
            [('field', lltype.FixedSizeArray(rffi.CHAR, 1))]))

    cConfig = rffi_platform.configure(CConfig)

    for fmtchar, ctype in INSPECT.items():
        S = cConfig[field_names[fmtchar]]
        alignment = rffi.offsetof(S, 'c_field')
        size = rffi.sizeof(S.c_field)
        signed = 'a' <= fmtchar <= 'z'

        if fmtchar == 'f':
            pack = pack_float
            unpack = unpack_float
        elif fmtchar == 'd':
            pack = pack_double
            unpack = unpack_double
        elif fmtchar == '?':
            pack = std.pack_bool
            unpack = std.unpack_bool
        else:
            pack = std.make_int_packer(size, signed, True)
            unpack = std.make_int_unpacker(size, signed)

        native_fmttable[fmtchar] = {'size': size,
                                    'alignment': alignment,
                                    'pack': pack,
                                    'unpack': unpack}

setup()

sizeof_double = native_fmttable['d']['size']
sizeof_float  = native_fmttable['f']['size']

# ____________________________________________________________
#
# A PyPy extension: accepts the 'u' format character in native mode,
# just like the array module does.  (This is actually used in the
# implementation of our interp-level array module.)

from pypy.rlib.rstruct import unichar

def pack_unichar(fmtiter):
    unistr = fmtiter.accept_unicode_arg()
    if len(unistr) != 1:
        raise StructError("expected a unicode string of length 1")
    c = unistr[0]   # string->char conversion for the annotator
    unichar.pack_unichar(c, fmtiter.result)

@specialize.argtype(0)
def unpack_unichar(fmtiter):
    data = fmtiter.read(unichar.UNICODE_SIZE)
    fmtiter.appendobj(unichar.unpack_unichar(data))

native_fmttable['u'] = {'size': unichar.UNICODE_SIZE,
                        'alignment': unichar.UNICODE_SIZE,
                        'pack': pack_unichar,
                        'unpack': unpack_unichar,
                        }
