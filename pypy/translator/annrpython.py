from __future__ import generators

from types import FunctionType, ClassType
from pypy.annotation import model as annmodel
from pypy.annotation.model import pair
from pypy.annotation.factory import ListFactory, DictFactory
from pypy.annotation.factory import BlockedInference, Bookkeeper
from pypy.objspace.flow.model import Variable, Constant, UndefinedConstant
from pypy.objspace.flow.model import SpaceOperation, FunctionGraph


class AnnotatorError(Exception):
    pass


class RPythonAnnotator:
    """Block annotator for RPython.
    See description in doc/transation/annotation.txt."""

    def __init__(self, translator=None):
        self.translator = translator
        self.pendingblocks = []  # list of (block, list-of-SomeValues-args)
        self.bindings = {}       # map Variables to SomeValues
        self.annotated = {}      # set of blocks already seen
        self.notify = {}         # {block: {factory-to-invalidate-when-done}}
        self.bookkeeper = Bookkeeper(self)

    #___ convenience high-level interface __________________

    def build_types(self, func_or_flowgraph, input_arg_types):
        """Recursively build annotations about the specific entry point."""
        if isinstance(func_or_flowgraph, FunctionGraph):
            flowgraph = func_or_flowgraph
        else:
            if self.translator is None:
                from pypy.translator.translator import Translator
                self.translator = Translator(func_or_flowgraph)
                self.translator.annotator = self
            flowgraph = self.translator.getflowgraph(func_or_flowgraph)
        # make input arguments and set their type
        input_arg_types = list(input_arg_types)
        nbarg = len(flowgraph.getargs())
        while len(input_arg_types) < nbarg:
            input_arg_types.append(object)
        inputcells = []
        for t in input_arg_types:
            if not isinstance(t, annmodel.SomeObject):
                t = annmodel.valueoftype(t)
            inputcells.append(t)
        
        # register the entry point
        self.addpendingblock(flowgraph.startblock, inputcells)
        # recursively proceed until no more pending block is left
        self.complete()
        return self.binding(flowgraph.getreturnvar())

    def gettype(self, variable):
        """Return the known type of a control flow graph variable,
        defaulting to 'object'."""
        if isinstance(variable, Constant):
            return type(variable.value)
        elif isinstance(variable, Variable):
            cell = self.bindings.get(variable)
            if cell:
                return cell.knowntype
            else:
                return object
        else:
            raise TypeError, ("Variable or Constant instance expected, "
                              "got %r" % (variable,))

    def getuserclasses(self):
        """Return a set of known user classes."""
        return self.bookkeeper.userclasses

    def getuserclassdefinitions(self):
        """Return a list of ClassDefs."""
        return self.bookkeeper.userclasseslist

    def getuserattributes(self, cls):
        """Enumerate the attributes of the given user class, as Variable()s."""
        clsdef = self.bookkeeper.userclasses[cls]
        for attr, s_value in clsdef.attrs.items():
            v = Variable(name=attr)
            self.bindings[v] = s_value
            yield v


    #___ medium-level interface ____________________________

    def addpendingblock(self, block, cells):
        """Register an entry point into block with the given input cells."""
        for a in cells:
            assert isinstance(a, annmodel.SomeObject)
        self.pendingblocks.append((block, cells))

    def complete(self):
        """Process pending blocks until none is left."""
        while self.pendingblocks:
            # XXX don't know if it is better to pop from the head or the tail.
            # but suspect from the tail is better in the new Factory model.
            block, cells = self.pendingblocks.pop()
            self.processblock(block, cells)
        if False in self.annotated.values():
            raise AnnotatorError('%d blocks are still blocked' %
                                 self.annotated.values().count(False))

    def binding(self, arg):
        "Gives the SomeValue corresponding to the given Variable or Constant."
        if isinstance(arg, Variable):
            return self.bindings[arg]
        elif isinstance(arg, UndefinedConstant):  # undefined local variables
            return annmodel.SomeImpossibleValue()
        elif isinstance(arg, Constant):
            return annmodel.immutablevalue(arg.value)
        else:
            raise TypeError, 'Variable or Constant expected, got %r' % (arg,)


    #___ interface for annotator.factory _______

    def recursivecall(self, func, factory, *args):
        graph = self.translator.getflowgraph(func)
        # self.notify[graph.returnblock] is a dictionary of
        # FuncCallFactories (call points to this func) which triggers a
        # reflow whenever the return block of this graph has been analysed.
        callfactories = self.notify.setdefault(graph.returnblock, {})
        callfactories[factory] = True
        # generalize the function's input arguments
        block = graph.startblock
        inputcells = list(args)
        # add default arguments if necessary
        missingargs = len(block.inputargs) - len(inputcells)
        if missingargs:
            assert missingargs >= 0
            assert missingargs <= len(func.func_defaults or ())
            for extra in func.func_defaults[-missingargs:]:
                inputcells.append(annmodel.immutablevalue(extra))
        self.addpendingblock(block, inputcells)
        # get the (current) return value
        v = graph.getreturnvar()
        return self.bindings.get(v, annmodel.SomeImpossibleValue())

    def reflowfromposition(self, position_key):
        block, index = position_key
        self.reflowpendingblock(block)


    #___ simplification (should be moved elsewhere?) _______

    # it should be!
    # now simplify_calls is moved to transform.py.
    # i kept reverse_binding here for future(?) purposes though. --sanxiyn

    def reverse_binding(self, known_variables, cell):
        """This is a hack."""
        # In simplify_calls, when we are trying to create the new
        # SpaceOperation, all we have are SomeValues.  But SpaceOperations take
        # Variables, not SomeValues.  Trouble is, we don't always have a
        # Variable that just happens to be bound to the given SomeValue.
        # A typical example would be if the tuple of arguments was created
        # from another basic block or even another function.  Well I guess
        # there is no clean solution, short of making the transformations
        # more syntactic (e.g. replacing a specific sequence of SpaceOperations
        # with another one).  This is a real hack because we have to use
        # the identity of 'cell'.
        if cell.is_constant():
            return Constant(cell.const)
        else:
            for v in known_variables:
                if self.bindings[v] is cell:
                    return v
            else:
                raise CannotSimplify

    def simplify(self):
        # Generic simpliciations
        from pypy.translator import transform
        transform.transform_graph(self)


    #___ flowing annotations in blocks _____________________

    def processblock(self, block, cells):
        # Important: this is not called recursively.
        # self.flowin() can only issue calls to self.addpendingblock().
        # The analysis of a block can be in three states:
        #  * block not in self.annotated:
        #      never seen the block.
        #  * self.annotated[block] == False:
        #      the input variables of the block are in self.bindings but we
        #      still have to consider all the operations in the block.
        #  * self.annotated[block] == True:
        #      analysis done (at least until we find we must generalize the
        #      input variables).

        #print '* processblock', block, cells
        if block not in self.annotated:
            self.bindinputargs(block, cells)
        elif cells is not None:
            self.mergeinputargs(block, cells)
        if not self.annotated[block]:
            self.annotated[block] = True
            try:
                self.flowin(block)
            except BlockedInference, e:
                #print '_'*60
                #print 'Blocked at %r:' % (e.break_at,)
                #import traceback, sys
                #traceback.print_tb(sys.exc_info()[2])
                self.annotated[block] = False   # failed, hopefully temporarily

    def reflowpendingblock(self, block):
        self.pendingblocks.append((block, None))
        assert block in self.annotated
        self.annotated[block] = False  # must re-flow

    def bindinputargs(self, block, inputcells):
        # Create the initial bindings for the input args of a block.
        for a, cell in zip(block.inputargs, inputcells):
            self.bindings[a] = cell
        self.annotated[block] = False  # must flowin.

    def mergeinputargs(self, block, inputcells):
        # Merge the new 'cells' with each of the block's existing input
        # variables.
        oldcells = [self.binding(a) for a in block.inputargs]
        unions = [annmodel.unionof(c1,c2) for c1, c2 in zip(oldcells,inputcells)]
        # if the merged cells changed, we must redo the analysis
        if unions != oldcells:
            self.bindinputargs(block, unions)

    def flowin(self, block):
        #print 'Flowing', block, [self.binding(a) for a in block.inputargs]
        for i in range(len(block.operations)):
            try:
                self.bookkeeper.enter((block, i))
                self.consider_op(block.operations[i])
            finally:
                self.bookkeeper.leave()
        for link in block.exits:
            cells = [self.binding(a) for a in link.args]
            self.addpendingblock(link.target, cells)
        if block in self.notify:
            # invalidate some factories when this block is done
            for factory in self.notify[block]:
                self.reflowfromposition(factory.position_key)


    #___ creating the annotations based on operations ______

    def consider_op(self,op):
        argcells = [self.binding(a) for a in op.args]
        consider_meth = getattr(self,'consider_op_'+op.opname,
                                self.default_consider_op)
        resultcell = consider_meth(*argcells)
        if resultcell is None:
            resultcell = annmodel.SomeImpossibleValue()  # no return value
        elif resultcell == annmodel.SomeImpossibleValue():
            raise BlockedInference  # the operation cannot succeed
        assert isinstance(resultcell, annmodel.SomeObject)
        assert isinstance(op.result, Variable)
        self.bindings[op.result] = resultcell   # bind resultcell to op.result

    def default_consider_op(self, *args):
        return annmodel.SomeObject()

    def _registeroperations(loc):
        # All unary operations
        for opname in annmodel.UNARY_OPERATIONS:
            exec """
def consider_op_%s(self, arg, *args):
    return arg.%s(*args)
""" % (opname, opname) in globals(), loc
        # All binary operations
        for opname in annmodel.BINARY_OPERATIONS:
            exec """
def consider_op_%s(self, arg1, arg2, *args):
    return pair(arg1,arg2).%s(*args)
""" % (opname, opname) in globals(), loc

    _registeroperations(locals())
    del _registeroperations

    def consider_op_newtuple(self, *args):
        return annmodel.SomeTuple(items = args)

    def consider_op_newlist(self, *args):
        factory = self.bookkeeper.getfactory(ListFactory)
        for a in args:
            factory.generalize(a)
        return factory.create()

    def consider_op_newdict(self, *args):
        assert not args, "XXX only supports newdict([])"
        factory = self.bookkeeper.getfactory(DictFactory)
        return factory.create()

