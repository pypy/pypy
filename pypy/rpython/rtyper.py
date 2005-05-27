from pypy.annotation.pairtype import pair
from pypy.annotation import model as annmodel
from pypy.objspace.flow.model import Variable, Constant, Block, Link
from pypy.objspace.flow.model import SpaceOperation
from pypy.rpython.lltype import Void, LowLevelType, NonGcPtr, ContainerType
from pypy.rpython.lltype import FuncType, functionptr, typeOf
from pypy.tool.tls import tlsobject
from pypy.tool.sourcetools import func_with_new_name, valid_identifier
from pypy.translator.unsimplify import insert_empty_block

TLS = tlsobject()


# XXX copied from pypy.translator.typer and modified.
#     We'll remove pypy.translator.typer at some point.
#     It also borrows a bit from pypy.translator.annrpython.

class TyperError(Exception):
    def __str__(self):
        result = Exception.__str__(self)
        if hasattr(self, 'where'):
            result += '\n.. %r\n.. %r' % self.where
        return result


class RPythonTyper:

    def __init__(self, annotator):
        self.annotator = annotator
        self.specialized_ll_functions = {}

    def specialize(self):
        """Main entry point: specialize all annotated blocks of the program."""
        # new blocks can be created as a result of specialize_block(), so
        # we need to be careful about the loop here.
        already_seen = {}
        pending = self.annotator.annotated.keys()
        while pending:
            for block in pending:
                self.specialize_block(block)
                already_seen[block] = True
            pending = [block for block in self.annotator.annotated
                             if block not in already_seen]

    def setconcretetype(self, v):
        assert isinstance(v, Variable)
        s_value = self.annotator.binding(v, True)
        if s_value is not None:
            v.concretetype = s_value.lowleveltype()

    def enter_operation(self, op, newops):
        TLS.rtyper = self
        TLS.currentoperation = op
        TLS.newops = newops

    def leave_operation(self):
        del TLS.rtyper
        del TLS.currentoperation
        del TLS.newops

    def specialize_block(self, block):
        # give the best possible types to the input args
        for a in block.inputargs:
            self.setconcretetype(a)

        # specialize all the operations, as far as possible
        if block.operations == ():   # return or except block
            return
        newops = []
        varmapping = {}
        for op in block.operations:
            try:
                args = list(op.args)
                bindings = [self.annotator.binding(a, True) for a in args]

                self.enter_operation(op, newops)
                try:
                    self.consider_op(op, varmapping)
                finally:
                    self.leave_operation()

            except TyperError, e:
                e.where = (block, op)
                raise

        block.operations[:] = newops
        # multiple renamings (v1->v2->v3->...) are possible
        while True:
            done = True
            for v1, v2 in varmapping.items():
                if v2 in varmapping:
                    varmapping[v1] = varmapping[v2]
                    done = False
            if done:
                break
        block.renamevariables(varmapping)
        self.insert_link_conversions(block)

    def insert_link_conversions(self, block):
        # insert the needed conversions on the links
        can_insert_here = block.exitswitch is None and len(block.exits) == 1
        for link in block.exits:
            try:
                for i in range(len(link.args)):
                    a1 = link.args[i]
                    ##if a1 in (link.last_exception, link.last_exc_value):# treated specially in gen_link
                    ##    continue
                    a2 = link.target.inputargs[i]
                    s_a1 = self.annotator.binding(a1)
                    s_a2 = self.annotator.binding(a2)
                    if s_a1 == s_a2:
                        continue   # no conversion needed
                    newops = []
                    self.enter_operation(None, newops)
                    try:
                        a1 = convertvar(a1, s_a1, s_a2)
                    finally:
                        self.leave_operation()
                    if newops and not can_insert_here:
                        # cannot insert conversion operations around a single
                        # link, unless it is the only exit of this block.
                        # create a new block along the link...
                        newblock = insert_empty_block(self.annotator.translator,
                                                      link)
                        # ...and do the conversions there.
                        self.insert_link_conversions(newblock)
                        break   # done with this link
                    else:
                        block.operations.extend(newops)
                        link.args[i] = a1
            except TyperError, e:
                e.where = (block, link)
                raise

    def consider_op(self, op, varmapping):
        argcells = [self.annotator.binding(a) for a in op.args]
        consider_meth = getattr(self, 'consider_op_'+op.opname)
        resultvar = consider_meth(*argcells)
        s_expected = self.annotator.binding(op.result)
        if resultvar is None:
            # no return value
            if s_expected != annmodel.SomeImpossibleValue():
                raise TyperError("the annotator doesn't agree that '%s' "
                                 "has no return value" % op.opname)
            op.result.concretetype = Void
        elif isinstance(resultvar, Variable):
            # for simplicity of the consider_meth, resultvar is usually not
            # op.result here.  We have to replace resultvar with op.result
            # in all generated operations.
            resulttype = resultvar.concretetype
            op.result.concretetype = s_expected.lowleveltype()
            if op.result.concretetype != resulttype:
                raise TyperError("inconsistent type for the result of '%s':\n"
                                 "annotator says %r\n"
                                 "   rtyper says %r" % (op.opname,
                                                        op.result.concretetype,
                                                        resulttype))
            while resultvar in varmapping:
                resultvar = varmapping[resultvar]
            varmapping[resultvar] = op.result
        else:
            # consider_meth() can actually generate no operation and return
            # a Constant.
            if not s_expected.is_constant():
                raise TyperError("the annotator doesn't agree that '%s' "
                                 "returns a constant" % op.opname)
            if resultvar.value != s_expected.const:
                raise TyperError("constant mismatch: %r vs %r" % (
                    resultvar.value, s_expected.const))
            op.result.concretetype = s_expected.lowleveltype()

    # __________ regular operations __________

    def _registeroperations(loc):
        # All unary operations
        for opname in annmodel.UNARY_OPERATIONS:
            exec """
def consider_op_%s(self, arg, *args):
    return arg.rtype_%s(*args)
""" % (opname, opname) in globals(), loc
        # All binary operations
        for opname in annmodel.BINARY_OPERATIONS:
            exec """
def consider_op_%s(self, arg1, arg2, *args):
    return pair(arg1,arg2).rtype_%s(*args)
""" % (opname, opname) in globals(), loc

    _registeroperations(locals())
    del _registeroperations

    # __________ irregular operations __________

    def consider_op_newlist(self, *items_s):
        return rlist.rtype_newlist(*items_s)

    # __________ utilities __________

    def getfunctionptr(self, func):
        """Make a functionptr from the given Python function."""
        a = self.annotator
        graph = a.translator.getflowgraph(func)
        llinputs = [a.binding(v).lowleveltype() for v in graph.getargs()]
        s_output = a.binding(graph.getreturnvar(), None)
        if s_output is None:
            lloutput = Void
        else:
            lloutput = s_output.lowleveltype()
        FT = FuncType(llinputs, lloutput)
        return functionptr(FT, func.func_name, graph = graph, _callable = func)

