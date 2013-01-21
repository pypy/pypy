from rpython.rtyper.exceptiondata import AbstractExceptionData
from rpython.rtyper.ootypesystem import rclass
from rpython.rtyper.ootypesystem import ootype
from rpython.annotator import model as annmodel
from rpython.annotator.classdef import FORCE_ATTRIBUTES_INTO_CLASSES

class ExceptionData(AbstractExceptionData):
    """Public information for the code generators to help with exceptions."""

    def __init__(self, rtyper):
        AbstractExceptionData.__init__(self, rtyper)
        self._compute_exception_instance(rtyper)

    def _compute_exception_instance(self, rtyper):
        excdef = rtyper.annotator.bookkeeper.getuniqueclassdef(Exception)
        excrepr = rclass.getinstancerepr(rtyper, excdef)
        self._EXCEPTION_INST = excrepr.lowleveltype

    def is_exception_instance(self, INSTANCE):
        return ootype.isSubclass(INSTANCE, self._EXCEPTION_INST)

    def make_helpers(self, rtyper):
        self.fn_exception_match = self.make_exception_matcher(rtyper)
        self.fn_type_of_exc_inst = self.make_type_of_exc_inst(rtyper)
        self.fn_raise_OSError    = self.make_raise_OSError(rtyper)        

    def make_exception_matcher(self, rtyper):
        # ll_exception_matcher(real_exception_class, match_exception_class)
        s_classtype = annmodel.SomeOOClass(ootype.ROOT)
        helper_fn = rtyper.annotate_helper_fn(rclass.ll_issubclass, [s_classtype, s_classtype])
        return helper_fn

    
    def make_type_of_exc_inst(self, rtyper):
        # ll_type_of_exc_inst(exception_instance) -> exception_vtable
        s_excinst = annmodel.SomeOOInstance(self.lltype_of_exception_value)
        helper_fn = rtyper.annotate_helper_fn(rclass.ll_inst_type, [s_excinst])
        return helper_fn

    def cast_exception(self, TYPE, value):
        return ootype.ooupcast(TYPE, value)