##    def decode_simple_call(self, s_varargs, s_varkwds):
##        # XXX replace all uses of this with direct calls into annmodel
##        return annmodel.decode_simple_call(s_varargs, s_varkwds)

##    def consider_op_call(self, s_func, s_varargs, s_kwargs):
##        if not s_func.is_constant():
##            return annmodel.SomeObject()
##        func = s_func.const
        
##        # XXX: generalize this later
##        if func is range:
##            factory = self.getfactory(ListFactory)
##            factory.generalize(annmodel.SomeInteger())  # XXX nonneg=...
##            return factory.create()
##        elif func is pow:
##            args = self.decode_simple_call(s_varargs, s_kwargs)
##            if args is not None and len(args) == 2:
##                if (issubclass(args[0].knowntype, int) and
##                    issubclass(args[1].knowntype, int)):
##                    return annmodel.SomeInteger()
##        elif isinstance(func, FunctionType) and self.translator:
##            args = self.decode_simple_call(s_varargs, s_kwargs)
##            return self.translator.consider_call(self, func, args)
##        elif (isinstance(func, (type, ClassType)) and
##              func.__module__ != '__builtin__'):
##            # XXX flow into __init__/__new__
##            factory = self.getfactory(InstanceFactory, func, self.userclasses)
##            return factory.create()
##        elif isinstance(func,type):
##            return annmodel.valueoftype(func)
##        return annmodel.SomeObject()


