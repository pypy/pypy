from rpython.jit.backend.llsupport.test.zrpy_gc_test import CompileFrameworkTests
import pytest


# XXX OpenBSD
# Generated binary crashes:
# mem.c: 13 mallocs left (use PYPY_ALLOC=1 to see the list)
# RPython traceback:
#   File "rpython_jit_backend_llsupport_test.c", line 232, in entrypoint
#   File "rpython_jit_backend_llsupport_test.c", line 520, in allfuncs
#   File "rpython_jit_backend_llsupport_test.c", line 599, in main_allfuncs
#   File "rpython_rtyper_lltypesystem.c", line 3658, in ll_dict_getitem_with_hash__dicttablePtr_rpy_stri
# Fatal RPython error: KeyError
class TestShadowStack(CompileFrameworkTests):
    gcrootfinder = "shadowstack"
    gc = "incminimark"
