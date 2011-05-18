
"""
The low-level implementation of termios module
note that this module should only be imported when
termios module is there
"""

import termios
from pypy.rpython.lltypesystem import rffi
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.extfunc import lazy_register, register_external
from pypy.rlib.rarithmetic import intmask
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.annotation import model as annmodel
from pypy.rpython import rclass
from pypy.rlib import rtermios, rposix
from pypy.rpython.tool import rffi_platform
from pypy.translator.tool.cbuild import ExternalCompilationInfo

eci = ExternalCompilationInfo(
    includes = ['termios.h', 'unistd.h']
)

class CConfig:
    _compilation_info_ = eci
    NCCS = rffi_platform.DefinedConstantInteger('NCCS')

NCCS = rffi_platform.configure(CConfig)['NCCS']

TCFLAG_T = rffi.UINT
CC_T = rffi.UCHAR
SPEED_T = rffi.UINT
INT = rffi.INT

TERMIOSP = rffi.CStructPtr('termios', ('c_iflag', TCFLAG_T), ('c_oflag', TCFLAG_T),
                           ('c_cflag', TCFLAG_T), ('c_lflag', TCFLAG_T),
                           ('c_cc', lltype.FixedSizeArray(CC_T, NCCS)))

def c_external(name, args, result):
    return rffi.llexternal(name, args, result, compilation_info=eci)

c_tcsetattr = c_external('tcsetattr', [INT, INT, TERMIOSP], INT)
c_cfgetispeed = c_external('cfgetispeed', [TERMIOSP], SPEED_T)
c_cfgetospeed = c_external('cfgetospeed', [TERMIOSP], SPEED_T)
c_cfsetispeed = c_external('cfsetispeed', [TERMIOSP, SPEED_T], INT)
c_cfsetospeed = c_external('cfsetospeed', [TERMIOSP, SPEED_T], INT)
c_tcsendbreak = c_external('tcsendbreak', [INT, INT], INT)
c_tcdrain = c_external('tcdrain', [INT], INT)
c_tcflush = c_external('tcflush', [INT, INT], INT)
c_tcflow = c_external('tcflow', [INT, INT], INT)

c_tcgetattr = c_external('tcgetattr', [INT, TERMIOSP], INT)

def tcgetattr_llimpl(fd):
    c_struct = lltype.malloc(TERMIOSP.TO, flavor='raw')

    try:
        if c_tcgetattr(fd, c_struct) < 0:
            raise OSError(rposix.get_errno(), 'tcgetattr failed')
        cc = [chr(c_struct.c_c_cc[i]) for i in range(NCCS)]
        ispeed = c_cfgetispeed(c_struct)
        ospeed = c_cfgetospeed(c_struct)
        result = (intmask(c_struct.c_c_iflag), intmask(c_struct.c_c_oflag),
                  intmask(c_struct.c_c_cflag), intmask(c_struct.c_c_lflag),
                  intmask(ispeed), intmask(ospeed), cc)
        return result
    finally:
        lltype.free(c_struct, flavor='raw')

register_external(rtermios.tcgetattr, [int], (int, int, int, int, int, int, [str]),
                   llimpl=tcgetattr_llimpl, export_name='termios.tcgetattr')

def tcsetattr_llimpl(fd, when, attributes):
    c_struct = lltype.malloc(TERMIOSP.TO, flavor='raw')
    c_struct.c_c_iflag, c_struct.c_c_oflag, c_struct.c_c_cflag, \
    c_struct.c_c_lflag, ispeed, ospeed, cc = attributes
    try:
        for i in range(NCCS):
            c_struct.c_c_cc[i] = rffi.r_uchar(ord(cc[i][0]))
        if c_cfsetispeed(c_struct, ispeed) < 0:
            raise OSError(rposix.get_errno(), 'tcsetattr failed')
        if c_cfsetospeed(c_struct, ospeed) < 0:
            raise OSError(rposix.get_errno(), 'tcsetattr failed')
        if c_tcsetattr(fd, when, c_struct) < 0:
            raise OSError(rposix.get_errno(), 'tcsetattr failed')
    finally:
        lltype.free(c_struct, flavor='raw')

r_uint = rffi.r_uint
register_external(rtermios.tcsetattr, [int, int, (r_uint, r_uint, r_uint,
                  r_uint, r_uint, r_uint, [str])], llimpl=tcsetattr_llimpl,
                  export_name='termios.tcsetattr')

# a bit C-c C-v code follows...

def tcsendbreak_llimpl(fd, duration):
    if c_tcsendbreak(fd, duration):
        raise OSError(rposix.get_errno(), 'tcsendbreak failed')
register_external(termios.tcsendbreak, [int, int],
                  llimpl=tcsendbreak_llimpl,
                  export_name='termios.tcsendbreak')

def tcdrain_llimpl(fd):
    if c_tcdrain(fd) < 0:
        raise OSError(rposix.get_errno(), 'tcdrain failed')
register_external(termios.tcdrain, [int], llimpl=tcdrain_llimpl,
                  export_name='termios.tcdrain')

def tcflush_llimpl(fd, queue_selector):
    if c_tcflush(fd, queue_selector) < 0:
        raise OSError(rposix.get_errno(), 'tcflush failed')
register_external(termios.tcflush, [int, int], llimpl=tcflush_llimpl,
                  export_name='termios.tcflush')

def tcflow_llimpl(fd, action):
    if c_tcflow(fd, action) < 0:
        raise OSError(rposix.get_errno(), 'tcflow failed')
register_external(termios.tcflow, [int, int], llimpl=tcflow_llimpl,
                  export_name='termios.tcflow')
