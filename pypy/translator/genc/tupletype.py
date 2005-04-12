from __future__ import generators
from pypy.translator.genc.basetype import CType
from pypy.objspace.flow.model import SpaceOperation, Constant, Variable


class CTupleType(CType):

    Counter = {}

    def __init__(self, translator, itemtypes):
        super(CTupleType, self).__init__(translator)
        self.itemtypes = itemtypes
        self.typename = 'tuple%d_%d' % (
            len(itemtypes),
            CTupleType.Counter.setdefault(len(itemtypes), 0))
        CTupleType.Counter[len(itemtypes)] += 1
        self.error_return = 'err_' + self.typename
        self.cnames = {}
        self.globaldecl = []

    def debugname(self):
        # a nice textual name for debugging...
        itemnames = [ct.debugname() for ct in self.itemtypes]
        return 'tuple(%s)' % (', '.join(itemnames),)

    def init_globals(self, genc):
        yield 'typedef struct {'
        for i, ct in zip(range(len(self.itemtypes)), self.itemtypes):
            yield '\t%s f%d;' % (ct.typename, i)
        yield '} %s;' % self.typename
        self.globaldecl.append(
            '%s %s;  /* uninitialized */' % (self.typename,
                                             self.error_return))
        self.generate_xxxref('INC')
        self.generate_xxxref('DEC')
        self.generate_conv_to_obj()
        self.generate_conv_from_obj()

    def collect_globals(self, genc):
        result = self.globaldecl
        self.globaldecl = []
        return result

    def nameof(self, tup, debug=None):
        try:
            return self.cnames[tup]
        except KeyError:
            genc = self.genc()
            name = genc.namespace.uniquename('gtup')
            self.globaldecl.append('%s %s = {' % (self.typename, name))
            lines = []
            for x, ct in zip(tup, self.itemtypes):
                lines.append('\t' + genc.nameofvalue(x, ct))
            self.globaldecl.append(',\n'.join(lines))
            self.globaldecl.append('};')
            self.cnames[tup] = name
            return name

    def generate_xxxref(self, op):
        self.globaldecl.append('#define OP_%sREF_%s(tup) \\' % (op,
                                                                self.typename))
        for i in range(len(self.itemtypes)):
            self.globaldecl.append('\tOP_%sREF_%s(tup.f%d) \\' % (
                op, self.itemtypes[i].typename, i))
        self.globaldecl.append('\t/* end */')

    def generate_conv_to_obj(self):
        # build a function that converts from our custom struct
        # format to a full-blown PyTupleObject.
        self.globaldecl += [
            "static PyObject* CONV_TO_OBJ_%s(%s tup)" % (self.typename,
                                                         self.typename),
            "{",
            "\tPyObject* o;",
            "\tPyObject* result = PyTuple_New(%d);" % len(self.itemtypes),
            "\tif (result == NULL) return NULL;",
            ]
        for i, ct in zip(range(len(self.itemtypes)), self.itemtypes):
            self.globaldecl += [
                "\to = CONV_TO_OBJ_%s(tup.f%d);" % (ct.typename, i),
                "\tif (o == NULL) goto err;",
                "\tPyTuple_SET_ITEM(result, %d, o);" % i,
                ]
        self.globaldecl += [
            "\treturn result;",
            "   err:",
            "\tPy_DECREF(result);",
            "\treturn NULL;",
            "}",
            ]

    def generate_conv_from_obj(self):
        # build a function that decodes a PyTupleObject and store it
        # into our custom struct format.
        self.globaldecl += [
            "static %s CONV_FROM_OBJ_%s(PyObject* obj)" % (self.typename,
                                                           self.typename),
            "{",
            "\t%s result;" % self.typename,
            "\tif (PyTuple_Size(obj) != %d) { /* also if not a tuple */" %
                len(self.itemtypes),
            "\t\tPyErr_SetString(PyExc_TypeError,",
            '\t\t\t"tuple of length %d expected");' % len(self.itemtypes),
            "\t\tgoto err0;",
            "\t}",
            ]
        for i, ct in zip(range(len(self.itemtypes)), self.itemtypes):
            self.globaldecl += [
                "\tresult.f%d = CONV_FROM_OBJ_%s(PyTuple_GET_ITEM(obj, %d));" %
                    (i, ct.typename, i),
                "\tif (PyErr_Occurred()) goto err%d;" % i,
                ]
        self.globaldecl += [
            "\treturn result;",
            ]
        # errors may occur in the middle of the construction of the struct,
        # we must decref only the fields that have been successfully built
        # so far...
        errlabels = range(len(self.itemtypes)) or [0]
        errlabels.reverse()
        for i in errlabels:
            self.globaldecl.append("   err%d:" % i)
            if i > 0:
                self.globaldecl.append('\tOP_DECREF_%s(result.f%d)' % (
                    self.itemtypes[i-1].typename, i-1))
        self.globaldecl += [
            "\treturn %s;" % self.error_return,
            "}",
            ]
