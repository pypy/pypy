from pypy.annotation import model as annmodel
from pypy.rpython.lltypesystem import rclass
from pypy.rpython.lltypesystem.lltype import \
     Array, malloc, Ptr, PyObject, pyobjectptr, \
     FuncType, functionptr, Signed
from pypy.rpython.exceptiondata import AbstractExceptionData
from pypy.annotation.classdef import FORCE_ATTRIBUTES_INTO_CLASSES

class ExceptionData(AbstractExceptionData):
    """Public information for the code generators to help with exceptions."""

    def make_helpers(self, rtyper):
        # create helper functionptrs
        self.fn_exception_match  = self.make_exception_matcher(rtyper)
        self.fn_type_of_exc_inst = self.make_type_of_exc_inst(rtyper)
        self.fn_pyexcclass2exc   = self.make_pyexcclass2exc(rtyper)
        self.fn_raise_OSError    = self.make_raise_OSError(rtyper)

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
                #else:
                #    assert cls.__module__ != 'exceptions', (
                #        "built-in exceptions should not grow attributes")
        r_inst = rclass.getinstancerepr(rtyper, None)
        r_inst.setup()
        default_excinst = malloc(self.lltype_of_exception_value.TO,
                                 immortal=True)
        default_excinst.typeptr = r_inst.rclass.getvtable()

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
        #print sortedtable

        A = Array(('pycls', Ptr(PyObject)),
                  ('excinst', self.lltype_of_exception_value))
        pycls2excinst = malloc(A, len(sortedtable), immortal=True)
        for i in range(len(sortedtable)):
            cls, example = sortedtable[i]
            pycls2excinst[i].pycls   = pyobjectptr(cls)
            pycls2excinst[i].excinst = example

        FUNCTYPE = FuncType([Ptr(PyObject), Ptr(PyObject)], Signed)
        PyErr_GivenExceptionMatches = functionptr(
            FUNCTYPE, "PyErr_GivenExceptionMatches", external="C",
            _callable=lambda pyobj1, pyobj2:
                          int(issubclass(pyobj1._obj.value, pyobj2._obj.value)))

        initial_value_of_i = len(pycls2excinst)-1

        def ll_pyexcclass2exc(python_exception_class):
            """Return an RPython instance of the best approximation of the
            Python exception identified by its Python class.
            """
            i = initial_value_of_i
            while i >= 0:
                if PyErr_GivenExceptionMatches(python_exception_class,
                                               pycls2excinst[i].pycls):
                    return pycls2excinst[i].excinst
                i -= 1
            return default_excinst

        s_pyobj = annmodel.SomePtr(Ptr(PyObject))
        helper_fn = rtyper.annotate_helper_fn(ll_pyexcclass2exc, [s_pyobj])
        return helper_fn

    def cast_exception(self, TYPE, value):
        return rclass.ll_cast_to_object(value)
