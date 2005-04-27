from __future__ import generators

from types import FunctionType, ClassType
from pypy.tool.ansi_print import ansi_print
from pypy.annotation import model as annmodel
from pypy.annotation.model import pair
from pypy.annotation.bookkeeper import Bookkeeper
from pypy.objspace.flow.model import Variable, Constant, undefined_value
from pypy.objspace.flow.model import SpaceOperation, FunctionGraph
from pypy.objspace.flow.model import last_exception, last_exc_value

class AnnotatorError(Exception):
    pass


class RPythonAnnotator:
    """Block annotator for RPython.
    See description in doc/translation/annotation.txt."""

    def __init__(self, translator=None, overrides={}):
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
        self.return_bindings = {} # map return Variables to functions
        # user-supplied annotation logic for functions we don't want to flow into
        self.overrides = overrides
        # --- end of debugging information ---
        self.bookkeeper = Bookkeeper(self)


    def _register_returnvar(self, flowgraph, func):
        if annmodel.DEBUG:
            self.return_bindings[flowgraph.getreturnvar()] = func

    #___ convenience high-level interface __________________

    def getflowgraph(self, func, called_by=None, call_tag=None):        
        flowgraph = self.translator.getflowgraph(func, called_by=called_by, call_tag=call_tag)
        self._register_returnvar(flowgraph, func)
        return flowgraph
        

    def build_types(self, func_or_flowgraph, input_arg_types, func=None):
        """Recursively build annotations about the specific entry point."""
        if isinstance(func_or_flowgraph, FunctionGraph):
            flowgraph = func_or_flowgraph
            self._register_returnvar(flowgraph, func)
        else:
            func = func_or_flowgraph
            if self.translator is None:
                from pypy.translator.translator import Translator
                self.translator = Translator(func, simplifying=True)
                self.translator.annotator = self
            flowgraph = self.getflowgraph(func)
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
        return self.binding(flowgraph.getreturnvar(), extquery=True)

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

    def getpbcaccesssets(self):
        """Return mapping const obj -> PBCAccessSet"""
        return self.bookkeeper.pbc_maximal_access_sets

    #___ medium-level interface ____________________________

    def addpendingblock(self, fn, block, cells, called_from=None):
        """Register an entry point into block with the given input cells."""
        assert self.translator is None or fn in self.translator.flowgraphs
        for a in cells:
            assert isinstance(a, annmodel.SomeObject)
        if block not in self.annotated:
            self.bindinputargs(fn, block, cells, called_from)
        else:
            self.mergeinputargs(fn, block, cells, called_from)
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
                        print self.whereami(self.why_not_annotated[block][1].break_at)
                        print 'because of:'
                        traceback.print_exception(*self.why_not_annotated[block])
                        print '-+' * 30
                        print
            print "++-" * 20
            print ('%d blocks are still blocked' %
                                 self.annotated.values().count(False))
            print "continuing anyway ...."
            print "++-" * 20
            

    def binding(self, arg, extquery=False):
        "Gives the SomeValue corresponding to the given Variable or Constant."
        if isinstance(arg, Variable):
            try:
                return self.bindings[arg]
            except KeyError:
                if extquery:
                    return None
                else:
                    raise
        elif isinstance(arg, Constant):
            if arg.value is undefined_value:   # undefined local variables
                return annmodel.SomeImpossibleValue()
            assert not arg.value is last_exception and not arg.value is last_exc_value
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
            if arg in self.return_bindings:
                ansi_print("%s -> %s" % (self.whereami((self.return_bindings[arg],
                                                         None, None)),
                                         s_value),
                           esc="1") # bold

            if arg in self.return_bindings and s_value == annmodel.SomeObject():
                ansi_print("*** WARNING: %s result degenerated to SomeObject" %
                           self.whereami((self.return_bindings[arg],None, None)),
                           esc="31") # RED
                
            self.binding_caused_by[arg] = called_from


    #___ interface for annotator.bookkeeper _______

    def recursivecall(self, func, position_key, inputcells):
        override = self.overrides.get(func, None)
        if override is not None:
            return override(*inputcells)
        parent_fn, parent_block, parent_index = position_key
        graph = self.getflowgraph(func, parent_fn, position_key)
        # self.notify[graph.returnblock] is a dictionary of call
        # points to this func which triggers a reflow whenever the
        # return block of this graph has been analysed.
        callpositions = self.notify.setdefault(graph.returnblock, {})
        callpositions[position_key] = True

        # generalize the function's input arguments
        self.addpendingblock(func, graph.startblock, inputcells, position_key)

        # get the (current) return value
        v = graph.getreturnvar()
        try:
            return self.bindings[v]
        except KeyError: 
            # the function didn't reach any return statement so far.
            # (some functions actually never do, they always raise exceptions)
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

    def specialize(self, specializer=None):
        if specializer is None:
            from pypy.translator.genc import ctyper
            specializer = ctyper.GenCSpecializer
        specializer(self).specialize()


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
        except Exception, e:
            # hack for debug tools only
            if not hasattr(e, '__annotator_block'):
                setattr(e, '__annotator_block', block)
            raise

    def reflowpendingblock(self, fn, block):
        self.pendingblocks[block] = fn
        assert block in self.annotated
        self.annotated[block] = False  # must re-flow

    def bindinputargs(self, fn, block, inputcells, called_from=None):
        # Create the initial bindings for the input args of a block.
        assert len(block.inputargs) == len(inputcells)
        for a, cell in zip(block.inputargs, inputcells):
            self.setbinding(a, cell, called_from)
        self.annotated[block] = False  # must flowin.

    def mergeinputargs(self, fn, block, inputcells, called_from=None):
        # Merge the new 'cells' with each of the block's existing input
        # variables.
        oldcells = [self.binding(a) for a in block.inputargs]
        unions = [annmodel.tracking_unionof((fn, block), c1,c2) for c1, c2 in zip(oldcells,inputcells)]
        # if the merged cells changed, we must redo the analysis
        if unions != oldcells:
            self.bindinputargs(fn, block, unions, called_from)

    def whereami(self, position_key):
        fn, block, i = position_key
        mod = getattr(fn, '__module__', None)
        if mod is None:
            mod = '?'
        name = getattr(fn, '__name__', None)
        if name is not None:
            firstlineno = fn.func_code.co_firstlineno
        else:
            name = 'UNKNOWN'
            firstlineno = -1
        blk = ""
        if block:
            at = block.at()
            if at:
                blk = " block"+at
        opid=""
        if i is not None:
            opid = " op=%d" % i
        return "(%s:%d) %s%s%s" % (mod, firstlineno, name, blk, opid)

    def flowin(self, fn, block):
        #print 'Flowing', block, [self.binding(a) for a in block.inputargs]
        try:
            for i in range(len(block.operations)):
                try:
                    self.bookkeeper.enter((fn, block, i))
                    self.consider_op(block.operations[i])
                finally:
                    self.bookkeeper.leave()

        except BlockedInference, e:
            if annmodel.DEBUG:
                import sys
                self.why_not_annotated[block] = sys.exc_info()

            if (e.op is block.operations[-1] and
                block.exitswitch == Constant(last_exception)):
                # this is the case where the last operation of the block will
                # always raise an exception which is immediately caught by
                # an exception handler.  We then only follow the exceptional
                # branches.
                exits = [link for link in block.exits
                              if link.exitcase is not None]

            elif e.op.opname in ('simple_call', 'call_args'):
                # XXX warning, keep the name of the call operations in sync
                # with the flow object space.  These are the operations for
                # which it is fine to always raise an exception.  We then
                # swallow the BlockedInference and that's it.
                return

            else:
                # other cases are problematic (but will hopefully be solved
                # later by reflowing).  Throw the BlockedInference up to
                # processblock().
                raise
        else:
            # dead code removal: don't follow all exits if the exitswitch
            # is known
            exits = block.exits
            if isinstance(block.exitswitch, Variable):
                s_exitswitch = self.bindings[block.exitswitch]
                if s_exitswitch.is_constant():
                    exits = [link for link in exits
                                  if link.exitcase == s_exitswitch.const]
        knownvars, knownvarvalue = getattr(self.bindings.get(block.exitswitch),
                                          "knowntypedata", (None, None))
        
        if block.exitswitch == Constant(last_exception):
            op = block.operations[-1]
            if op.opname in annmodel.BINARY_OPERATIONS:
                arg1 = self.binding(op.args[0])
                arg2 = self.binding(op.args[1])
                binop = getattr(pair(arg1, arg2), op.opname, None)
                can_only_throw = getattr(binop, "can_only_throw", None)
            elif op.opname in annmodel.UNARY_OPERATIONS:
                arg1 = self.binding(op.args[0])
                unop = getattr(arg1, op.opname, None)
                can_only_throw = getattr(unop, "can_only_throw", None)
            else:
                can_only_throw = None
            if can_only_throw is not None:
                exits = [link
                         for link in exits
                         if link.exitcase is None
                         or link.exitcase in can_only_throw ]
                print can_only_throw
                print exits
                print len(exits)
                for link in exits:
                    print link, link.exitcase
                print 100*"*"

        for link in exits:
            self.links_followed[link] = True
            import types
            in_except_block = False
            if isinstance(link.exitcase, (types.ClassType, type)) \
                   and issubclass(link.exitcase, Exception):
                last_exception_object = annmodel.SomeObject()
                if link.exitcase is Exception:
                    last_exc_value_object = annmodel.SomeObject()
                else:
                    last_exc_value_object = self.bookkeeper.valueoftype(link.exitcase)
                last_exc_value_vars = []
                in_except_block = True

            cells = []
            renaming = {}
            for a,v in zip(link.args,link.target.inputargs):
                renaming.setdefault(a, []).append(v)
            for a,v in zip(link.args,link.target.inputargs):
                if a == Constant(last_exception):
                    assert in_except_block
                    cells.append(last_exception_object)
                elif a == Constant(last_exc_value):
                    assert in_except_block
                    cells.append(last_exc_value_object)
                    last_exc_value_vars.append(v)
                else:
                    cell = self.binding(a)
                    if link.exitcase is True and knownvars is not None and a in knownvars \
                            and not knownvarvalue.contains(cell):
                        cell = knownvarvalue
                    if hasattr(cell,'is_type_of'):
                        renamed_is_type_of = []
                        for v in cell.is_type_of:
                            new_vs = renaming.get(v,[])
                            renamed_is_type_of += new_vs
                        cell = annmodel.SomeObject()
                        cell.is_type_of = renamed_is_type_of
                    cells.append(cell)

            if in_except_block:
                last_exception_object.is_type_of = last_exc_value_vars

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
        # let's be careful about avoiding propagated SomeImpossibleValues
        # to enter an op; the latter can result in violations of the
        # more general results invariant: e.g. if SomeImpossibleValue enters is_
        #  is_(SomeImpossibleValue, None) -> SomeBool
        #  is_(SomeInstance(not None), None) -> SomeBool(const=False) ...
        # boom -- in the assert of setbinding()
        for arg in argcells:
            if isinstance(arg, annmodel.SomeImpossibleValue):
                raise BlockedInference(self, op)
        resultcell = consider_meth(*argcells)
        if resultcell is None:
            resultcell = annmodel.SomeImpossibleValue()  # no return value
        elif resultcell == annmodel.SomeImpossibleValue():
            raise BlockedInference(self, op) # the operation cannot succeed
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

    # XXX "contains" clash with SomeObject method
    def consider_op_contains(self, seq, elem):
        return annmodel.SomeBool()

    def consider_op_newtuple(self, *args):
        return annmodel.SomeTuple(items = args)

    def consider_op_newlist(self, *args):
        return self.bookkeeper.newlist(*args)

    def consider_op_newdict(self, *args):
        assert len(args) % 2 == 0
        items_s = []
        for i in range(0, len(args), 2):
            items_s.append((args[i], args[i+1]))
        return self.bookkeeper.newdict(*items_s)

    def consider_op_newslice(self, start, stop, step):
        return annmodel.SomeSlice(start, stop, step)


class CannotSimplify(Exception):
    pass


class BlockedInference(Exception):
    """This exception signals the type inference engine that the situation
    is currently blocked, and that it should try to progress elsewhere."""

    def __init__(self, annotator, op):
        self.annotator = annotator
        try:
            self.break_at = annotator.bookkeeper.position_key
        except AttributeError:
            self.break_at = None
        self.op = op

    def __repr__(self):
        if not self.break_at:
            break_at = "?"
        else:
            break_at = self.annotator.whereami(self.break_at)
        return "<BlockedInference break_at %s [%s]>" %(break_at, self.op)

    __str__ = __repr__
