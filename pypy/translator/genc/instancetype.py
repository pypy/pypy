from __future__ import generators
from pypy.objspace.flow.model import Constant, SpaceOperation
from pypy.translator.genc.heapobjecttype import CHeapObjectType
from pypy.translator.genc.tupletype import CTupleType


class CInstanceType(CHeapObjectType):
    """The type 'pointer to a class instance in the heap."""

    def __init__(self, translator, fieldnames, fieldtypes, classname):
        self.fieldnames = fieldnames
        self.fieldtypes = fieldtypes
        contenttype = translator.getconcretetype(CTupleType, fieldtypes)
        super(CInstanceType, self).__init__(translator, None, contenttype,
                                            classname)
        self.fields = {}  # XXX parent
        for name, ct in zip(fieldnames, fieldtypes):
            self.fields[name] = ct

    def init_globals(self, genc):
        for line in super(CInstanceType, self).init_globals(genc):
            yield line
        for i, name in zip(range(len(self.fieldnames)), self.fieldnames):
            yield '#define INST_ATTR_%s__%s(x)    (x)->ext.f%d' % (
                self.typename, name, i)

    # ____________________________________________________________

    def spec_getattr(self, typer, op):
        if not isinstance(op.args[1], Constant):
            raise NotImplementedError
        attrname = op.args[1].value
        try:
            ct = self.fields[attrname]
        except KeyError:
            print "* warning, no field %s in %s" % (attrname, self.typename)
            raise NotImplementedError
        TPyObject = typer.TPyObject
        yield typer.typed_op(op, [self, TPyObject], ct,   # args_t, ret_t
                             newopname='inst_getattr')
        yield typer.incref_op(op.result)

    def spec_setattr(self, typer, op):
        if not isinstance(op.args[1], Constant):
            raise NotImplementedError
        attrname = op.args[1].value
        try:
            ct = self.fields[attrname]
        except KeyError:
            print "* warning, no field %s in %s" % (attrname, self.typename)
            raise NotImplementedError
        TNone = typer.TNone
        TPyObject = typer.TPyObject
        # XXX decref existing value first
        yield typer.typed_op(op, [self, TPyObject, ct], TNone,  # args_t, ret_t
                             newopname='inst_setattr')
        yield typer.incref_op(op.args[2])
