import sys
from pypy.annotation.pairtype import pair
from pypy.annotation import model as annmodel
from pypy.objspace.flow.model import Variable, Constant, Block, Link
from pypy.objspace.flow.model import SpaceOperation
from pypy.rpython.lltype import Signed, Unsigned, Float, Char, Bool, Void
from pypy.rpython.lltype import LowLevelType, NonGcPtr, ContainerType
from pypy.rpython.lltype import FuncType, functionptr, typeOf
from pypy.tool.sourcetools import func_with_new_name, valid_identifier
from pypy.translator.unsimplify import insert_empty_block
from pypy.rpython.rmodel import Repr, inputconst, TyperError


debug = False
crash_on_first_typeerror = False

# XXX copied from pypy.translator.typer and modified.
#     We'll remove pypy.translator.typer at some point.
#     It also borrows a bit from pypy.translator.annrpython.

class RPythonTyper:

    def __init__(self, annotator):
        self.annotator = annotator
        self.reprs_by_id = {}
        self.reprs_by_content = {}
        self.specialized_ll_functions = {}
        self.class_reprs = {}
        self.instance_reprs = {}
        self.typererror = None
        # make the primitive_to_repr constant mapping
        self.primitive_to_repr = {}
        for s_primitive, lltype in annmodel.annotation_to_ll_map:
            r = self.getrepr(s_primitive)
            self.primitive_to_repr[r.lowleveltype] = r

    def getrepr(self, s_obj):
        # s_objs are not hashable... try hard to find a hash anyway
        try:
            result, s_obj = self.reprs_by_id[id(s_obj)]
        except KeyError:
            key = [s_obj.__class__]
            items = s_obj.__dict__.items()
            items.sort()
            for name, value in items:
                key.append(name)
                key.append(Constant(value))
            key = tuple(key)
            try:
                result = self.reprs_by_content[key]
            except KeyError:
                # here is the code that actually builds a Repr instance
                result = s_obj.rtyper_makerepr(self)
                assert not isinstance(result.lowleveltype, ContainerType), (
                    "missing a GcPtr or NonGcPtr in the type specification "
                    "of %s:\n%r" % (s_obj, result.lowleveltype))
                self.reprs_by_content[key] = result
                result.setup()
            self.reprs_by_id[id(s_obj)] = result, s_obj
        return result

    def binding(self, var):
        s_obj = self.annotator.binding(var, True)
        if s_obj is None:
            s_obj = annmodel.SomeObject()
        return s_obj

    def bindingrepr(self, var):
        return self.getrepr(self.binding(var))

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
        v.concretetype = self.bindingrepr(v).lowleveltype

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
                return  # cannot continue this block: no op.result.concretetype

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
            for a in [link.last_exception, link.last_exc_value]:
                if isinstance(a, Variable):
                    self.setconcretetype(a)
            for i in range(len(link.args)):
                a1 = link.args[i]
                a2 = link.target.inputargs[i]
                r_a2 = self.bindingrepr(a2)
                if isinstance(a1, Constant):
                    link.args[i] = inputconst(r_a2, a1.value)
                    continue   # the Constant was typed, done
                r_a1 = self.bindingrepr(a1)
                if r_a1 == r_a2:
                    continue   # no conversion needed
                newops = LowLevelOpList(self)
                try:
                    a1 = newops.convertvar(a1, r_a1, r_a2)
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
        if debug:
            print hop.spaceop.opname, hop.args_s
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
            op.result.concretetype = hop.r_result.lowleveltype
            if op.result.concretetype != resulttype:
                raise TyperError("inconsistent type for the result of '%s':\n"
                                 "annotator says  %s,\n"
                                 "whose lltype is %r\n"
                                 "but rtype* says %r" % (
                    op.opname, hop.s_result,
                    op.result.concretetype, resulttype))
            while resultvar in varmapping:
                resultvar = varmapping[resultvar]
            varmapping[resultvar] = op.result
        else:
            # translate_meth() returned a Constant
            assert isinstance(resultvar, Constant)
            if not hop.s_result.is_constant():
                raise TyperError("the annotator doesn't agree that '%s' "
                                 "returns a constant" % op.opname)
            if resultvar.value != hop.s_result.const:
                raise TyperError("constant mismatch: %r vs %r" % (
                    resultvar.value, hop.s_result.const))
            op.result.concretetype = hop.r_result.lowleveltype

    def gottypererror(self, e, block, position, llops):
        """Record a TyperError without crashing immediately.
        Put a 'TyperError' operation in the graph instead.
        """
        e.where = (block, position)
        if crash_on_first_typeerror:
            raise
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
    r_arg1 = hop.args_r[0]
    return r_arg1.rtype_%s(hop)
""" % (opname, opname) in globals(), loc
        # All binary operations
        for opname in annmodel.BINARY_OPERATIONS:
            exec """
