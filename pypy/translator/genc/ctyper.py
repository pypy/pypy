"""
GenC-specific type specializer
"""

from pypy.translator.typer import Specializer, TypeMatch
from pypy.annotation.model import SomeInteger
from pypy.translator.genc.t_pyobj import CType_PyObject
from pypy.translator.genc.t_int import CType_Int

class GenCSpecializer(Specializer):

    TInt = TypeMatch(SomeInteger(), CType_Int)
    typematches = [TInt]   # in more-specific-first, more-general-last order
    defaulttypecls = CType_PyObject

    specializationtable = [
        ## op      specialized op   arg types   concrete return type
        ('add',     'int_add',     TInt, TInt,   CType_Int),
        ('sub',     'int_sub',     TInt, TInt,   CType_Int),
        ('is_true', 'int_is_true', TInt,         CType_Int),
        ]
