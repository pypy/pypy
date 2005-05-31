import sys
from pypy.annotation.pairtype import pair
from pypy.annotation import model as annmodel
from pypy.objspace.flow.model import Variable, Constant, Block, Link
from pypy.objspace.flow.model import SpaceOperation
from pypy.rpython.lltype import Void, LowLevelType, NonGcPtr, ContainerType
from pypy.rpython.lltype import FuncType, functionptr, typeOf
from pypy.tool.sourcetools import func_with_new_name, valid_identifier
from pypy.translator.unsimplify import insert_empty_block


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
        self.typererror = None

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
        if self.typererror:
            exc, value, tb = self.typererror
            self.typererror = None
            #self.annotator.translator.view()
            raise exc, value, tb

    def setconcretetype(self, v):
        assert isinstance(v, Variable)
        s_value = self.annotator.binding(v, True)
        if s_value is not None:
            v.concretetype = s_value.lowleveltype()

    def specialize_block(self, block):
        # give the best possible types to the input args
        for a in block.inputargs:
            self.setconcretetype(a)

        # specialize all the operations, as far as possible
        if block.operations == ():   # return or except block
            return
        newops = LowLevelOpList(self)
        varmapping = {}
        for op in block.operations:
            try:
                hop = HighLevelOp(self, op, newops)
                self.translate_hl_to_ll(hop, varmapping)
            except TyperError, e:
                self.gottypererror(e, block, op, newops)

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
            for i in range(len(link.args)):
                a1 = link.args[i]
                ##if a1 in (link.last_exception, link.last_exc_value):# treated specially in gen_link
                ##    continue
                a2 = link.target.inputargs[i]
                s_a2 = self.annotator.binding(a2)
                if isinstance(a1, Constant):
                    link.args[i] = inputconst(s_a2.lowleveltype(), a1.value)
                    continue   # the Constant was typed, done
                s_a1 = self.annotator.binding(a1)
                if s_a1 == s_a2:
                    continue   # no conversion needed
                newops = LowLevelOpList(self)
                try:
                    a1 = newops.convertvar(a1, s_a1, s_a2)
                except TyperError, e:
                    self.gottypererror(e, block, link, newops)

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

    def translate_hl_to_ll(self, hop, varmapping):
        op = hop.spaceop
        translate_meth = getattr(self, 'translate_op_'+op.opname,
                                 self.missing_operation)
        resultvar = translate_meth(hop)
        if resultvar is None:
            # no return value
            if hop.s_result != annmodel.SomeImpossibleValue():
                raise TyperError("the annotator doesn't agree that '%s' "
                                 "has no return value" % op.opname)
            op.result.concretetype = Void
        elif isinstance(resultvar, Variable):
            # for simplicity of the translate_meth, resultvar is usually not
            # op.result here.  We have to replace resultvar with op.result
            # in all generated operations.
            resulttype = resultvar.concretetype
            op.result.concretetype = hop.s_result.lowleveltype()
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
            # translate_meth() returned a Constant
            if not hop.s_result.is_constant():
                raise TyperError("the annotator doesn't agree that '%s' "
                                 "returns a constant" % op.opname)
            if resultvar.value != hop.s_result.const:
                raise TyperError("constant mismatch: %r vs %r" % (
                    resultvar.value, hop.s_result.const))
            op.result.concretetype = hop.s_result.lowleveltype()

    def gottypererror(self, e, block, position, llops):
        """Record a TyperError without crashing immediately.
        Put a 'TyperError' operation in the graph instead.
        """
        e.where = (block, position)
        if self.typererror is None:
            self.typererror = sys.exc_info()
        c1 = inputconst(Void, Exception.__str__(e))
        llops.genop('TYPER ERROR', [c1], resulttype=Void)

    # __________ regular operations __________

    def _registeroperations(loc):
        # All unary operations
        for opname in annmodel.UNARY_OPERATIONS:
            exec """
def translate_op_%s(self, hop):
    s_arg1 = hop.args_s[0]
    return s_arg1.rtype_%s(hop)
""" % (opname, opname) in globals(), loc
        # All binary operations
        for opname in annmodel.BINARY_OPERATIONS:
            exec """
def translate_op_%s(self, hop):
    s_arg1 = hop.args_s[0]
    s_arg2 = hop.args_s[1]
    return pair(s_arg1, s_arg2).rtype_%s(hop)
""" % (opname, opname) in globals(), loc

    _registeroperations(locals())
    del _registeroperations

    # __________ irregular operations __________

    def translate_op_newlist(self, hop):
        return rlist.rtype_newlist(hop)

    def missing_operation(self, hop):
        raise TyperError("unimplemented operation: '%s'" % hop.spaceop.opname)

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

