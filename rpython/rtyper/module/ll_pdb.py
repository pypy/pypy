"""
Low-level implementation for pdb.set_trace()
"""

import os
import pdb
from rpython.rtyper.module.support import _WIN32
from rpython.rtyper.extfunc import register_external


if not _WIN32:
    def pdb_set_trace():
        pid = os.getpid()
        gdbpid = os.fork()
        if gdbpid == 0:
            shell = os.environ.get("SHELL") or "/bin/sh"
            sepidx = shell.rfind(os.sep) + 1
            if sepidx > 0:
                argv0 = shell[sepidx:]
            else:
                argv0 = shell
            try:
                os.execv(shell, [argv0, "-c", "gdb -p %d" % pid])
            except OSError as e:
                raise SystemExit('Could not start GDB: %s.' % e)
    register_external(pdb.set_trace, [], llimpl=pdb_set_trace)