##    def consider_op_setattr(self,obj,attr,newval):
##        objtype = self.heap.get(ANN.type,obj)
##        if objtype in self.userclasses:
##            attr = self.heap.get(ANN.const,attr)
##            if isinstance(attr, str):
##                # do we already know about this attribute?
##                attrdict = self.userclasses[objtype]
##                clscell = self.constant(objtype)
##                if attr not in attrdict:
##                    # no -> create it
##                    attrdict[attr] = True
##                    self.heap.set(ANN.instanceattr[attr], clscell, newval)
##                else:
##                    # yes -> update it
##                    self.heap.generalize(ANN.instanceattr[attr], clscell, newval)
##        return SomeValue()

##    def consider_op_getattr(self,obj,attr):
##        result = SomeValue()
##        objtype = self.heap.get(ANN.type,obj)
##        if objtype in self.userclasses:
##            attr = self.heap.get(ANN.const,attr)
##            if isinstance(attr, str):
##                # do we know something about this attribute?
##                attrdict = self.userclasses[objtype]
##                if attr in attrdict:
##                    # yes -> return the current annotation
##                    clscell = self.constant(objtype)
##                    return self.heap.get(ANN.instanceattr[attr], clscell)
##        return result
        

##    def consider_op_add(self, arg1, arg2):
##        result = SomeValue()
##        tp = self.heap.checktype
##        if tp(arg1, int) and tp(arg2, int):
##            self.heap.settype(result, int)
##        elif tp(arg1, (int, long)) and tp(arg2, (int, long)):
##            self.heap.settype(result, long)
##        if tp(arg1, str) and tp(arg2, str):
##            self.heap.settype(result, str)
##        if tp(arg1, list) and tp(arg2, list):
##            self.heap.settype(result, list)
##            # XXX propagate information about the type of the elements
##        return result

