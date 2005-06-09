from __future__ import generators
from pypy.translator.genc.basetype import CType
from pypy.objspace.flow.model import SpaceOperation, Constant, Variable


class CListType(CType):
    error_return  = 'NULL'

    Counter = 0

    def __init__(self, translator, itemtype):
        super(CListType, self).__init__(translator)
        self.itemtype = itemtype
        self.itemtypename = itemtype.typename
        self.typename = 'list_%d' % CListType.Counter
        CListType.Counter += 1
        self.cnames = {}
        self.globaldecl = []

    def debugname(self):
        # a nice textual name for debugging...
        return 'list(%s)' % (self.itemtype.debugname(),)

    def init_globals(self, genc):
        yield genc.loadincludefile('list_template.h') % {
            'typename'    : self.typename,
            'TYPENAME'    : self.typename.upper(),
            'itemtypename': self.itemtypename,
            }

    def collect_globals(self, genc):
        result = self.globaldecl
        self.globaldecl = []
        return result

    def nameof(self, lst, debug=None):
        key = Constant(lst).key
        try:
            return self.cnames[key]
        except KeyError:
            genc = self.genc()
            name = genc.namespace.uniquename('g%dlst' % len(lst))
            self.globaldecl.append('struct s_%s %s = {' % (self.typename, name))
            self.globaldecl.append('\t1,  /* refcount */')
            self.globaldecl.append('\t%d, /* count */' % len(lst))
            if len(lst) == 0:
                self.globaldecl.append('\tNULL /* items */')
            else:
                self.globaldecl.append('\t{   /* items */')
                ct = self.itemtype
                trail = [','] * (len(lst)-1) + ['']
                for x, comma in zip(lst, trail):
                    self.globaldecl.append('\t\t' +
                                           genc.nameofvalue(x, ct) +
                                           comma)
                self.globaldecl.append('\t}')
            self.globaldecl.append('}')
            self.cnames[key] = name
            return name

    # ____________________________________________________________

    def spec_newlist(self, typer, op):
        TInt  = typer.TInt
        TNone = typer.TNone
        ct = self.itemtype
        n = len(op.args)
        v2 = op.result
        yield typer.typed_op(SpaceOperation('alloc_'+self.typename,
                       [Constant(n)], v2),    # args, ret
                       [TInt       ], self)   # args_t, ret_t
        for i in range(len(op.args)):
            vitem = op.args[i]
            v0 = Variable()
            yield typer.typed_op(SpaceOperation('list_fastsetitem',
                       [v2,   Constant(i), vitem], v0), # args, ret
                       [self, TInt,        ct   ], TNone) # a_t,r_t
            yield typer.incref_op(vitem)
        v0 = Variable()
        yield typer.typed_op(SpaceOperation('list_setcount',
                       [v2,   Constant(n)], v0), # args, ret
                       [self, TInt,      ], TNone) # a_t,r_t

    def spec_getitem(self, typer, op):
        ct = self.itemtype
        yield typer.typed_op(op, [self, typer.TInt], ct,
                             newopname='list_getitem')
        yield typer.incref_op(op.result)
