from __future__ import generators
from pypy.translator.genc.t_simple import CType
from pypy.objspace.flow.model import SpaceOperation, Constant, Variable


class CTupleType(CType):

    Counter = {}

    def __init__(self, translator, itemtypes):
        super(CTupleType, self).__init__(translator)
        self.itemtypes = itemtypes
        self.structname = 'struct tuple%d_%d' % (
            len(itemtypes),
            CTupleType.Counter.setdefault(len(itemtypes), 0))
        CTupleType.Counter[len(itemtypes)] += 1
        self.ctypetemplate = self.structname + ' %s'
        self.error_return = self.structname.replace(' ', '_err_')
        self.cnames = {}
        self.globaldecl = []
        self._conv_to_obj = None
        self._conv_from_obj = None

    def debugname(self):
        # a nice textual name for debugging...
        itemnames = [ct.debugname() for ct in self.itemtypes]
        return 'tuple(%s)' % (', '.join(itemnames),)

    def fieldnames(self):
        return ['f%d' % i for i in range(len(self.itemtypes))]

    def init_globals(self, genc):
        yield '%s {' % self.structname
        for ct, name in zip(self.itemtypes, self.fieldnames()):
            yield '\t' + ct.ctypetemplate % (name,) + ';'
        yield '};'
        self.globaldecl.append(
            '%s %s;  /* uninitialized */' % (self.structname,
                                             self.error_return))

    def collect_globals(self, genc):
        result = self.globaldecl
        self.globaldecl = []
        return result

    def cincref(self, expr):
        result = []
        for i in range(len(self.itemtypes)):
            line = self.itemtypes[i].cincref('%s.f%d' % (expr, i))
            if line:
                result.append(line)
        return ' '.join(result)

    def cdecref(self, expr):
        result = []
        for i in range(len(self.itemtypes)):
            line = self.itemtypes[i].cdecref('%s.f%d' % (expr, i))
            if line:
                result.append(line)
        return '\t'.join(result)

    def nameof(self, tup, debug=None):
        try:
            return self.cnames[tup]
        except KeyError:
            genc = self.genc()
            name = genc.namespace.uniquename('gtup')
            self.globaldecl.append('%s %s = {' % (self.structname, name))
            lines = []
            for x, ct in zip(tup, self.itemtypes):
                lines.append('\t' + genc.nameofvalue(x, ct))
            self.globaldecl.append(',\n'.join(lines))
            self.globaldecl.append('};')
            self.cnames[tup] = name
            return name

    def fn_conv_to_obj(self):
        if self._conv_to_obj is None:
            # build a function that converts from our custom struct
            # format to a full-blown PyTupleObject.
            self._conv_to_obj = self.structname.replace(' ', '_to_obj_')
            self.globaldecl += [
                "static PyObject* %s(%s tup)" % (self._conv_to_obj,
                                                 self.structname),
                "{",
                "\tPyObject* o;",
                "\tPyObject* result = PyTuple_New(%d);" % len(self.itemtypes),
                "\tif (result == NULL) return NULL;",
                ]
            for i, ct in zip(range(len(self.itemtypes)), self.itemtypes):
                self.globaldecl += [
                    "\to = %s(tup.f%d);" % (ct.fn_conv_to_obj(), i),
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
        return self._conv_to_obj

    def fn_conv_from_obj(self):
        if self._conv_from_obj is None:
            # build a function that decodes a PyTupleObject and store it
            # into our custom struct format.
            self._conv_from_obj = self.structname.replace(' ', '_from_obj_')
            self.globaldecl += [
                "static %s %s(PyObject* obj)" % (self.structname,
                                                 self._conv_from_obj),
                "{",
                "\t%s result;" % self.structname,
                "\tif (PyTuple_Size(obj) != %d) { /* also if not a tuple */" %
                    len(self.itemtypes),
                "\t\tPyErr_SetString(PyExc_TypeError,",
                '\t\t\t"tuple of length %d expected");' % len(self.itemtypes),
                "\t\tgoto err0;",
                "\t}",
                ]
            for i, ct in zip(range(len(self.itemtypes)), self.itemtypes):
                self.globaldecl += [
                    "\tresult.f%d = %s(PyTuple_GET_ITEM(obj, %d));" % (
                        i, ct.fn_conv_from_obj(), i),
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
                    cdecref = self.itemtypes[i-1].cdecref('result.f%d' % (i-1))
                    if cdecref:
                        self.globaldecl.append('\t' + cdecref)
            self.globaldecl += [
                "\treturn %s;" % self.error_return,
                "}",
                ]
        return self._conv_from_obj
