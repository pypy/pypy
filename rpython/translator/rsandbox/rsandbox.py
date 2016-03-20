import py
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.translator.c.support import cdecl


def register_rsandbox_func(database, ll_func, fnname):
    """Register a trampoline function for the given ll_func
    and return its name.

    The trampoline is meant to be used in place of real calls to the external
    function named 'fnname'.  It calls a function pointer that is
    under control of the main C program using the sandboxed library.
    """
    try:
        extfuncs = database._sandboxlib_fnnames
    except AttributeError:
        extfuncs = database._sandboxlib_fnnames = {}

    if fnname not in extfuncs:
        extfuncs[fnname] = lltype.typeOf(ll_func)
    else:
        FUNC = extfuncs[fnname]
        assert lltype.typeOf(ll_func) == FUNC, (
            "seen two sandboxed functions called %r with different "
            "signatures:\n  %r\n  %r" % (fnname, FUNC, lltype.typeOf(ll_func)))
    return 'rsandbox_' + fnname


def add_sandbox_files(database, eci, targetdir):
    c_header = ['''
#ifndef _RSANDBOX_H_
#define _RSANDBOX_H_

#ifndef RPY_SANDBOX_EXPORTED
/* common definitions when including this file from an external C project */
#define RPY_SANDBOX_EXPORTED  extern
typedef long Signed;
typedef unsigned long Unsigned;
#endif

''']
    c_source = ['''
#include <stdlib.h>
#include <sys/utsname.h>
#include "rsandbox.h"

''']

    fnnames = database._sandboxlib_fnnames
    for fnname in sorted(fnnames):
        FUNC = fnnames[fnname]
        rsandboxname = 'rsandbox_' + fnname

        vardecl = cdecl(database.gettype(lltype.Ptr(FUNC)), rsandboxname)
        c_header.append('RPY_SANDBOX_EXPORTED %s;\n' % (vardecl,))

        emptyfuncname = 'rsand_def_' + fnname
        argnames = ['a%d' % i for i in range(len(FUNC.ARGS))]
        c_source.append("""
static %s {
    abort();
};
%s = %s;
""" % (cdecl(database.gettype(FUNC, argnames=argnames), emptyfuncname),
       vardecl, emptyfuncname))

    c_header.append('''
#endif  /* _RSANDBOX_H_ */
''')
    targetdir.join('rsandbox.c').write(''.join(c_source))
    targetdir.join('rsandbox.h').write(''.join(c_header))
    # ^^^ a #include "rsandbox.h" is explicitly added to forwarddecl.h
    #     from genc.py

    return eci.merge(ExternalCompilationInfo(
        separate_module_files=[targetdir.join('rsandbox.c')]))
