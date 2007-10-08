from pypy.rpython.rslice import AbstractSliceRepr
from pypy.rpython.lltypesystem.lltype import \
     GcStruct, Signed, Ptr, Void, malloc, PyObject, nullptr
from pypy.tool.pairtype import pairtype
from pypy.rpython.robject import PyObjRepr, pyobj_repr
from pypy.rpython.rmodel import inputconst, PyObjPtr, IntegerRepr

# ____________________________________________________________
#
#  Concrete implementation of RPython slice objects:
#
#  - if stop is None, use only a Signed
#  - if stop is not None:
#
#      struct slice {
#          Signed start;
#          Signed stop;
#          //     step is always 1
#      }

SLICE = GcStruct("slice", ("start", Signed), ("stop", Signed),
                 hints = {'immutable': True})

class SliceRepr(AbstractSliceRepr):
    pass

startstop_slice_repr = SliceRepr()
startstop_slice_repr.lowleveltype = Ptr(SLICE)
startonly_slice_repr = SliceRepr()
startonly_slice_repr.lowleveltype = Signed
minusone_slice_repr = SliceRepr()
minusone_slice_repr.lowleveltype = Void    # only for [:-1]

# ____________________________________________________________

def ll_newslice(start, stop):
    s = malloc(SLICE)
    s.start = start
    s.stop = stop
    return s

# ____________________________________________________________
#
# limited support for casting into PyObject

# stuff like this should go into one file maybe

class __extend__(pairtype(SliceRepr, PyObjRepr)):
    def convert_from_to((r_from, r_to), v, llops):
        null = inputconst(Ptr(PyObject), nullptr(PyObject))
        def pyint(v):
            return llops.gencapicall('PyInt_FromLong', [v], resulttype=r_to)
        v_step = v_start = v_stop = null
        if r_from.lowleveltype is Signed:
            v_start = pyint(v)
        elif r_from.lowleveltype is Void:
            v_stop = inputconst(r_to, -1)
        else:
            v_start = pyint(llops.genop('getfield', [v, inputconst(Void, 'start')],
                            resulttype=Signed))
            v_stop = pyint(llops.genop('getfield', [v, inputconst(Void, 'stop')],
                           resulttype=Signed))
        return llops.gencapicall('PySlice_New',
                                 [v_start, v_stop, v_step],
                                 resulttype = pyobj_repr)
