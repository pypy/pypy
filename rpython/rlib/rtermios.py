# This are here only because it's always better safe than sorry.
# The issue is that from-time-to-time CPython's termios.tcgetattr
# returns list of mostly-strings of length one, but with few ints
# inside, so we make sure it works

from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rtyper.tool import rffi_platform
from rpython.translator.tool.cbuild import ExternalCompilationInfo

from rpython.rlib import rposix

eci = ExternalCompilationInfo(
    includes = ['termios.h', 'unistd.h']
)

class CConfig:
    _compilation_info_ = eci
    NCCS = rffi_platform.DefinedConstantInteger('NCCS')
    TCSANOW = rffi_platform.ConstantInteger('TCSANOW')
    _HAVE_STRUCT_TERMIOS_C_ISPEED = rffi_platform.Defined(
            '_HAVE_STRUCT_TERMIOS_C_ISPEED')
    _HAVE_STRUCT_TERMIOS_C_OSPEED = rffi_platform.Defined(
            '_HAVE_STRUCT_TERMIOS_C_OSPEED')

c_config = rffi_platform.configure(CConfig)
NCCS = c_config['NCCS']
TCSANOW = c_config['TCSANOW']

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

c_tcsetattr = c_external('tcsetattr', [rffi.INT, rffi.INT, TERMIOSP], rffi.INT)
c_cfsetispeed = c_external('cfsetispeed', [TERMIOSP, SPEED_T], rffi.INT)
c_cfsetospeed = c_external('cfsetospeed', [TERMIOSP, SPEED_T], rffi.INT)


def tcgetattr(fd):
    # NOT_RPYTHON
    import termios
    try:
        lst = list(termios.tcgetattr(fd))
    except termios.error, e:
        raise OSError(*e.args)
    cc = lst[-1]
    next_cc = []
    for c in cc:
        if isinstance(c, int):
            next_cc.append(chr(c))
        else:
            next_cc.append(c)
    lst[-1] = next_cc
    return tuple(lst)


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
