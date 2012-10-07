from pypy.annotation import model as annmodel
from pypy.rpython.lltypesystem import rclass
from pypy.rpython.lltypesystem.lltype import (Array, malloc, Ptr, FuncType,
    functionptr, Signed)
from pypy.rpython.exceptiondata import AbstractExceptionData
from pypy.annotation.classdef import FORCE_ATTRIBUTES_INTO_CLASSES


class ExceptionData(AbstractExceptionData):
    """Public information for the code generators to help with exceptions."""

    def make_helpers(self, rtyper):
        # create helper functionptrs
        self.fn_exception_match  = self.make_exception_matcher(rtyper)
        self.fn_type_of_exc_inst = self.make_type_of_exc_inst(rtyper)
        self.fn_raise_OSError    = self.make_raise_OSError(rtyper)
        self.fn_raise_noarg      = self.make_raise_noarg(rtyper)

    def make_exception_matcher(self, rtyper):
        # ll_exception_matcher(real_exception_vtable, match_exception_vtable)
        s_typeptr = annmodel.SomePtr(self.lltype_of_exception_type)
        helper_fn = rtyper.annotate_helper_fn(rclass.ll_issubclass, [s_typeptr, s_typeptr])
        return helper_fn

    def make_type_of_exc_inst(self, rtyper):
        # ll_type_of_exc_inst(exception_instance) -> exception_vtable
        s_excinst = annmodel.SomePtr(self.lltype_of_exception_value)
        helper_fn = rtyper.annotate_helper_fn(rclass.ll_type, [s_excinst])
        return helper_fn

    def cast_exception(self, TYPE, value):
        return rclass.ll_cast_to_object(value)
