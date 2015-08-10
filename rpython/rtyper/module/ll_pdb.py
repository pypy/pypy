"""
Low-level implementation for pdb.set_trace()
"""

import os
import pdb
import signal
from rpython.rtyper.module.support import _WIN32
from rpython.rtyper.extfunc import register_external, ExtFuncEntry
from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.annotator.model import s_None
from rpython.config.translationoption import get_translation_config

import time


if not _WIN32:
    import sys
    if sys.platform.startswith('linux'):
        # Only necessary on Linux
        eci = ExternalCompilationInfo(includes=['string.h', 'assert.h', 'sys/prctl.h'],
                                      post_include_bits=["""
static void pypy__allow_attach(void) {
    prctl(PR_SET_PTRACER, PR_SET_PTRACER_ANY);
    return;
}
        """])
    else:
        # Do nothing, there's no prctl
        eci = ExternalCompilationInfo(post_include_bits=["static void pypy__allow_attach(void) { return; }"])

    allow_attach= rffi.llexternal(
        "pypy__allow_attach", [], lltype.Void,
        compilation_info=eci, _nowrapper=True)

    def pdb_set_trace():
        allow_attach()
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
                os.write(2, "Could not start GDB: %s" % (os.strerror(e.errno)))
                raise SystemExit
        else:
            time.sleep(1) # give the GDB time to attach


    class FunEntry(ExtFuncEntry):
        _about_ = pdb.set_trace
        signature_args = []
        lltypeimpl = staticmethod(pdb_set_trace)
        name = "pdb_set_trace"

        def compute_result_annotation(self, *args_s):
            config = self.bookkeeper.annotator.translator.config.translation
            if config.lldebug or config.lldebug0:
                return s_None
            raise Exception("running pdb.set_trace() without also providing "
                            "--lldebug when translating is not supported")
