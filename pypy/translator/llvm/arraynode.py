from pypy.rpython.lltypesystem import lltype
from pypy.translator.llvm.node import ConstantNode

class DebugStrNode(ConstantNode):
    prefix = "@dg_isnt"
    def __init__(self, value):
        self.value = value
        self.make_name()

    def get_length(self):
        return len(self.value) + 1

    def get_typerepr(self):
        return '[%s x i8]' % self.get_length()
    
    def constantvalue(self):
        return '%s c"%s\\00"' % (self.get_typerepr(), self.value)
    
    def writeglobalconstants(self, codewriter):
        codewriter.globalinstance(self.ref, self.constantvalue())
        codewriter.newline()
        codewriter.newline()
        
class ArrayNode(ConstantNode):
    __slots__ = "db value arraytype".split()
    prefix = '@a_inst'
    
    def __init__(self, db, value):
        assert isinstance(lltype.typeOf(value), lltype.Array)
        self.db = db
        self.value = value
        self.arraytype = lltype.typeOf(value).OF

        name = '' #str(value).split()[1]
        self.make_name(name)

    def setup(self):
        for value in self.db.gcpolicy.gcheader_initdata(self.value):
            self.db.prepare_constant(lltype.typeOf(value), value)
        for item in self.value.items:
            self.db.prepare_constant(self.arraytype, item)

        p, c = lltype.parentlink(self.value)
        if p is not None:
            self.db.prepare_constant(lltype.typeOf(p), p)

    def get_length(self):
        """ returns logical length of array """
        items = self.value.items
        return len(items)

    def get_arrayvalue(self):
        items = self.value.items
        l = len(items)
        reprs = [self.db.repr_constant(v)[1] for v in items]
        line = ",  ".join(reprs)
        if len(line) < 70:
            r = "[%s]" % line
        else:
            r = "[%s]" % ",\n\t ".join(reprs)
        return l, r 

    def get_typerepr(self):
        arraylen = self.get_arrayvalue()[0]
        typedefnode = self.db.obj2node[lltype.typeOf(self.value)]
        return typedefnode.get_typerepr(arraylen)
    
    def constantvalue(self):
        physicallen, arrayrepr = self.get_arrayvalue()
        typeval = self.db.repr_type(self.arraytype)

        # first length is logical, second is physical
        result = ""
        for value in self.db.gcpolicy.gcheader_initdata(self.value):
            result += "%s, " % (self.db.repr_constant(value)[1],)
        result += "%s %s, [%s x %s]\n\t%s" % (self.db.get_machine_word(),
                                            self.get_length(),
                                            physicallen,
                                            typeval,
                                            arrayrepr)

        return "%s {%s}" % (self.get_typerepr(), result)

class ArrayNoLengthNode(ArrayNode):
    def get_typerepr(self):
        arraylen = self.get_arrayvalue()[0]
        typeval = self.db.repr_type(self.arraytype)
        return "[%s x %s]" % (arraylen, typeval)

    def constantvalue(self):
        physicallen, arrayrepr = self.get_arrayvalue()
        s = "%s %s" % (self.get_typerepr(), arrayrepr)
        return s

class StrArrayNode(ArrayNode):
    __slots__ = "".split()

    printables = dict([(ord(i), None) for i in
      ("0123456789abcdefghijklmnopqrstuvwxyz" +
       "ABCDEFGHIJKLMNOPQRSTUVWXYZ" +
       "!#$%&()*+,-./:;<=>?@[]^_`{|}~ '")])

    def get_arrayvalue(self):
        items = self.value.items
        item_length = len(items)
        if item_length == 0 or items[-1] != chr(0):
            items = items + [chr(0)]
            item_length += 1
        s = []
        for c in items:
            if ord(c) in StrArrayNode.printables:
                s.append(c)
            else:
                s.append("\\%02x" % ord(c))
                
        r = 'c"%s"' % "".join(s)
        return item_length, r

class StrArrayNoLengthNode(StrArrayNode, ArrayNoLengthNode):
    pass

class VoidArrayNode(ConstantNode):
    __slots__ = "db value".split()
    prefix = '@voidarrayinstance'

    def __init__(self, db, value):
        assert isinstance(lltype.typeOf(value), lltype.Array)
        self.db = db
        self.value = value
        name = '' #str(value).split()[1]
        self.make_name(name)

    def setup(self):
        for value in self.db.gcpolicy.gcheader_initdata(self.value):
            self.db.prepare_constant(lltype.typeOf(value), value)

    def get_typerepr(self):
        typedefnode = self.db.obj2node[lltype.typeOf(self.value)]
        return typedefnode.get_typerepr()

    def get_length(self):
        """ returns logical length of array """
        items = self.value.items
        return len(items)

    def constantvalue(self):
        result = ""
        for value in self.db.gcpolicy.gcheader_initdata(self.value):
            result += "%s %s, " % self.db.repr_constant(value)
        result += "%s %s" % (self.db.get_machine_word(),
                             self.get_length())
        return "%s { %s }" % (self.get_typerepr(), result)
