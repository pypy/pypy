from __future__ import generators

from types import FunctionType, ClassType
from pypy.annotation import model as annmodel
from pypy.annotation.model import pair
from pypy.annotation.factory import ListFactory, DictFactory, BlockedInference
from pypy.annotation.bookkeeper import Bookkeeper
from pypy.objspace.flow.model import Variable, Constant, UndefinedConstant
from pypy.objspace.flow.model import SpaceOperation, FunctionGraph
from pypy.objspace.flow.model import last_exception, last_exc_value
from pypy.interpreter.pycode import cpython_code_signature
from pypy.interpreter.argument import ArgErr


class AnnotatorError(Exception):
    pass


class RPythonAnnotator:
    """Block annotator for RPython.
    See description in doc/translation/annotation.txt."""

    def __init__(self, translator=None):
        self.translator = translator
        self.pendingblocks = {}  # map {block: function}
        self.bindings = {}       # map Variables to SomeValues
        self.annotated = {}      # set of blocks already seen
        self.links_followed = {} # set of links that have ever been followed
        self.notify = {}        # {block: {positions-to-reflow-from-when-done}}
        # --- the following information is recorded for debugging only ---
        # --- and only if annotation.model.DEBUG is kept to True
        self.why_not_annotated = {} # {block: (exc_type, exc_value, traceback)}
                                    # records the location of BlockedInference
                                    # exceptions that blocked some blocks.
        self.blocked_functions = {} # set of functions that have blocked blocks
        self.bindingshistory = {}# map Variables to lists of SomeValues
        self.binding_caused_by = {}     # map Variables to position_keys
               # records the caller position that caused bindings of inputargs
               # to be updated
        self.binding_cause_history = {} # map Variables to lists of positions
                # history of binding_caused_by, kept in sync with
                # bindingshistory
        # --- end of debugging information ---
        self.bookkeeper = Bookkeeper(self)

    #___ convenience high-level interface __________________

    def build_types(self, func_or_flowgraph, input_arg_types, func=None):
        """Recursively build annotations about the specific entry point."""
        if isinstance(func_or_flowgraph, FunctionGraph):
            flowgraph = func_or_flowgraph
        else:
            func = func_or_flowgraph
            if self.translator is None:
                from pypy.translator.translator import Translator
                self.translator = Translator(func, simplifying=True)
                self.translator.annotator = self
            flowgraph = self.translator.getflowgraph(func)
        # make input arguments and set their type
        input_arg_types = list(input_arg_types)
        nbarg = len(flowgraph.getargs())
        while len(input_arg_types) < nbarg:
            input_arg_types.append(object)
        inputcells = []
        for t in input_arg_types:
            if not isinstance(t, annmodel.SomeObject):
                t = self.bookkeeper.valueoftype(t)
            inputcells.append(t)
        
        # register the entry point
        self.addpendingblock(func, flowgraph.startblock, inputcells)
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

    def addpendingblock(self, fn, block, cells, called_from=None):
        """Register an entry point into block with the given input cells."""
        assert self.translator is None or fn in self.translator.flowgraphs
        for a in cells:
            assert isinstance(a, annmodel.SomeObject)
        if block not in self.annotated:
            self.bindinputargs(block, cells, called_from)
        else:
            self.mergeinputargs(block, cells, called_from)
        if not self.annotated[block]:
            self.pendingblocks[block] = fn

    def complete(self):
        """Process pending blocks until none is left."""
        while self.pendingblocks:
            block, fn = self.pendingblocks.popitem()
            self.processblock(fn, block)
        if False in self.annotated.values():
            if annmodel.DEBUG:
                for block in self.annotated:
                    if self.annotated[block] is False:
                        fn = self.why_not_annotated[block][1].break_at[0]
                        self.blocked_functions[fn] = True
                        import traceback
                        print '-+' * 30
                        print 'BLOCKED block at:',
                        print self.why_not_annotated[block][1].break_at
                        print 'because of:'
                        traceback.print_exception(*self.why_not_annotated[block])
                        print '-+' * 30
                        print
            print "++-" * 20
            print ('%d blocks are still blocked' %
                                 self.annotated.values().count(False))
            print "continuing anyway ...."
            print "++-" * 20
            

    def binding(self, arg, in_link=None):
        "Gives the SomeValue corresponding to the given Variable or Constant."
        if isinstance(arg, Variable):
            return self.bindings[arg]
        elif isinstance(arg, UndefinedConstant):  # undefined local variables
            return annmodel.SomeImpossibleValue()
        elif isinstance(arg, Constant):
            if arg.value is last_exception or arg.value is last_exc_value:
                assert in_link
                assert isinstance(in_link.exitcase, type(Exception))
                assert issubclass(in_link.exitcase, Exception)
                return annmodel.SomeObject()   # XXX
            return self.bookkeeper.immutablevalue(arg.value)
        else:
            raise TypeError, 'Variable or Constant expected, got %r' % (arg,)

    def setbinding(self, arg, s_value, called_from=None):
        if arg in self.bindings:
            assert s_value.contains(self.bindings[arg])
            # for debugging purposes, record the history of bindings that
            # have been given to this variable
            if annmodel.DEBUG:
                history = self.bindingshistory.setdefault(arg, [])
                history.append(self.bindings[arg])
                cause_history = self.binding_cause_history.setdefault(arg, [])
                cause_history.append(self.binding_caused_by[arg])
        self.bindings[arg] = s_value
        if annmodel.DEBUG:
            self.binding_caused_by[arg] = called_from


    #___ interface for annotator.factory _______

    def recursivecall(self, func, position_key, args):
        parent_fn, parent_block, parent_index = position_key
        graph = self.translator.getflowgraph(func, parent_fn,
                                             position_key)
        # self.notify[graph.returnblock] is a dictionary of call
        # points to this func which triggers a reflow whenever the
        # return block of this graph has been analysed.
        callpositions = self.notify.setdefault(graph.returnblock, {})
        callpositions[position_key] = True

        # parse the arguments according to the function we are calling
        signature = cpython_code_signature(func.func_code)
        defs_s = []
        if func.func_defaults:
            for x in func.func_defaults:
                defs_s.append(self.bookkeeper.immutablevalue(x))
        try:
            inputcells = args.match_signature(signature, defs_s)
        except ArgErr, e:
            print 'IGNORED', e     # hopefully temporary hack
            return SomeImpossibleValue()

        # generalize the function's input arguments
        self.addpendingblock(func, graph.startblock, inputcells, position_key)

        # get the (current) return value
        v = graph.getreturnvar()
        try:
            return self.bindings[v]
        except KeyError: 
            # let's see if the graph only has exception returns 
            if graph.hasonlyexceptionreturns(): 
                # XXX for functions with exceptions what to 
                #     do anyway? 
                return self.bookkeeper.immutablevalue(None)
            return annmodel.SomeImpossibleValue()

    def reflowfromposition(self, position_key):
        fn, block, index = position_key
        self.reflowpendingblock(fn, block)


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
        # Generic simplifications
        from pypy.translator import transform
        transform.transform_graph(self)
        from pypy.translator import simplify 
        for graph in self.translator.flowgraphs.values(): 
            simplify.eliminate_empty_blocks(graph) 


    #___ flowing annotations in blocks _____________________

    def processblock(self, fn, block):
        # Important: this is not called recursively.
        # self.flowin() can only issue calls to self.addpendingblock().
        # The analysis of a block can be in three states:
        #  * block not in self.annotated:
        #      never seen the block.
        #  * self.annotated[block] == False:
        #      the input variables of the block are in self.bindings but we
        #      still have to consider all the operations in the block.
        #  * self.annotated[block] == True or <original function object>:
        #      analysis done (at least until we find we must generalize the
        #      input variables).

        #print '* processblock', block, cells
        self.annotated[block] = fn or True
        try:
            self.flowin(fn, block)
        except BlockedInference, e:
            #print '_'*60
            #print 'Blocked at %r:' % (e.break_at,)
            #import traceback, sys
            #traceback.print_tb(sys.exc_info()[2])
            self.annotated[block] = False   # failed, hopefully temporarily
            if annmodel.DEBUG:
                import sys
                self.why_not_annotated[block] = sys.exc_info()
        except Exception, e:
            # hack for debug tools only
            if not hasattr(e, '__annotator_block'):
                setattr(e, '__annotator_block', block)
            raise

    def reflowpendingblock(self, fn, block):
        self.pendingblocks[block] = fn
        assert block in self.annotated
        self.annotated[block] = False  # must re-flow

    def bindinputargs(self, block, inputcells, called_from=None):
        # Create the initial bindings for the input args of a block.
        assert len(block.inputargs) == len(inputcells)
        for a, cell in zip(block.inputargs, inputcells):
            self.setbinding(a, cell, called_from)
        self.annotated[block] = False  # must flowin.

    def mergeinputargs(self, block, inputcells, called_from=None):
        # Merge the new 'cells' with each of the block's existing input
        # variables.
        oldcells = [self.binding(a) for a in block.inputargs]
        unions = [annmodel.unionof(c1,c2) for c1, c2 in zip(oldcells,inputcells)]
        # if the merged cells changed, we must redo the analysis
        if unions != oldcells:
            self.bindinputargs(block, unions, called_from)

    def flowin(self, fn, block):
        #print 'Flowing', block, [self.binding(a) for a in block.inputargs]
        for i in range(len(block.operations)):
            try:
                self.bookkeeper.enter((fn, block, i))
                self.consider_op(block.operations[i])
            finally:
                self.bookkeeper.leave()
        # dead code removal: don't follow all exits if the exitswitch is known
        exits = block.exits
        if isinstance(block.exitswitch, Variable):
            s_exitswitch = self.bindings[block.exitswitch]
            if s_exitswitch.is_constant():
                exits = [link for link in exits
                              if link.exitcase == s_exitswitch.const]
        knownvar, knownvarvalue = getattr(self.bindings.get(block.exitswitch),
                                          "knowntypedata", (None, None))
        for link in exits:
            self.links_followed[link] = True
            cells = []
            for a in link.args:
                cell = self.binding(a, in_link=link)
                if link.exitcase is True and a is knownvar \
                       and not knownvarvalue.contains(cell):
                    cell = knownvarvalue
                cells.append(cell)
            self.addpendingblock(fn, link.target, cells)
        if block in self.notify:
            # reflow from certain positions when this block is done
            for position_key in self.notify[block]:
                self.reflowfromposition(position_key)


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
        self.setbinding(op.result, resultcell)  # bind resultcell to op.result

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


class CannotSimplify(Exception):
    pass
