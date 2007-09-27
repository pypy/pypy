import struct
from pypy.module.struct import standardfmttable as std
from pypy.rpython.tool import rffi_platform
from pypy.rpython.lltypesystem import lltype, rffi

native_is_bigendian = struct.pack("=i", 1) == struct.pack(">i", 1)

native_fmttable = {
    'x': std.standard_fmttable['x'],
    'c': std.standard_fmttable['c'],
    's': std.standard_fmttable['s'],
    'p': std.standard_fmttable['p'],
    }

# ____________________________________________________________
#
# Use rffi_platform to get the native sizes and alignments from the C compiler

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
           }

class CConfig:
    _header_ = ""

for fmtchar, ctype in INSPECT.items():
    CConfig._header_ += """
        struct about_%s {
            char pad;
            %s field;
        };
    """ % (fmtchar, ctype)
    setattr(CConfig, fmtchar, rffi_platform.Struct(
        "struct about_%s" % (fmtchar,),
        [('field', lltype.FixedSizeArray(rffi.CHAR, 1))]))

cConfig = rffi_platform.configure(CConfig)

for fmtchar, ctype in INSPECT.items():
    S = cConfig[fmtchar]
    alignment = rffi.offsetof(S, 'c_field')
    size = rffi.sizeof(S.c_field)
    signed = 'a' <= fmtchar <= 'z'

    native_fmttable[fmtchar] = {
        'size': size,
        'alignment': alignment,
        'pack': std.make_int_packer(size, signed),     # XXX 'f', 'd'
        'unpack': std.make_int_unpacker(size, signed),
        }
