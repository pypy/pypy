from pypy.annotation.pairtype import pairtype
from pypy.annotation import model as annmodel
from pypy.rpython import rmodel, lltype

# ____________________________________________________________
#
#  PyPy uses dictionaries that are known to be empty at run-time!
#  look for 'lazyloaders'.

class EmptyDictRepr(rmodel.Repr):
    lowleveltype = lltype.Void

    def rtype_len(self, hop):
        return hop.inputconst(lltype.Signed, 0)
