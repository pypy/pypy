from pypy.rpython.exceptiondata import AbstractExceptionData
from pypy.rpython.ootypesystem import rclass
from pypy.rpython.annlowlevel import annotate_lowlevel_helper
from pypy.annotation import model as annmodel

class ExceptionData(AbstractExceptionData):
    """Public information for the code generators to help with exceptions."""

    def make_helpers(self, rtyper):
        self.fn_exception_match = self.make_exception_matcher(rtyper)

    def make_exception_matcher(self, rtyper):
        # ll_exception_matcher(real_exception_meta, match_exception_meta)
        s_classtype = annmodel.SomeOOInstance(self.lltype_of_exception_type)
        helper_graph = annotate_lowlevel_helper(
            rtyper.annotator, rclass.ll_issubclass, [s_classtype, s_classtype])
        return rtyper.getcallable(helper_graph)
