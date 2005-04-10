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

    def debugname(self):
        # a nice textual name for debugging...
        itemnames = [ct.debugname() for ct in self.itemtypes]
        return 'tuple (%s)' % (', '.join(itemnames),)

    def fieldnames(self):
        return ['f%d' % i for i in range(len(self.itemtypes))]

    def init_globals(self, genc):
        yield '%s {' % self.structname
        for ct, name in zip(self.itemtypes, self.fieldnames()):
            yield '\t' + ct.ctypetemplate % (name,) + ';'
        yield '};'
        yield '%s %s;  /* uninitialized */' % (self.structname,
                                               self.error_return)

    def collect_globals(self, genc):
        result = self.globaldecl
        self.globaldecl = []
        return result

    def nameof(self, tup, debug=None):
        genc = self.genc()
        try:
            return self.cnames[tup]
        except KeyError:
            name = genc.namespace.uniquename('gtup')
            self.globaldecl.append('%s %s = {' % (self.structname, name))
            lines = []
            for x, ct in zip(tup, self.itemtypes):
                lines.append('\t' + genc.nameofvalue(x, ct))
            self.globaldecl.append(',\n'.join(lines))
            self.globaldecl.append('};')
            self.cnames[tup] = name
            return name

    def convert_to_obj(self, typer, v1, v2):
        TPyObj = typer.TPyObject
        TNone  = typer.TNone
        TInt   = typer.TInt
        pyobjitems_v = []
        for i, ct in zip(range(len(self.itemtypes)), self.itemtypes):
            # read the ith field out of the "struct" tuple
            vitem = Variable()
            yield typer.typed_op(SpaceOperation('tuple_getitem',
                                   [v1,   Constant(i)], vitem),  # args, retval
                                   [self, TInt       ], ct    )  # arg_t, ret_t
            pyobjitems_v.append(vitem)
        # create a new PyTupleObject with these values
        # note that typed_op() will insert the conversion of vitem if needed
        yield typer.typed_op(SpaceOperation('newtuple',
                                   pyobjitems_v, v2),    # args, retval
                     [TPyObj]*len(pyobjitems_v), TPyObj) # arg_t, ret_t

    def convert_from_obj(self, typer, v1, v2):
        TPyObj = typer.TPyObject
        TNone  = typer.TNone
        TInt   = typer.TInt
        yield typer.typed_op(SpaceOperation('tuple_new', [], v2),
                                                         [], self)
        for i, ct in zip(range(len(self.itemtypes)), self.itemtypes):
            # read the ith field out of the PyTupleObject
            vitem = Variable()
            yield typer.typed_op(SpaceOperation('pytuple_getitem',
                                   [v1,     Constant(i)], vitem), # args, retval
                                   [TPyObj, TInt       ], TPyObj) # arg_t, ret_t
            # store it into the "struct" tuple
            # note that typed_op() will insert the conversion of vitem if needed
            v0 = Variable()
            yield typer.typed_op(SpaceOperation('tuple_setitem',
                                   [v2,   Constant(i), vitem], v0),  # args, ret
                                   [self, TInt,        ct   ], TNone) # a_t, r_t
