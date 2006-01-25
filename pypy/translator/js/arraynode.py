import py
from pypy.rpython.lltypesystem import lltype
from pypy.translator.js.node import Node
from pypy.translator.js.log import log
log = log.structnode


class ArrayNode(Node):
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
        self.ref = db.namespace.uniquename('arrayinstance') #XXX how to get the name

    def __str__(self):
        return "<ArrayNode %r>" % (self.ref,)

    def setup(self):
        for item in self.value.items:
            self.db.prepare_constant(self.arraytype, item)

        p, c = lltype.parentlink(self.value)
        p, c = lltype.parentlink(self.value)
        if p is not None:
            self.db.prepare_constant(lltype.typeOf(p), p)

    def write_global_array(self, codewriter):
        fields = [self.db.repr_constant(v)[1] for i, v in enumerate(self.value.items)]
        line   = "var %s = [%s];" % (self.ref, ", ".join(fields))
        log.writeglobaldata(line)
        codewriter.append(line)


class StrArrayNode(ArrayNode):
    printables = dict([(ord(i), None) for i in
      ("0123456789abcdefghijklmnopqrstuvwxyz" +
       "ABCDEFGHIJKLMNOPQRSTUVWXYZ" +
       "!#$%&()*+,-./:;<=>?@[]^_`{|}~ '")])

    def write_global_array(self, codewriter):
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
        line = "var " + self.ref + " = " + s
        log.writeglobaldata(line)
        codewriter.append(line)
        #return [line]


class VoidArrayNode(ArrayNode):
    def __init__(self, db, value):
        assert isinstance(lltype.typeOf(value), lltype.Array)
        self.db = db
        self.value = value
        self.arraytype = lltype.typeOf(value).OF
        self.ref = db.namespace.uniquename('arrayinstance_Void')
