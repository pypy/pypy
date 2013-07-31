from rpython.annotator import model as annmodel
from rpython.rlib import rstackovf
from rpython.rtyper import rclass
from rpython.rtyper.lltypesystem.rclass import (ll_issubclass, ll_type,
        ll_cast_to_object)

# the exceptions that can be implicitely raised by some operations
standardexceptions = set([TypeError, OverflowError, ValueError,
    ZeroDivisionError, MemoryError, IOError, OSError, StopIteration, KeyError,
    IndexError, AssertionError, RuntimeError, UnicodeDecodeError,
    UnicodeEncodeError, NotImplementedError, rstackovf._StackOverflow])

class UnknownException(Exception):
    pass


class ExceptionData(object):
    """Public information for the code generators to help with exceptions."""

    standardexceptions = standardexceptions

    def __init__(self, rtyper):
        self.make_standard_exceptions(rtyper)
        # (NB. rclass identifies 'Exception' and 'object')
        r_type = rclass.getclassrepr(rtyper, None)
        r_instance = rclass.getinstancerepr(rtyper, None)
        r_type.setup()
        r_instance.setup()
        self.r_exception_type = r_type
        self.r_exception_value = r_instance
        self.lltype_of_exception_type = r_type.lowleveltype
        self.lltype_of_exception_value = r_instance.lowleveltype
        self.rtyper = rtyper

    def make_standard_exceptions(self, rtyper):
        bk = rtyper.annotator.bookkeeper
        for cls in self.standardexceptions:
            bk.getuniqueclassdef(cls)

    def finish(self, rtyper):
        bk = rtyper.annotator.bookkeeper
        for cls in self.standardexceptions:
            classdef = bk.getuniqueclassdef(cls)
            rclass.getclassrepr(rtyper, classdef).setup()

    def make_raise_OSError(self, rtyper):
        # ll_raise_OSError(errno)
        def ll_raise_OSError(errno):
            raise OSError(errno, None)
        helper_fn = rtyper.annotate_helper_fn(ll_raise_OSError, [annmodel.SomeInteger()])
        return helper_fn

    def get_standard_ll_exc_instance(self, rtyper, clsdef):
        from rpython.rtyper.lltypesystem.rclass import getinstancerepr
        r_inst = getinstancerepr(rtyper, clsdef)
        example = r_inst.get_reusable_prebuilt_instance()
        example = ll_cast_to_object(example)
        return example

    def get_standard_ll_exc_instance_by_class(self, exceptionclass):
        if exceptionclass not in self.standardexceptions:
            raise UnknownException(exceptionclass)
        clsdef = self.rtyper.annotator.bookkeeper.getuniqueclassdef(
            exceptionclass)
        return self.get_standard_ll_exc_instance(self.rtyper, clsdef)

    def make_helpers(self, rtyper):
        # create helper functionptrs
        self.fn_exception_match  = self.make_exception_matcher(rtyper)
        self.fn_type_of_exc_inst = self.make_type_of_exc_inst(rtyper)
        self.fn_raise_OSError    = self.make_raise_OSError(rtyper)

    def make_exception_matcher(self, rtyper):
        # ll_exception_matcher(real_exception_vtable, match_exception_vtable)
        s_typeptr = annmodel.SomePtr(self.lltype_of_exception_type)
        helper_fn = rtyper.annotate_helper_fn(ll_issubclass, [s_typeptr, s_typeptr])
        return helper_fn

    def make_type_of_exc_inst(self, rtyper):
        # ll_type_of_exc_inst(exception_instance) -> exception_vtable
        s_excinst = annmodel.SomePtr(self.lltype_of_exception_value)
        helper_fn = rtyper.annotate_helper_fn(ll_type, [s_excinst])
        return helper_fn
