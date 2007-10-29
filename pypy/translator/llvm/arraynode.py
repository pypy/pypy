from pypy.rpython.lltypesystem import lltype
from pypy.translator.llvm.node import ConstantNode

class ArrayNode(ConstantNode):
    __slots__ = "db value arraytype".split()
    prefix = '%arrayinstance'
    
    def __init__(self, db, value):
        assert isinstance(lltype.typeOf(value), lltype.Array)
        self.db = db
        self.value = value
        self.arraytype = lltype.typeOf(value).OF

        name = '' #str(value).split()[1]
        self.make_name(name)

    def setup(self):
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
        r = "[%s]" % ", ".join([self.db.repr_constant(v)[1] for v in items])
        return l, r 

    def get_typerepr(self):
        arraylen = self.get_arrayvalue()[0]
        typeval = self.db.repr_type(self.arraytype)
        return "{ %s, [%s x %s] }" % (self.db.get_machine_word(),
                                      arraylen, typeval)

    def get_ref(self):
        typeval = self.db.repr_type(lltype.typeOf(self.value))
        p, c = lltype.parentlink(self.value)
        if p is None:
            ref = self.name
        else:
            ref = self.db.get_childref(p, c)

        ref = "cast(%s* %s to %s*)" % (self.get_typerepr(),
                                       ref,
                                       typeval)
        print 'KKKKKKKKKK', ref
        return ref

    def get_pbcref(self, toptr):
        p, c = lltype.parentlink(self.value)
        assert p is None, "child PBC arrays are NOT needed by rtyper"

        fromptr = "%s*" % self.get_typerepr()
        ref = "cast(%s %s to %s)" % (fromptr, self.name, toptr)
        print 'XXXXXXXXX', ref
        return ref

    def get_childref(self, index):
        return "getelementptr(%s* %s, int 0, uint 1, int %s)" % (
            self.get_typerepr(),
            self.name,
            index)
    
    def constantvalue(self):
        physicallen, arrayrepr = self.get_arrayvalue()
        typeval = self.db.repr_type(self.arraytype)

        # first length is logical, second is physical
        value = "%s %s, [%s x %s] %s" % (self.db.get_machine_word(),
                                         self.get_length(),
                                         physicallen,
                                         typeval,
                                         arrayrepr)

        s = "%s {%s}" % (self.get_typerepr(), value)
        return s

class ArrayNoLengthNode(ArrayNode):
    def get_typerepr(self):
        arraylen = self.get_arrayvalue()[0]
        typeval = self.db.repr_type(self.arraytype)
        return "{ [%s x %s] }" % (arraylen, typeval)
    
    def get_childref(self, index):
        return "getelementptr(%s* %s, int 0, int %s)" %(
            self.get_typerepr(),
            self.name,
            index)

    def constantvalue(self):
        physicallen, arrayrepr = self.get_arrayvalue()
        typeval = self.db.repr_type(self.arraytype)

        value = "[%s x %s] %s" % (physicallen,
                                  typeval,
                                  arrayrepr)

        s = "%s {%s}" % (self.get_typerepr(), value)
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

class VoidArrayNode(ConstantNode):
    __slots__ = "db value".split()
    prefix = '%voidarrayinstance'

    def __init__(self, db, value):
        assert isinstance(lltype.typeOf(value), lltype.Array)
        self.db = db
        self.value = value
        name = '' #str(value).split()[1]
        self.make_name(name)

    def constantvalue(self):
        return "{ %s } {%s %s}" % (self.db.get_machine_word(),
                                   self.db.get_machine_word(),
                                   len(self.value.items))
