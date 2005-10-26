import py
from pypy.rpython.lltypesystem import lltype
from pypy.translator.js.node import LLVMNode, ConstantLLVMNode
from pypy.translator.js.log import log
log = log.structnode


class ArrayNode(ConstantLLVMNode):
    """ An arraynode.  Elements can be
    a primitive,
    a struct,
    pointer to struct/array
    """
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

    def get_ref(self):
        return self.ref

    def get_childref(self, index):
        return "getelementptr(%s* %s, int 0, uint 1, int %s)" %(
            self.get_typerepr(),
            self.ref,
            index)
    
    def constantvalue(self):
        lines = []
        for i, v in enumerate(self.value.items):
            s = self.db.repr_constant(v)[1]
            line = "%s[%d] = %s" % (self.ref, i, s)
            lines.append(line)
        return lines


class StrArrayNode(ArrayNode):
    printables = dict([(ord(i), None) for i in
      ("0123456789abcdefghijklmnopqrstuvwxyz" +
       "ABCDEFGHIJKLMNOPQRSTUVWXYZ" +
       "!#$%&()*+,-./:;<=>?@[]^_`{|}~ '")])

    def constantvalue(self):
        s = '"'
        if len(self.value.items) > 0 and self.value.items[-1] == '\0':
            items = self.value.items[:-1]   #remove string null terminator
        else:
            items = self.value.items
        for c in items:
            if ord(c) in StrArrayNode.printables:
                s += c
            else:
                s += "\\%02x" % ord(c)
        s += '"'
        return [self.ref + " = " + s]


class VoidArrayNode(ArrayNode):
    def __init__(self, db, value):
        assert isinstance(lltype.typeOf(value), lltype.Array)
        self.db = db
        self.value = value
        prefix = 'arrayinstance_Void'
        name = ''
        self.ref = self.make_ref(prefix, name)