##    def consider_op_mul(self, arg1, arg2):
##        result = SomeValue()
##        tp = self.heap.checktype
##        if tp(arg1, int) and tp(arg2, int):
##            self.heap.settype(result, int)
##        elif tp(arg1, (int, long)) and tp(arg2, (int, long)):
##            self.heap.settype(result, long)
##        return result

##    def consider_op_inplace_add(self, arg1, arg2):
##        tp = self.heap.checktype
##        if tp(arg1, list) and tp(arg2, list):
##            # Annotations about the items of arg2 are merged with the ones about
##            # the items of arg1.  arg2 is not modified during this operation.
##            # result is arg1.
##            self.heap.kill(ANN.len, arg1)
##            item2 = self.heap.get(ANN.listitems, arg2)
##            self.heap.generalize(ANN.listitems, arg1, item2)
##            return arg1
##        else:
##            return self.consider_op_add(arg1, arg2)

##    def consider_op_sub(self, arg1, arg2):
##        result = SomeValue()
##        tp = self.heap.checktype
##        if tp(arg1, int) and tp(arg2, int):
##            self.heap.settype(result, int)
##        elif tp(arg1, (int, long)) and tp(arg2, (int, long)):
##            self.heap.settype(result, long)
##        return result

##    consider_op_and_ = consider_op_sub # trailing underline
##    consider_op_mod  = consider_op_sub
##    consider_op_inplace_lshift = consider_op_sub

##    def consider_op_is_true(self, arg):
##        return boolvalue

##    consider_op_not_ = consider_op_is_true

##    def consider_op_lt(self, arg1, arg2):
##        return boolvalue

##    consider_op_le = consider_op_lt
##    consider_op_eq = consider_op_lt
##    consider_op_ne = consider_op_lt
##    consider_op_gt = consider_op_lt
##    consider_op_ge = consider_op_lt

##    def consider_op_newslice(self, *args):
##        result = SomeValue()
##        self.heap.settype(result, slice)
##        return result

##    def consider_op_newdict(self, *args):
##        result = SomeValue()
##        self.heap.settype(result, dict)
##        if not args:
##            self.heap.set(ANN.len, result, 0)
##        return result

##    def consider_op_getitem(self, arg1, arg2):
##        tp = self.heap.checktype
##        if tp(arg2, int):
##            if tp(arg1, tuple):
##                index = self.heap.get(ANN.const, arg2)
##                if index is not mostgeneralvalue:
##                    return self.heap.get(ANN.tupleitem[index], arg1)
##            if tp(arg1, list):
##                return self.heap.get(ANN.listitems, arg1)
##        result = SomeValue()
##        if tp(arg2, slice):
##            self.heap.copytype(arg1, result)
##            # XXX copy some information about the items
##        return result

##    def decode_simple_call(self, varargs_cell, varkwds_cell):
##        nbargs = self.heap.get(ANN.len, varargs_cell)
##        if nbargs is mostgeneralvalue:
##            return None
##        arg_cells = [self.heap.get(ANN.tupleitem[j], varargs_cell)
##                     for j in range(nbargs)]
##        nbkwds = self.heap.get(ANN.len, varkwds_cell)
##        if nbkwds != 0:
##            return None  # XXX deal with dictionaries with constant keys
##        return arg_cells

##    def consider_op_call(self, func, varargs, kwargs):
##        result = SomeValue()
##        tp = self.heap.checktype
##        func = self.heap.get(ANN.const, func)
##        # XXX: generalize this later
##        if func is range:
##            self.heap.settype(result, list)
##        elif func is pow:
##            args = self.decode_simple_call(varargs, kwargs)
##            if args is not None and len(args) == 2:
##                if tp(args[0], int) and tp(args[1], int):
##                    self.heap.settype(result, int)
##        elif isinstance(func, FunctionType) and self.translator:
##            args = self.decode_simple_call(varargs, kwargs)
##            return self.translator.consider_call(self, func, args)
##        elif isinstance(func,type):
##            # XXX flow into __init__/__new__
##            self.heap.settype(result,func)
##            if func.__module__ != '__builtin__':
##                self.userclasses.setdefault(func, {})
##        return result

##    def consider_const(self, constvalue):
##        result = SomeValue()
##        self.heap.set(ANN.const, result, constvalue)
##        self.heap.settype(result, type(constvalue))
##        if isinstance(constvalue, tuple):
##            pass # XXX say something about the elements
##        return result


class CannotSimplify(Exception):
    pass
