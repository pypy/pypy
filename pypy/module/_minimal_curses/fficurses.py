""" The ffi for rpython, need to be imported for side effects
"""

from rpython.rtyper.lltypesystem import rffi
from rpython.rtyper.lltypesystem import lltype
from rpython.rtyper.tool import rffi_platform
from rpython.rtyper.extfunc import register_external
from pypy.module._minimal_curses import interp_curses
from rpython.translator.tool.cbuild import ExternalCompilationInfo

# We cannot trust ncurses5-config, it's broken in various ways in
# various versions.  For example it might not list -ltinfo even though
# it's needed, or --cflags might be completely empty.  On Ubuntu 10.04
# it gives -I/usr/include/ncurses, which doesn't exist at all.  Crap.

def try_cflags():
    yield ExternalCompilationInfo(includes=['curses.h', 'term.h'])
    yield ExternalCompilationInfo(includes=['curses.h', 'term.h'],
                                  include_dirs=['/usr/include/ncurses'])
    yield ExternalCompilationInfo(includes=['ncurses/curses.h',
                                            'ncurses/term.h'])

def try_ldflags():
    yield ExternalCompilationInfo(libraries=['curses'])
    yield ExternalCompilationInfo(libraries=['curses', 'tinfo'])
    yield ExternalCompilationInfo(libraries=['ncurses'])
    yield ExternalCompilationInfo(libraries=['ncurses'],
                                  library_dirs=['/usr/lib64'])

def try_tools():
    try:
        yield ExternalCompilationInfo.from_pkg_config("ncurses")
    except Exception:
        pass
    try:
        yield ExternalCompilationInfo.from_config_tool("ncurses5-config")
    except Exception:
        pass

def try_eci():
    for eci in try_tools():
        yield eci.merge(ExternalCompilationInfo(includes=['curses.h',
                                                          'term.h']))
    for eci1 in try_cflags():
        for eci2 in try_ldflags():
            yield eci1.merge(eci2)

def guess_eci():
    for eci in try_eci():
        class CConfig:
            _compilation_info_ = eci
            HAS = rffi_platform.Has("setupterm")
        if rffi_platform.configure(CConfig)['HAS']:
            return eci
    raise ImportError("failed to guess where ncurses is installed. "
                      "You might need to install libncurses5-dev or similar.")

eci = guess_eci()


INT = rffi.INT
INTP = lltype.Ptr(lltype.Array(INT, hints={'nolength':True}))
c_setupterm = rffi.llexternal('setupterm', [rffi.CCHARP, INT, INTP], INT,
                              compilation_info=eci)
c_tigetstr = rffi.llexternal('tigetstr', [rffi.CCHARP], rffi.CCHARP,
                             compilation_info=eci)
c_tparm = rffi.llexternal('tparm', [rffi.CCHARP, INT, INT, INT, INT, INT,
                                    INT, INT, INT, INT], rffi.CCHARP,
                          compilation_info=eci)

ERR = rffi.CConstant('ERR', lltype.Signed)
OK = rffi.CConstant('OK', lltype.Signed)

def curses_setupterm(term, fd):
    intp = lltype.malloc(INTP.TO, 1, flavor='raw')
    err = rffi.cast(lltype.Signed, c_setupterm(term, fd, intp))
    try:
        if err == ERR:
            errret = rffi.cast(lltype.Signed, intp[0])
            if errret == 0:
                msg = "setupterm: could not find terminal"
            elif errret == -1:
                msg = "setupterm: could not find terminfo database"
            else:
                msg = "setupterm: unknown error"
            raise interp_curses.curses_error(msg)
        interp_curses.module_info.setupterm_called = True
    finally:
        lltype.free(intp, flavor='raw')

def curses_setupterm_null_llimpl(fd):
    curses_setupterm(lltype.nullptr(rffi.CCHARP.TO), fd)

def curses_setupterm_llimpl(term, fd):
    ll_s = rffi.str2charp(term)
    try:
        curses_setupterm(ll_s, fd)
    finally:
        rffi.free_charp(ll_s)

register_external(interp_curses._curses_setupterm_null,
                  [int], llimpl=curses_setupterm_null_llimpl,
                  export_name='_curses.setupterm_null')
register_external(interp_curses._curses_setupterm,
                  [str, int], llimpl=curses_setupterm_llimpl,
                  export_name='_curses.setupterm')

def check_setup_invoked():
    if not interp_curses.module_info.setupterm_called:
        raise interp_curses.curses_error("must call (at least) setupterm() first")

def tigetstr_llimpl(cap):
    check_setup_invoked()
    ll_cap = rffi.str2charp(cap)
    try:
        ll_res = c_tigetstr(ll_cap)
        num = lltype.cast_ptr_to_int(ll_res)
        if num == 0 or num == -1:
            raise interp_curses.TermError()
        res = rffi.charp2str(ll_res)
        return res
    finally:
        rffi.free_charp(ll_cap)

register_external(interp_curses._curses_tigetstr, [str], str,
                  export_name='_curses.tigetstr', llimpl=tigetstr_llimpl)

def tparm_llimpl(s, args):
    check_setup_invoked()
    l = [0, 0, 0, 0, 0, 0, 0, 0, 0]
    for i in range(min(len(args), 9)):
        l[i] = args[i]
    ll_s = rffi.str2charp(s)
    # XXX nasty trick stolen from CPython
    ll_res = c_tparm(ll_s, l[0], l[1], l[2], l[3], l[4], l[5], l[6],
                     l[7], l[8])
    rffi.free_charp(ll_s)
    res = rffi.charp2str(ll_res)
    return res

register_external(interp_curses._curses_tparm, [str, [int]], str,
                  export_name='_curses.tparm', llimpl=tparm_llimpl)

