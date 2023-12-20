"""
In this file we check that if we use legacy features in universal mode, we
get the expected compile time errors
"""

import sys
import pytest
from .support import HPyTest, make_hpy_abi_fixture, ONLY_LINUX

# this is not strictly correct, we should check whether the actual compiler
# is GCC. But for the CI and most cases, it's enough to assume that if we are
# on linux we are using GCC.
#
# We need this because some of the nice compilation errors (such as the ones
# causes by _HPY_LEGACY) are triggered only by gcc. Would be nice to have them
# also for other compilers
ONLY_GCC = ONLY_LINUX


class TestLegacyForbidden(HPyTest):

    hpy_abi = make_hpy_abi_fixture(['universal'], class_fixture=True)

    LEGACY_ERROR = "Cannot use legacy functions when targeting the HPy Universal ABI"

    def test_expect_make_error(self):
        src = """
            #error "this is a compile time error"
        """
        self.expect_make_error(src, "this is a compile time error")

    def test_Python_h_forbidden(self, capfd):
        src = """
                #include <Python.h>
                @INIT
        """
        self.expect_make_error(src,
            "It is forbidden to #include <Python.h> "
            "when targeting the HPy Universal ABI")

    @ONLY_GCC
    def test_HPy_AsPyObject(self, capfd):
        # NOTE: in this test we don't include Python.h. We want to test that
        # we get a nice compile-time error by just calling HPy_AsPyObject.
        # that's why we use "cpy_PyObject" (which is available because defined
        # by hpy.h)
        src = """
            HPyDef_METH(f, "f", HPyFunc_NOARGS)
            static HPy f_impl(HPyContext *ctx, HPy self)
            {
                cpy_PyObject *pyobj = HPy_AsPyObject(ctx, self);
                (void)pyobj; // silence the warning about unused variable
                return HPy_NULL;
            }
            @EXPORT(f)
            @INIT
        """
        self.expect_make_error(src, self.LEGACY_ERROR)

    @ONLY_GCC
    def test_HPy_FromPyObject(self, capfd):
        # NOTE: in this test we don't include Python.h. We want to test that
        # we get a nice compile-time error by just calling HPy_AsPyObject.
        # that's why we use "cpy_PyObject" (which is available because defined
        # by hpy.h)
        src = """
            HPyDef_METH(f, "f", HPyFunc_NOARGS)
            static HPy f_impl(HPyContext *ctx, HPy self)
            {
                cpy_PyObject *pyobj = NULL;
                return HPy_FromPyObject(ctx, pyobj);
            }
            @EXPORT(f)
            @INIT
        """
        self.expect_make_error(src, self.LEGACY_ERROR)
