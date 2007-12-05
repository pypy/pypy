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

        name = str(value).split()[1]
        self.make_name(name)

    # ______________________________________________________________________
    # main entry points from genllvm 

    def writeglobalconstants(self, codewriter):
        pass

    def constantvalue(self):
        return "%s zeroinitializer" % self.db.repr_type(self.value._TYPE)

