# This are here only because it's always better safe than sorry.
# The issue is that from-time-to-time CPython's termios.tcgetattr
# returns list of mostly-strings of length one, but with few ints
# inside, so we make sure it works

from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rtyper.tool import rffi_platform
from rpython.translator.tool.cbuild import ExternalCompilationInfo

from rpython.rlib import rposix
from rpython.rlib.rarithmetic import intmask

eci = ExternalCompilationInfo(
    includes = ['termios.h', 'unistd.h']
)

class CConfig:
    _compilation_info_ = eci
    NCCS = rffi_platform.DefinedConstantInteger('NCCS')
    _HAVE_STRUCT_TERMIOS_C_ISPEED = rffi_platform.Defined(
            '_HAVE_STRUCT_TERMIOS_C_ISPEED')
    _HAVE_STRUCT_TERMIOS_C_OSPEED = rffi_platform.Defined(
            '_HAVE_STRUCT_TERMIOS_C_OSPEED')

    TCSANOW = rffi_platform.ConstantInteger('TCSANOW')
    TCIOFLUSH = rffi_platform.ConstantInteger('TCIOFLUSH')
    TCOON = rffi_platform.ConstantInteger('TCOON')



c_config = rffi_platform.configure(CConfig)
NCCS = c_config['NCCS']

TCSANOW = c_config['TCSANOW']
TCIOFLUSH = c_config['TCIOFLUSH']
TCOON = c_config['TCOON']

TCFLAG_T = rffi.UINT
CC_T = rffi.UCHAR
SPEED_T = rffi.UINT

_add = []
if c_config['_HAVE_STRUCT_TERMIOS_C_ISPEED']:
    _add.append(('c_ispeed', SPEED_T))
if c_config['_HAVE_STRUCT_TERMIOS_C_OSPEED']:
    _add.append(('c_ospeed', SPEED_T))
TERMIOSP = rffi.CStructPtr('termios', ('c_iflag', TCFLAG_T), ('c_oflag', TCFLAG_T),
                           ('c_cflag', TCFLAG_T), ('c_lflag', TCFLAG_T),
                           ('c_line', CC_T),
                           ('c_cc', lltype.FixedSizeArray(CC_T, NCCS)), *_add)

def c_external(name, args, result):
    return rffi.llexternal(name, args, result, compilation_info=eci)

c_tcgetattr = c_external('tcgetattr', [rffi.INT, TERMIOSP], rffi.INT)
c_tcsetattr = c_external('tcsetattr', [rffi.INT, rffi.INT, TERMIOSP], rffi.INT)
c_cfgetispeed = c_external('cfgetispeed', [TERMIOSP], SPEED_T)
c_cfgetospeed = c_external('cfgetospeed', [TERMIOSP], SPEED_T)
c_cfsetispeed = c_external('cfsetispeed', [TERMIOSP, SPEED_T], rffi.INT)
c_cfsetospeed = c_external('cfsetospeed', [TERMIOSP, SPEED_T], rffi.INT)

c_tcsendbreak = c_external('tcsendbreak', [rffi.INT, rffi.INT], rffi.INT)
c_tcdrain = c_external('tcdrain', [rffi.INT], rffi.INT)
c_tcflush = c_external('tcflush', [rffi.INT, rffi.INT], rffi.INT)
c_tcflow = c_external('tcflow', [rffi.INT, rffi.INT], rffi.INT)


def tcgetattr(fd):
    with lltype.scoped_alloc(TERMIOSP.TO) as c_struct:
        if c_tcgetattr(fd, c_struct) < 0:
            raise OSError(rposix.get_errno(), 'tcgetattr failed')
        cc = [chr(c_struct.c_c_cc[i]) for i in range(NCCS)]
        ispeed = c_cfgetispeed(c_struct)
        ospeed = c_cfgetospeed(c_struct)
        result = (intmask(c_struct.c_c_iflag), intmask(c_struct.c_c_oflag),
                  intmask(c_struct.c_c_cflag), intmask(c_struct.c_c_lflag),
                  intmask(ispeed), intmask(ospeed), cc)
        return result


# This function is not an exact replacement of termios.tcsetattr:
# the last attribute must be a list of chars.
def tcsetattr(fd, when, attributes):
    with lltype.scoped_alloc(TERMIOSP.TO) as c_struct:
        rffi.setintfield(c_struct, 'c_c_iflag', attributes[0])
        rffi.setintfield(c_struct, 'c_c_oflag', attributes[1])
        rffi.setintfield(c_struct, 'c_c_cflag', attributes[2])
        rffi.setintfield(c_struct, 'c_c_lflag', attributes[3])
        ispeed = attributes[4]
        ospeed = attributes[5]
        cc = attributes[6]
        for i in range(NCCS):
            c_struct.c_c_cc[i] = rffi.r_uchar(ord(cc[i][0]))
        if c_cfsetispeed(c_struct, ispeed) < 0:
            raise OSError(rposix.get_errno(), 'tcsetattr failed')
        if c_cfsetospeed(c_struct, ospeed) < 0:
            raise OSError(rposix.get_errno(), 'tcsetattr failed')
        if c_tcsetattr(fd, when, c_struct) < 0:
            raise OSError(rposix.get_errno(), 'tcsetattr failed')

def tcsendbreak(fd, duration):
    if c_tcsendbreak(fd, duration) < 0:
        raise OSError(rposix.get_errno(), 'tcsendbreak failed')

def tcdrain(fd):
    if c_tcdrain(fd) < 0:
        raise OSError(rposix.get_errno(), 'tcdrain failed')

def tcflush(fd, queue_selector):
    if c_tcflush(fd, queue_selector) < 0:
        raise OSError(rposix.get_errno(), 'tcflush failed')

def tcflow(fd, action):
    if c_tcflow(fd, action) < 0:
        raise OSError(rposix.get_errno(), 'tcflow failed')
