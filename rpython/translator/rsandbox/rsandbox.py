import py, re
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
/* Common definitions when including this file from an external C project */

#include <stdlib.h>
#include <sys/utsname.h>

#define RPY_SANDBOX_EXPORTED  extern

typedef long Signed;
typedef unsigned long Unsigned;

#endif

/* The list of 'rsandbox_*' function pointers is automatically
   generated.  Most of these function pointers are initialized to
   point to a function that aborts the sandboxed execution.  The
   sandboxed program cannot, by default, use any of them.  A few
   exceptions are provided, where the default implementation returns a
   safe default; for example rsandbox_getenv().
*/
''']
    c_source = ['''
#include "common_header.h"
#include "rsandbox.h"
#include <stdlib.h>

''']

    default_h = py.path.local(__file__).join('..', 'default.h').read()
    c_source.append(default_h)
    present = set(re.findall(r'\brsand_def_([a-zA-Z0-9_]+)[(]', default_h))

    fnnames = database._sandboxlib_fnnames
    for fnname in sorted(fnnames):
        FUNC = fnnames[fnname]
        rsandboxname = 'rsandbox_' + fnname

        vardecl = cdecl(database.gettype(lltype.Ptr(FUNC)), rsandboxname)
        c_header.append('RPY_SANDBOX_EXPORTED %s;\n' % (vardecl,))

        emptyfuncname = 'rsand_def_' + fnname
        argnames = ['a%d' % i for i in range(len(FUNC.ARGS))]
        if fnname not in present:
            c_source.append("""
static %s {
    rsand_fatal("%s");
};
""" % (cdecl(database.gettype(FUNC, argnames=argnames), emptyfuncname), fnname))
        else:
            c_source.append('\n')
        c_source.append("%s = %s;\n" % (vardecl, emptyfuncname))

    c_header.append('''
#endif  /* _RSANDBOX_H_ */
''')
    targetdir.join('rsandbox.c').write(''.join(c_source))
    targetdir.join('rsandbox.h').write(''.join(c_header))
    # ^^^ a #include "rsandbox.h" is explicitly added to forwarddecl.h
    #     from genc.py

    return eci.merge(ExternalCompilationInfo(
        separate_module_files=[targetdir.join('rsandbox.c')]))
