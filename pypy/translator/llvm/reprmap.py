import autopath

from pypy.rpython import lltype

from pypy.translator.llvm import representation, funcrepr, typerepr, seqrepr
from pypy.translator.llvm import classrepr, pbcrepr

PRIMITIVE_REPRS = {
    lltype.Signed: representation.SignedRepr,
    lltype.Unsigned: representation.UnsignedRepr,
    lltype.Char: representation.CharRepr,
    lltype.Bool: representation.BoolRepr
}
    
PRIMITIVE_TYPES = {
    lltype.Signed: typerepr.SignedTypeRepr,
    lltype.Unsigned: typerepr.UnsignedTypeRepr,
    lltype.Char: typerepr.CharTypeRepr,
    lltype.Bool: typerepr.BoolTypeRepr,
}
    