def translate_op_%s(self, hop):
    r_arg1 = hop.args_r[0]
    r_arg2 = hop.args_r[1]
    return pair(r_arg1, r_arg2).rtype_%s(hop)
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
        llinputs = [self.bindingrepr(v).lowleveltype for v in graph.getargs()]
        s_output = a.binding(graph.getreturnvar(), None)
        if s_output is None:
            lloutput = Void
        else:
            lloutput = self.getrepr(s_output).lowleveltype
        FT = FuncType(llinputs, lloutput)
        return functionptr(FT, func.func_name, graph = graph, _callable = func)


# ____________________________________________________________


class HighLevelOp:
    nb_popped = 0

    def __init__(self, rtyper, spaceop, llops):
        self.rtyper   = rtyper
        self.spaceop  = spaceop
        self.nb_args  = len(spaceop.args)
        self.llops    = llops
        self.args_s   = [rtyper.binding(a) for a in spaceop.args]
        self.s_result = rtyper.binding(spaceop.result)
        self.args_r   = [rtyper.getrepr(s_a) for s_a in self.args_s]
        self.r_result = rtyper.getrepr(self.s_result)

    def inputarg(self, converted_to, arg):
        """Returns the arg'th input argument of the current operation,
        as a Variable or Constant converted to the requested type.
        'converted_to' should be a Repr instance or a Primitive low-level
        type.
        """
        v = self.spaceop.args[self.nb_popped + arg]
        if isinstance(v, Constant):
            return inputconst(converted_to, v.value)
        assert hasattr(v, 'concretetype')

        s_binding = self.args_s[arg]
        if s_binding.is_constant():
            return inputconst(converted_to, s_binding.const)

        if not isinstance(converted_to, Repr):
            converted_to = self.rtyper.primitive_to_repr[converted_to]
        r_binding = self.args_r[arg]
        return self.llops.convertvar(v, r_binding, converted_to)

    inputconst = staticmethod(inputconst)    # export via the HighLevelOp class

    def inputargs(self, *converted_to):
        assert len(converted_to) == self.nb_args, (
            "operation argument count mismatch: '%s' has %d+%d arguments" % (
            self.spaceop.opname, self.nb_popped, self.nb_args))
        vars = []
        for i in range(len(converted_to)):
            vars.append(self.inputarg(converted_to[i], i))
        return vars

    def genop(self, opname, args_v, resulttype=None):
        return self.llops.genop(opname, args_v, resulttype)

    def gendirectcall(self, ll_function, *args_v):
        return self.llops.gendirectcall(ll_function, *args_v)

    def r_s_popfirstarg(self):
        "Return and discard the first argument."
        self.nb_popped += 1
        self.nb_args -= 1
        return self.args_r.pop(0), self.args_s.pop(0)

# ____________________________________________________________

class LowLevelOpList(list):
    """A list with gen*() methods to build and append low-level
    operations to it.
    """
    def __init__(self, rtyper):
        self.rtyper = rtyper

    def convertvar(self, v, r_from, r_to):
        assert isinstance(v, Variable)
        if r_from != r_to:
            v = pair(r_from, r_to).convert_from_to(v, self)
            if v is NotImplemented:
                raise TyperError("don't know how to convert from %r to %r" %
                                 (r_from, r_to))
        return v

    def genop(self, opname, args_v, resulttype=None):
        vresult = Variable()
        self.append(SpaceOperation(opname, args_v, vresult))
        if resulttype is None:
            vresult.concretetype = Void
            return None
        else:
            if isinstance(resulttype, Repr):
                resulttype = resulttype.lowleveltype
            assert isinstance(resulttype, LowLevelType)
            vresult.concretetype = resulttype
            return vresult

    def gendirectcall(self, ll_function, *args_v):
        rtyper = self.rtyper
        spec_key = [ll_function]
        spec_name = [ll_function.func_name]
        args_s = []
        for v in args_v:
            if v.concretetype == Void:
                s_value = rtyper.binding(v)
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
            spec_graph = rtyper.annotator.translator.getflowgraph(spec_function)
            rtyper.annotator.build_types(spec_function, args_s)
            # cache the result
            self.rtyper.specialized_ll_functions[spec_key] = spec_function

        # build the 'direct_call' operation
        f = self.rtyper.getfunctionptr(spec_function)
        c = inputconst(typeOf(f), f)
        return self.genop('direct_call', [c]+list(args_v),
                          resulttype = typeOf(f).TO.RESULT)

    def gencapicall(self, cfnname, args_v, resulttype):
        if isinstance(resulttype, Repr):
            resulttype = resulttype.lowleveltype
        argtypes = [v.concretetype for v in args_v]
        FUNCTYPE = FuncType(argtypes, resulttype)
        f = functionptr(FUNCTYPE, cfnname, external="C")
        cf = inputconst(typeOf(f), f)
        return self.genop('direct_call', [cf]+list(args_v), resulttype)


# _______________________________________________________________________
# this has the side-effect of registering the unary and binary operations
# and the rtyper_chooserepr() methods
from pypy.rpython import robject
from pypy.rpython import rint, rbool, rfloat
from pypy.rpython import rlist, rstr
from pypy.rpython import rbuiltin, rpbc
from pypy.rpython import rptr
