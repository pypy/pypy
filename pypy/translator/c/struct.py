from pypy.rpython.lltypes import *
from pypy.translator.c.repr import Repr


class ReprStruct(Repr):

    def follow_type_references(db, lowleveltype):
        T = lowleveltype.TO
        assert isinstance(T, Struct)
        for name in T._names:
            db.getlltype(T._flds[name])
    follow_type_references = staticmethod(follow_type_references)
