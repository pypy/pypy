from pypy.rpython import rclass
from pypy.annotation import model as annmodel


# the exceptions that can be implicitely raised by some operations
standardexceptions = {
    TypeError        : True,
    OverflowError    : True,
    ValueError       : True,
    ZeroDivisionError: True,
    MemoryError      : True,
    IOError          : True,
    OSError          : True,
    StopIteration    : True,
    KeyError         : True,
    IndexError       : True,
    AssertionError   : True,
    RuntimeError     : True,
    UnicodeDecodeError: True,
    UnicodeEncodeError: True,
    NotImplementedError: True,
    }


class AbstractExceptionData:
    """Public information for the code generators to help with exceptions."""
    standardexceptions = standardexceptions

    def __init__(self, rtyper):
        self.make_standard_exceptions(rtyper)
        # (NB. rclass identifies 'Exception' and 'object')
        r_type = rclass.getclassrepr(rtyper, None)
        r_instance = rclass.getinstancerepr(rtyper, None)
        r_type.setup()
        r_instance.setup()
        self.r_exception_type  = r_type
        self.r_exception_value = r_instance
        self.lltype_of_exception_type  = r_type.lowleveltype
        self.lltype_of_exception_value = r_instance.lowleveltype

    def make_standard_exceptions(self, rtyper):
        bk = rtyper.annotator.bookkeeper
        for cls in self.standardexceptions:
            classdef = bk.getuniqueclassdef(cls)

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
        rclass = rtyper.type_system.rclass
        r_inst = rclass.getinstancerepr(rtyper, clsdef)
        example = r_inst.get_reusable_prebuilt_instance()
        example = self.cast_exception(self.lltype_of_exception_value, example)
        return example
 

