import py
from pypy.rpython import lltype
from pypy.translator.js.node import LLVMNode, ConstantLLVMNode
from pypy.translator.js.log import log
log = log.structnode


class ArrayNode(ConstantLLVMNode):
    """ An arraynode.  Elements can be
    a primitive,
    a struct,
    pointer to struct/array
    """
    __slots__ = "db value arraytype ref".split()
    
    def __init__(self, db, value):
        assert isinstance(lltype.typeOf(value), lltype.Array)
        self.db = db
        self.value = value
        self.arraytype = lltype.typeOf(value).OF
        prefix = 'arrayinstance'
        name = ''   #XXX how to get the name
        self.ref = self.make_ref(prefix, name)

    def __str__(self):
        return "<ArrayNode %r>" % (self.ref,)

    def setup(self):
        for item in self.value.items:
            self.db.prepare_constant(self.arraytype, item)

        p, c = lltype.parentlink(self.value)
        p, c = lltype.parentlink(self.value)
        if p is not None:
            self.db.prepare_constant(lltype.typeOf(p), p)

    def writedecl(self, codewriter):
        if self.arraytype is lltype.Char:
            codewriter.declare(self.ref + ' = new String()') #XXX string should be earlier
        else:
            codewriter.declare(self.ref + ' = new Array()')

    def get_length(self):
        """ returns logical length of array """
        items = self.value.items
        return len(items)

    def get_arrayvalue(self):
        items = self.value.items
        l = len(items)
        r = "[%s]" % ", ".join([self.db.repr_constant(v)[1] for v in items])
        return l, r 

    def get_ref(self):
        return self.ref

    #def get_pbcref(self, toptr):
    #    return self.ref
    #    #ref = self.ref
    #    #p, c = lltype.parentlink(self.value)
    #    #assert p is None, "child arrays are NOT needed by rtyper"
    #    #
    #    #fromptr = "%s*" % self.get_typerepr()
    #    #ref = "cast(%s %s to %s)" % (fromptr, ref, toptr)
    #    #return ref

    def get_childref(self, index):
        return "getelementptr(%s* %s, int 0, uint 1, int %s)" %(
            self.get_typerepr(),
            self.ref,
            index)
    
    def constantvalue(self):
        physicallen, arrayrepr = self.get_arrayvalue()
        return arrayrepr


class StrArrayNode(ArrayNode):
    __slots__ = "".split()

    printables = dict([(ord(i), None) for i in
      ("0123456789abcdefghijklmnopqrstuvwxyz" +
       "ABCDEFGHIJKLMNOPQRSTUVWXYZ" +
       "!#$%&()*+,-./:;<=>?@[]^_`{|}~ '")])

    def get_arrayvalue(self):
        items = self.value.items
        item_length = len(items)
        s = []
        for c in items:
            if ord(c) in StrArrayNode.printables:
                s.append(c)
            else:
                s.append("\\%02x" % ord(c))
                
        r = '"%s"' % "".join(s)
        return item_length, r


class VoidArrayNode(ConstantLLVMNode):
    __slots__ = "db value ref".split()

    def __init__(self, db, value):
        assert isinstance(lltype.typeOf(value), lltype.Array)
        self.db = db
        self.value = value
        prefix = 'arrayinstance_Void'
        name = ''
        self.ref = self.make_ref(prefix, name)

    def constantvalue(self):
        return "{ int } {int %s}" % len(self.value.items)
