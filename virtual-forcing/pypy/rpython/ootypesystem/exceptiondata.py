from pypy.rpython.exceptiondata import AbstractExceptionData
from pypy.rpython.ootypesystem import rclass
from pypy.rpython.ootypesystem import ootype
from pypy.annotation import model as annmodel
from pypy.annotation.classdef import FORCE_ATTRIBUTES_INTO_CLASSES

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
        self.fn_pyexcclass2exc = self.make_pyexcclass2exc(rtyper)
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

    def make_pyexcclass2exc(self, rtyper):
        # ll_pyexcclass2exc(python_exception_class) -> exception_instance
        table = {}
        Exception_def = rtyper.annotator.bookkeeper.getuniqueclassdef(Exception)
        for clsdef in rtyper.class_reprs:
            if (clsdef and clsdef is not Exception_def
                and clsdef.issubclass(Exception_def)):
                if not hasattr(clsdef.classdesc, 'pyobj'):
                    continue
                cls = clsdef.classdesc.pyobj
                if cls in self.standardexceptions and cls not in FORCE_ATTRIBUTES_INTO_CLASSES:
                    is_standard = True
                    assert not clsdef.attrs, (
                        "%r should not have grown attributes" % (cls,))
                else:
                    is_standard = (cls.__module__ == 'exceptions'
                                   and not clsdef.attrs)
                if is_standard:
                    example = self.get_standard_ll_exc_instance(rtyper, clsdef)
                    table[cls] = example
        r_inst = rclass.getinstancerepr(rtyper, None)
        r_inst.setup()
        r_class = rclass.getclassrepr(rtyper, None)
        r_class.setup()
        default_excinst = ootype.new(self.lltype_of_exception_value)

        # build the table in order base classes first, subclasses last
        sortedtable = []
        def add_class(cls):
            if cls in table:
                for base in cls.__bases__:
                    add_class(base)
                sortedtable.append((cls, table[cls]))
                del table[cls]
        for cls in table.keys():
            add_class(cls)
        assert table == {}

        initial_value_of_i = len(sortedtable) - 1
        def pyexcclass2exc(python_exception_class):
            python_exception_class = python_exception_class._obj.value
            i = initial_value_of_i
            while i >= 0:
                if issubclass(python_exception_class, sortedtable[i][0]):
                    return sortedtable[i][1]
                i -= 1
            return default_excinst

        # This function will only be used by the llinterpreter which usually
        # expects a low-level callable (_meth, _static_meth), so we just
        # fake it here.
        FakeCallableType = ootype.OOType()
        FakeCallableType.ARGS = ()
        class fake_callable(object):
            def __init__(self, fn):
                self._TYPE = FakeCallableType
                self._callable = fn
        return fake_callable(pyexcclass2exc)

    def cast_exception(self, TYPE, value):
        return ootype.ooupcast(TYPE, value)