# ____________________________________________________________
#
#  Global helpers, working on the current operation (as stored in TLS)

def _requestedtype(s_requested):
    if isinstance(s_requested, LowLevelType):
        lowleveltype = s_requested
        s_requested = annmodel.lltype_to_annotation(lowleveltype)
    elif isinstance(s_requested, annmodel.SomeObject):
        lowleveltype = s_requested.lowleveltype()
    else:
        raise TypeError("SomeObject or LowLevelType expected, got %r" % (
            s_requested,))
    return s_requested, lowleveltype

def receiveconst(s_requested, value):
    """Return a Constant with the given value, of the requested type.
    s_requested can be a SomeXxx annotation or a primitive low-level type.
    """
    if isinstance(s_requested, LowLevelType):
        lowleveltype = s_requested
    else:
        lowleveltype = s_requested.lowleveltype()
    assert not isinstance(lowleveltype, ContainerType), (
        "missing a GcPtr or NonGcPtr in the type specification of %r" %
        (lowleveltype,))
    c = Constant(value)
    c.concretetype = lowleveltype
    return c

def receive(s_requested, arg):
    """Returns the arg'th input argument of the current operation,
    as a Variable or Constant converted to the requested type.
    s_requested can be a SomeXxx annotation or a primitive low-level type.
    """
    v = TLS.currentoperation.args[arg]
    if isinstance(v, Constant):
        return receiveconst(s_requested, v.value)

    s_binding = TLS.rtyper.annotator.binding(v, True)
    if s_binding is None:
        s_binding = annmodel.SomeObject()
    if s_binding.is_constant():
        return receiveconst(s_requested, s_binding.const)

    s_requested, lowleveltype = _requestedtype(s_requested)
    return convertvar(v, s_binding, s_requested)

def convertvar(v, s_from, s_to):
    if s_from != s_to:
        v = pair(s_from, s_to).rtype_convert_from_to(v)
    return v


def peek_at_result_annotation():
    return TLS.rtyper.annotator.binding(TLS.currentoperation.result)


def direct_call(ll_function, *args_v):
    annotator = TLS.rtyper.annotator
    spec_key = [ll_function]
    spec_name = [ll_function.func_name]
    args_s = []
    for v in args_v:
        s_value = annotator.binding(v, True)
        if s_value is None:
            s_value = annmodel.SomeObject()
        if v.concretetype == Void:
            if not s_value.is_constant():
                raise TyperError("non-constant variable of type Void")
            key = s_value.const       # specialize by constant value
            args_s.append(s_value)
            suffix = 'Const'
        else:
            key = v.concretetype      # specialize by low-level type
            args_s.append(annmodel.lltype_to_annotation(key))
            suffix = ''
        spec_key.append(key)
        spec_name.append(valid_identifier(getattr(key, '__name__', key))+suffix)
    spec_key = tuple(spec_key)
    try:
        spec_function = TLS.rtyper.specialized_ll_functions[spec_key]
    except KeyError:
        name = '_'.join(spec_name)
        spec_function = func_with_new_name(ll_function, name)
        # flow and annotate (the copy of) the low-level function
        spec_graph = annotator.translator.getflowgraph(spec_function)
        annotator.build_types(spec_function, args_s)
        # cache the result
        TLS.rtyper.specialized_ll_functions[spec_key] = spec_function

    # build the 'direct_call' operation
    f = TLS.rtyper.getfunctionptr(spec_function)
    c = receiveconst(typeOf(f), f)
    return direct_op('direct_call', [c]+list(args_v),
                     resulttype = typeOf(f).TO.RESULT)


def direct_op(opname, args, resulttype=None):
    v = Variable()
    TLS.newops.append(SpaceOperation(opname, args, v))
    if resulttype is None:
        v.concretetype = Void
        return None
    else:
        v.concretetype = resulttype
        return v


# _______________________________________________________________________
# this has the side-effect of registering the unary and binary operations
from pypy.rpython import robject, rlist, rptr, rbuiltin, rint, rbool, rfloat
from pypy.rpython import rpbc
