from pypy.translator.llvm.node import ConstantNode
from pypy.rpython.lltypesystem import lltype

class OpaqueNode(ConstantNode):
    def __init__(self, db, value):
        self.db = db
        self.value = value
        self.name = "null"
 
    def writeglobalconstants(self, codewriter):
        pass

class ExtOpaqueNode(ConstantNode):
    prefix = '%opaqueinstance_'
    def __init__(self, db, value):
        self.db = db
        self.value = value
        self._get_ref_cache = None

        name = str(value).split()[1]
        self.make_name(name)

    # ______________________________________________________________________
    # main entry points from genllvm 

    def get_ref(self):
        """ Returns a reference as used for operations in blocks. """        
        if self._get_ref_cache:
            return self._get_ref_cache
        p, c = lltype.parentlink(self.value)
        if p is None:
            ref = self.name
        else:
            ref = self.db.get_childref(p, c)
        self._get_ref_cache = ref
        return ref

    def writeglobalconstants(self, codewriter):
        pass

    def constantvalue(self):
        return "%s zeroinitializer" % self.db.repr_type(self.value._TYPE)

