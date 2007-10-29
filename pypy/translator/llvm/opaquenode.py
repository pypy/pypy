from pypy.translator.llvm.node import ConstantNode
from pypy.rpython.lltypesystem import lltype

class OpaqueNode(ConstantNode):
    def __init__(self, db, value):
        self.db = db
        self.value = value
        self.name = "null"
 
    def writeglobalconstants(self, codewriter):
        # XXX Dummy - not sure what what we want
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
        # XXX Dummy - not sure what what we want
        pass

    def constantvalue(self):
        return "%s zeroinitializer" % self.db.repr_type(self.value._TYPE)

    def writesetupcode(self, codewriter):
        T = self.value._TYPE
        # XXX similar non generic hacks to genc for now
        if T.tag == 'ThreadLock':
            argrefs = [self.get_ref()]
            argtypes = [self.db.repr_type(T) + "*"]
            lock = self.value.externalobj
            argtypes.append("int")
            if lock.locked():
                argrefs.append('1')
            else:
                argrefs.append('0')

            # XXX Check result
            codewriter.call(self.db.repr_tmpvar(),
                            "sbyte*",
                            "%RPyOpaque_LLVM_SETUP_ThreadLock",
                            argtypes, argrefs)
            # XXX Check result