def inputconst(type, value):
    """Return a Constant with the given value, of the requested type.
    'type' can be a SomeXxx annotation or a low-level type.
    """
    if isinstance(type, LowLevelType):
        lowleveltype = type
    else:
        lowleveltype = type.lowleveltype()
    assert not isinstance(lowleveltype, ContainerType), (
        "missing a GcPtr or NonGcPtr in the type specification of %r" %
        (lowleveltype,))
    c = Constant(value)
    c.concretetype = lowleveltype
    return c

# ____________________________________________________________

class HighLevelOp:
    nb_popped = 0

    def __init__(self, rtyper, spaceop, llops):
        self.rtyper   = rtyper
        self.spaceop  = spaceop
        self.nb_args  = len(spaceop.args)
        self.llops    = llops
        self.args_s   = [rtyper.annotator.binding(a) for a in spaceop.args]
        self.s_result = rtyper.annotator.binding(spaceop.result)

    def inputarg(self, converted_to, arg):
        """Returns the arg'th input argument of the current operation,
        as a Variable or Constant converted to the requested type.
        'converted_to' can be a SomeXxx annotation or a primitive low-level
        type.
        """
        v = self.spaceop.args[self.nb_popped + arg]
        if isinstance(v, Constant):
            return inputconst(converted_to, v.value)

        s_binding = self.args_s[arg]
        if s_binding is None:
            s_binding = annmodel.SomeObject()
        if s_binding.is_constant():
            return inputconst(converted_to, s_binding.const)

        if isinstance(converted_to, LowLevelType):
            converted_to = annmodel.lltype_to_annotation(converted_to)
        return self.llops.convertvar(v, s_binding, converted_to)

    def inputargs(self, *converted_to):
        assert len(converted_to) == self.nb_args, (
            "operation argument count mismatch: '%s' has %d+%d arguments" % (
            self.spaceop.opname, self.nb_popped, self.nb_args))
        vars = []
        for i in range(len(converted_to)):
            vars.append(self.inputarg(converted_to[i], i))
        return vars

    inputconst = staticmethod(inputconst)    # export via the HighLevelOp class

    def genop(self, opname, args_v, resulttype=None):
        return self.llops.genop(opname, args_v, resulttype)

    def gendirectcall(self, ll_function, *args_v):
        return self.llops.gendirectcall(ll_function, *args_v)

    def s_popfirstarg(self):
        "Return and discard the first argument."
        self.nb_popped += 1
        self.nb_args -= 1
        return self.args_s.pop(0)

# ____________________________________________________________

class LowLevelOpList(list):
    """A list with gen*() methods to build and append low-level
    operations to it.
    """
    def __init__(self, rtyper):
        self.rtyper = rtyper

    def convertvar(self, v, s_from, s_to):
        assert isinstance(v, Variable)
        if s_from != s_to:
            v = pair(s_from, s_to).rtype_convert_from_to(v, self)
            if v is NotImplemented:
                raise TyperError("don't know how to convert from %r to %r" % (
                    s_from, s_to))
        return v

    def genop(self, opname, args_v, resulttype=None):
        vresult = Variable()
        self.append(SpaceOperation(opname, args_v, vresult))
        if resulttype is None:
            vresult.concretetype = Void
            return None
        else:
            vresult.concretetype = resulttype
            return vresult

    def gendirectcall(self, ll_function, *args_v):
        annotator = self.rtyper.annotator
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
            spec_name.append(valid_identifier(getattr(key, '__name__', key))
                             + suffix)
        spec_key = tuple(spec_key)
        try:
            spec_function = self.rtyper.specialized_ll_functions[spec_key]
        except KeyError:
            name = '_'.join(spec_name)
            spec_function = func_with_new_name(ll_function, name)
            # flow and annotate (the copy of) the low-level function
            spec_graph = annotator.translator.getflowgraph(spec_function)
            annotator.build_types(spec_function, args_s)
            # cache the result
            self.rtyper.specialized_ll_functions[spec_key] = spec_function

        # build the 'direct_call' operation
        f = self.rtyper.getfunctionptr(spec_function)
        c = inputconst(typeOf(f), f)
        return self.genop('direct_call', [c]+list(args_v),
                          resulttype = typeOf(f).TO.RESULT)

    def gencapicall(self, cfnname, args_v, resulttype):
        argtypes = [v.concretetype for v in args_v]
        FUNCTYPE = FuncType(argtypes, resulttype)
        f = functionptr(FUNCTYPE, cfnname, external="C")
        cf = inputconst(typeOf(f), f)
        return self.genop('direct_call', [cf]+list(args_v), resulttype)


# _______________________________________________________________________
# this has the side-effect of registering the unary and binary operations
from pypy.rpython import robject, rlist, rptr, rbuiltin, rint, rbool, rfloat
from pypy.rpython import rpbc
