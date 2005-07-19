from pypy.annotation.pairtype import pairtype
from pypy.annotation import model as annmodel
from pypy.rpython.lltype import Signed, Unsigned, Bool, Float, pyobjectptr
from pypy.rpython.rmodel import Repr, TyperError, IntegerRepr, BoolRepr
from pypy.rpython.robject import PyObjRepr, pyobj_repr


debug = False

class __extend__(annmodel.SomeBool):
    def rtyper_makerepr(self, rtyper):
        return bool_repr
    def rtyper_makekey(self):
        return self.__class__,

bool_repr = BoolRepr()


class __extend__(BoolRepr):

    def convert_const(self, value):
        if not isinstance(value, bool):
            raise TyperError("not a bool: %r" % (value,))
        return value

    def get_ll_eq_function(self):
        return None 

    def rtype_is_true(_, hop):
        vlist = hop.inputargs(Bool)
        return vlist[0]

    def rtype_int(_, hop):
        vlist = hop.inputargs(Signed)
        return vlist[0]

    def rtype_float(_, hop):
        vlist = hop.inputargs(Float)
        return vlist[0]

#
# _________________________ Conversions _________________________

class __extend__(pairtype(BoolRepr, IntegerRepr)):
    def convert_from_to((r_from, r_to), v, llops):
        if r_from.lowleveltype == Bool and r_to.lowleveltype == Unsigned:
            if debug: print 'explicit cast_bool_to_uint'
            return llops.genop('cast_bool_to_uint', [v], resulttype=Unsigned)
        if r_from.lowleveltype == Bool and r_to.lowleveltype == Signed:
            if debug: print 'explicit cast_bool_to_int'
            return llops.genop('cast_bool_to_int', [v], resulttype=Signed)
        return NotImplemented

class __extend__(pairtype(PyObjRepr, BoolRepr)):
    def convert_from_to((r_from, r_to), v, llops):
        if r_to.lowleveltype == Bool:
            # xxx put in table
            return llops.gencapicall('PyObject_IsTrue', [v], resulttype=Bool,
                                     _callable=lambda pyo: bool(pyo._obj.value))
        return NotImplemented

class __extend__(pairtype(BoolRepr, PyObjRepr)):
    def convert_from_to((r_from, r_to), v, llops):
        if r_from.lowleveltype == Bool:
            return llops.gencapicall('PyBool_FromLong', [v],
                                     resulttype = pyobj_repr)
        return NotImplemented
