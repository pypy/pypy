from pypy.translator.llvm.node import LLVMNode, ConstantLLVMNode
from pypy.rpython.lltypesystem import lltype

class OpaqueTypeNode(LLVMNode):

    def __init__(self, db, opaquetype): 
        assert isinstance(opaquetype, lltype.OpaqueType)
        self.db = db
        self.opaquetype = opaquetype
        self.ref = "%%RPyOpaque_%s" % (opaquetype.tag)
        
    def __str__(self):
        return "<OpaqueNode %r>" %(self.ref,)

    # ______________________________________________________________________
    # main entry points from genllvm 

    def writedatatypedecl(self, codewriter):
        codewriter.typedef(self.ref, "opaque*")

class ExtOpaqueTypeNode(OpaqueTypeNode):
    def writedatatypedecl(self, codewriter):
        pass

class OpaqueNode(ConstantLLVMNode):
    def __init__(self, db, value):
        self.db = db
        self.value = value
        self.ref = "null"
    # ______________________________________________________________________
    # main entry points from genllvm 

    def writeglobalconstants(self, codewriter):
        # XXX Dummy - not sure what what we want
        pass

class ExtOpaqueNode(ConstantLLVMNode):
    def __init__(self, db, value):
        self.db = db
        self.value = value
        prefix = '%opaqueinstance_'
        name = str(value).split()[1]
        self.ref = self.make_ref(prefix, name)
        self._get_ref_cache = None

    # ______________________________________________________________________
    # main entry points from genllvm 

    def get_ref(self):
        """ Returns a reference as used for operations in blocks. """        
        if self._get_ref_cache:
            return self._get_ref_cache
        p, c = lltype.parentlink(self.value)
        if p is None:
            ref = self.ref
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
