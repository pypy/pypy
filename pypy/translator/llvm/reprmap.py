import autopath

from pypy.rpython import lltype

from pypy.translator.llvm import representation, funcrepr, typerepr, seqrepr
from pypy.translator.llvm import classrepr, pbcrepr, pointerrepr

PRIMITIVE_REPRS = {
    lltype.Signed: representation.SignedRepr,
    lltype.Unsigned: representation.UnsignedRepr,
    lltype.Char: representation.CharRepr,
    lltype.Bool: representation.BoolRepr,
    lltype.Float: representation.FloatRepr,
}
    
PRIMITIVE_TYPES = {
    lltype.Signed: typerepr.SignedTypeRepr,
    lltype.Unsigned: typerepr.UnsignedTypeRepr,
    lltype.Char: typerepr.CharTypeRepr,
    lltype.Bool: typerepr.BoolTypeRepr,
    lltype.Float: typerepr.FloatTypeRepr,
}
    
#def ptr_types(ptr):
#    if isinstance(ptr._obj, lltype._func):
#        return pointerrepr.FuncPointerRepr(ptr)
        
