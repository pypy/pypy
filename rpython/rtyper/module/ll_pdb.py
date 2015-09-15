"""
Complain if you leave in pdb.set_trace() in the code
"""

import pdb
from rpython.rtyper.extfunc import ExtFuncEntry


class FunEntry(ExtFuncEntry):
    _about_ = pdb.set_trace
    def compute_result_annotation(self, *args_s):
        raise Exception("you left pdb.set_trace() in your interpreter!"
                        "If you want to attach a gdb instead, call rlib.debug.attach_gdb()")
