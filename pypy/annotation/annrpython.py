from __future__ import generators

from types import FunctionType
from pypy.tool.ansi_print import ansi_log, raise_nicer_exception
from pypy.annotation import model as annmodel
from pypy.tool.pairtype import pair
from pypy.annotation.bookkeeper import Bookkeeper
from pypy.annotation import signature
from pypy.objspace.flow.model import Variable, Constant
from pypy.objspace.flow.model import FunctionGraph
from pypy.objspace.flow.model import c_last_exception, checkgraph
import py
log = py.log.Producer("annrpython") 
py.log.setconsumer("annrpython", ansi_log) 

from pypy.tool.error import format_blocked_annotation_error, format_someobject_error, AnnotatorError

FAIL = object()

class RPythonAnnotator(object):
    """Block annotator for RPython.
    See description in doc/translation.txt."""

    def __init__(self, translator=None, policy=None, bookkeeper=None):
        import pypy.rpython.ootypesystem.ooregistry # has side effects
        import pypy.rpython.ootypesystem.bltregistry # has side effects
        import pypy.rpython.extfuncregistry # has side effects
        import pypy.rlib.nonconst # has side effects

        if translator is None:
            # interface for tests
            from pypy.translator.translator import TranslationContext
            translator = TranslationContext()
            translator.annotator = self
        self.translator = translator
        self.pendingblocks = {}  # map {block: graph-containing-it}
        self.bindings = {}       # map Variables to SomeValues
        self.annotated = {}      # set of blocks already seen
        self.added_blocks = None # see processblock() below
        self.links_followed = {} # set of links that have ever been followed
        self.notify = {}        # {block: {positions-to-reflow-from-when-done}}
        self.fixed_graphs = {}  # set of graphs not to annotate again
        self.blocked_blocks = {} # set of {blocked_block: graph}
        # --- the following information is recorded for debugging only ---
        # --- and only if annotation.model.DEBUG is kept to True
        self.why_not_annotated = {} # {block: (exc_type, exc_value, traceback)}
                                    # records the location of BlockedInference
                                    # exceptions that blocked some blocks.
        self.blocked_graphs = {} # set of graphs that have blocked blocks
        self.bindingshistory = {}# map Variables to lists of SomeValues
        self.binding_caused_by = {}     # map Variables to position_keys
               # records the caller position that caused bindings of inputargs
               # to be updated
        self.binding_cause_history = {} # map Variables to lists of positions
                # history of binding_caused_by, kept in sync with
                # bindingshistory
        self.reflowcounter = {}
        self.return_bindings = {} # map return Variables to their graphs
        # --- end of debugging information ---
        self.frozen = False
        if policy is None:
            from pypy.annotation.policy import AnnotatorPolicy
            self.policy = AnnotatorPolicy()
        else:
            self.policy = policy
        if bookkeeper is None:
            bookkeeper = Bookkeeper(self)
        self.bookkeeper = bookkeeper

    def __getstate__(self):
        attrs = """translator pendingblocks bindings annotated links_followed
        notify bookkeeper frozen policy added_blocks""".split()
        ret = self.__dict__.copy()
        for key, value in ret.items():
            if key not in attrs:
                assert type(value) is dict, (
                    "%r is not dict. please update %s.__getstate__" %
                    (key, self.__class__.__name__))
                ret[key] = {}
        return ret

    def _register_returnvar(self, flowgraph):
        if annmodel.DEBUG:
            self.return_bindings[flowgraph.getreturnvar()] = flowgraph

    #___ convenience high-level interface __________________

    def build_types(self, function, input_arg_types, complete_now=True):
        """Recursively build annotations about the specific entry point."""
        assert isinstance(function, FunctionType), "fix that!"

        # make input arguments and set their type
        inputcells = [self.typeannotation(t) for t in input_arg_types]

        desc = self.bookkeeper.getdesc(function)
        desc.getcallfamily()   # record this implicit call (hint for back-ends)
        flowgraph = desc.specialize(inputcells)
        if not isinstance(flowgraph, FunctionGraph):
            assert isinstance(flowgraph, annmodel.SomeObject)
            return flowgraph

        return self.build_graph_types(flowgraph, inputcells, complete_now=complete_now)

    def get_call_parameters(self, function, args_s, policy):
        desc = self.bookkeeper.getdesc(function)
        args = self.bookkeeper.build_args("simple_call", args_s[:])
        result = []
        def schedule(graph, inputcells):
            result.append((graph, inputcells))
            return annmodel.s_ImpossibleValue

        prevpolicy = self.policy
        self.policy = policy
        self.bookkeeper.enter(None)
        try:
            desc.pycall(schedule, args, annmodel.s_ImpossibleValue)
        finally:
            self.bookkeeper.leave()
            self.policy = prevpolicy
        [(graph, inputcells)] = result
        return graph, inputcells

    def annotate_helper(self, function, args_s, policy=None):
        if policy is None:
            from pypy.annotation.policy import AnnotatorPolicy
            policy = AnnotatorPolicy()
        graph, inputcells = self.get_call_parameters(function, args_s, policy)
        self.build_graph_types(graph, inputcells, complete_now=False)
        self.complete_helpers(policy)
        return graph
    
    def annotate_helper_method(self, _class, attr, args_s, policy=None):
        """ Warning! this method is meant to be used between
        annotation and rtyping
        """
        if policy is None:
            from pypy.annotation.policy import AnnotatorPolicy
            policy = AnnotatorPolicy()
        
        assert attr != '__class__'
        classdef = self.bookkeeper.getuniqueclassdef(_class)
        attrdef = classdef.find_attribute(attr)
        s_result = attrdef.getvalue()
        classdef.add_source_for_attribute(attr, classdef.classdesc)
        self.bookkeeper
        assert isinstance(s_result, annmodel.SomePBC)
        olddesc = s_result.descriptions.iterkeys().next()
        desc = olddesc.bind_self(classdef)
        args = self.bookkeeper.build_args("simple_call", args_s[:])
        desc.consider_call_site(self.bookkeeper, desc.getcallfamily(), [desc],
            args, annmodel.s_ImpossibleValue)
        result = []
        def schedule(graph, inputcells):
            result.append((graph, inputcells))
            return annmodel.s_ImpossibleValue

        prevpolicy = self.policy
        self.policy = policy
        self.bookkeeper.enter(None)
        try:
            desc.pycall(schedule, args, annmodel.s_ImpossibleValue)
        finally:
            self.bookkeeper.leave()
            self.policy = prevpolicy
        [(graph, inputcells)] = result
        self.build_graph_types(graph, inputcells, complete_now=False)
        self.complete_helpers(policy)
        return graph

    def complete_helpers(self, policy):
        saved = self.policy, self.added_blocks
        self.policy = policy
        try:
            self.added_blocks = {}
            self.complete()
            # invoke annotation simplifications for the new blocks
            self.simplify(block_subset=self.added_blocks)
        finally:
            self.policy, self.added_blocks = saved

    def build_graph_types(self, flowgraph, inputcells, complete_now=True):
        checkgraph(flowgraph)

        nbarg = len(flowgraph.getargs())
        if len(inputcells) != nbarg: 
            raise TypeError("%s expects %d args, got %d" %(       
                            flowgraph, nbarg, len(inputcells)))
        
        # register the entry point
        self.addpendinggraph(flowgraph, inputcells)
        # recursively proceed until no more pending block is left
        if complete_now:
            self.complete()
        return self.binding(flowgraph.getreturnvar(), None)

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

    def getuserclassdefinitions(self):
        """Return a list of ClassDefs."""
        return self.bookkeeper.classdefs

    #___ medium-level interface ____________________________

    def addpendinggraph(self, flowgraph, inputcells):
        self._register_returnvar(flowgraph)
        self.addpendingblock(flowgraph, flowgraph.startblock, inputcells)

    def addpendingblock(self, graph, block, cells, called_from_graph=None):
        """Register an entry point into block with the given input cells."""
        if graph in self.fixed_graphs:
            # special case for annotating/rtyping in several phases: calling
            # a graph that has already been rtyped.  Safety-check the new
            # annotations that are passed in, and don't annotate the old
            # graph -- it's already low-level operations!
            for a, s_newarg in zip(graph.getargs(), cells):
                s_oldarg = self.binding(a)
                assert s_oldarg.contains(s_newarg)
        else:
            assert not self.frozen
            for a in cells:
                assert isinstance(a, annmodel.SomeObject)
            if block not in self.annotated:
                self.bindinputargs(graph, block, cells, called_from_graph)
            else:
                self.mergeinputargs(graph, block, cells, called_from_graph)
            if not self.annotated[block]:
                self.pendingblocks[block] = graph

    def complete(self):
        """Process pending blocks until none is left."""
        while True:
            while self.pendingblocks:
                block, graph = self.pendingblocks.popitem()
                if annmodel.DEBUG:
                    self.flowin_block = block # we need to keep track of block
                self.processblock(graph, block)
            self.policy.no_more_blocks_to_annotate(self)
            if not self.pendingblocks:
                break   # finished
        # make sure that the return variables of all graphs is annotated
        if self.added_blocks is not None:
            newgraphs = [self.annotated[block] for block in self.added_blocks]
            newgraphs = dict.fromkeys(newgraphs)
            got_blocked_blocks = False in newgraphs
        else:
            newgraphs = self.translator.graphs  #all of them
            got_blocked_blocks = False in self.annotated.values()
        if got_blocked_blocks:
            for graph in self.blocked_graphs.values():
                self.blocked_graphs[graph] = True

            blocked_blocks = [block for block, done in self.annotated.items()
                                    if done is False]
            assert len(blocked_blocks) == len(self.blocked_blocks)

            text = format_blocked_annotation_error(self, self.blocked_blocks)
            #raise SystemExit()
            raise AnnotatorError(text)
        for graph in newgraphs:
            v = graph.getreturnvar()
            if v not in self.bindings:
                self.setbinding(v, annmodel.s_ImpossibleValue)
        # policy-dependent computation
        self.bookkeeper.compute_at_fixpoint()

    def binding(self, arg, default=FAIL):
        "Gives the SomeValue corresponding to the given Variable or Constant."
        if isinstance(arg, Variable):
            try:
                return self.bindings[arg]
            except KeyError:
                if default is not FAIL:
                    return default
                else:
                    raise
        elif isinstance(arg, Constant):
            #if arg.value is undefined_value:   # undefined local variables
            #    return annmodel.s_ImpossibleValue
            return self.bookkeeper.immutableconstant(arg)
        else:
            raise TypeError, 'Variable or Constant expected, got %r' % (arg,)

    def typeannotation(self, t):
        return signature.annotation(t, self.bookkeeper)

    def ondegenerated(self, what, s_value, where=None, called_from_graph=None):
        if self.policy.allow_someobjects:
            return
        # is the function itself tagged with allow_someobjects?
        position_key = where or getattr(self.bookkeeper, 'position_key', None)
        if position_key is not None:
            graph, block, i = position_key
            try:
                if graph.func.allow_someobjects:
                    return
            except AttributeError:
                pass

        graph = position_key[0]
        msgstr = format_someobject_error(self, position_key, what, s_value,
                                         called_from_graph,
                                         self.bindings.get(what, "(none)"))

        raise AnnotatorError(msgstr)

    def setbinding(self, arg, s_value, called_from_graph=None, where=None):
        if arg in self.bindings:
            assert s_value.contains(self.bindings[arg])
            # for debugging purposes, record the history of bindings that
            # have been given to this variable
            if annmodel.DEBUG:
                history = self.bindingshistory.setdefault(arg, [])
                history.append(self.bindings[arg])
                cause_history = self.binding_cause_history.setdefault(arg, [])
                cause_history.append(self.binding_caused_by[arg])

        degenerated = annmodel.isdegenerated(s_value)

        if degenerated:
            self.ondegenerated(arg, s_value, where=where,
                               called_from_graph=called_from_graph)

        self.bindings[arg] = s_value
        if annmodel.DEBUG:
            if arg in self.return_bindings:
                log.event("%s -> %s" % 
                    (self.whereami((self.return_bindings[arg], None, None)), 
                     s_value)) 

            if arg in self.return_bindings and degenerated:
                self.warning("result degenerated to SomeObject",
                             (self.return_bindings[arg],None, None))
                
            self.binding_caused_by[arg] = called_from_graph

    def transfer_binding(self, v_target, v_source):
        assert v_source in self.bindings
        self.bindings[v_target] = self.bindings[v_source]
        if annmodel.DEBUG:
            self.binding_caused_by[v_target] = None

    def warning(self, msg, pos=None):
        if pos is None:
            try:
                pos = self.bookkeeper.position_key
            except AttributeError:
                pos = '?'
        if pos != '?':
            pos = self.whereami(pos)
 
        log.WARNING("%s/ %s" % (pos, msg))


    #___ interface for annotator.bookkeeper _______

    def recursivecall(self, graph, whence, inputcells): # whence = position_key|callback taking the annotator, graph 
        if isinstance(whence, tuple):
            parent_graph, parent_block, parent_index = position_key = whence
            tag = parent_block, parent_index
            self.translator.update_call_graph(parent_graph, graph, tag)
        else:
            position_key = None
        self._register_returnvar(graph)
        # self.notify[graph.returnblock] is a dictionary of call
        # points to this func which triggers a reflow whenever the
        # return block of this graph has been analysed.
        callpositions = self.notify.setdefault(graph.returnblock, {})
        if whence is not None:
            if callable(whence):
                def callback():
                    whence(self, graph)
            else:
                callback = whence
            callpositions[callback] = True

        # generalize the function's input arguments
        self.addpendingblock(graph, graph.startblock, inputcells,
                             position_key)

        # get the (current) return value
        v = graph.getreturnvar()
        try:
            return self.bindings[v]
        except KeyError: 
            # the function didn't reach any return statement so far.
            # (some functions actually never do, they always raise exceptions)
            return annmodel.s_ImpossibleValue

    def reflowfromposition(self, position_key):
        graph, block, index = position_key
        self.reflowpendingblock(graph, block)


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

    def simplify(self, block_subset=None, extra_passes=None):
        # Generic simplifications
        from pypy.translator import transform
        transform.transform_graph(self, block_subset=block_subset,
                                  extra_passes=extra_passes)
        from pypy.translator import simplify 
        if block_subset is None:
            graphs = self.translator.graphs
        else:
            graphs = {}
            for block in block_subset:
                graph = self.annotated.get(block)
                if graph:
                    graphs[graph] = True
        for graph in graphs:
            simplify.eliminate_empty_blocks(graph)


    #___ flowing annotations in blocks _____________________

    def processblock(self, graph, block):
        # Important: this is not called recursively.
        # self.flowin() can only issue calls to self.addpendingblock().
        # The analysis of a block can be in three states:
        #  * block not in self.annotated:
        #      never seen the block.
        #  * self.annotated[block] == False:
        #      the input variables of the block are in self.bindings but we
        #      still have to consider all the operations in the block.
        #  * self.annotated[block] == graph-containing-block:
        #      analysis done (at least until we find we must generalize the
        #      input variables).

        #print '* processblock', block, cells
        if annmodel.DEBUG:
            self.reflowcounter.setdefault(block, 0)
            self.reflowcounter[block] += 1
        self.annotated[block] = graph
        if block in self.blocked_blocks:
            del self.blocked_blocks[block]
        try:
            self.flowin(graph, block)
        except BlockedInference, e:
            self.annotated[block] = False   # failed, hopefully temporarily
            self.blocked_blocks[block] = graph
        except Exception, e:
            # hack for debug tools only
            if not hasattr(e, '__annotator_block'):
                setattr(e, '__annotator_block', block)
            raise

        # The dict 'added_blocks' is used by rpython.annlowlevel to
        # detect which are the new blocks that annotating an additional
        # small helper creates.
        if self.added_blocks is not None:
            self.added_blocks[block] = True

    def reflowpendingblock(self, graph, block):
        assert not self.frozen
        assert graph not in self.fixed_graphs
        self.pendingblocks[block] = graph
        assert block in self.annotated
        self.annotated[block] = False  # must re-flow
        self.blocked_blocks[block] = graph

    def bindinputargs(self, graph, block, inputcells, called_from_graph=None):
        # Create the initial bindings for the input args of a block.
        assert len(block.inputargs) == len(inputcells)
        where = (graph, block, None)
        for a, cell in zip(block.inputargs, inputcells):
            self.setbinding(a, cell, called_from_graph, where=where)
        self.annotated[block] = False  # must flowin.
        self.blocked_blocks[block] = graph

    def mergeinputargs(self, graph, block, inputcells, called_from_graph=None):
        # Merge the new 'cells' with each of the block's existing input
        # variables.
        oldcells = [self.binding(a) for a in block.inputargs]
        unions = [annmodel.unionof(c1,c2) for c1, c2 in zip(oldcells,inputcells)]
        # if the merged cells changed, we must redo the analysis
        if unions != oldcells:
            self.bindinputargs(graph, block, unions, called_from_graph)

    def whereami(self, position_key):
        graph, block, i = position_key
        blk = ""
        if block:
            at = block.at()
            if at:
                blk = " block"+at
        opid=""
        if i is not None:
            opid = " op=%d" % i
        return repr(graph) + blk + opid

    def flowin(self, graph, block):
        #print 'Flowing', block, [self.binding(a) for a in block.inputargs]
        try:
            for i in range(len(block.operations)):
                try:
                    self.bookkeeper.enter((graph, block, i))
                    self.consider_op(block.operations[i])
                finally:
                    self.bookkeeper.leave()

        except BlockedInference, e:
            if annmodel.DEBUG:
                import sys
                self.why_not_annotated[block] = sys.exc_info()

            if (e.op is block.operations[-1] and
                block.exitswitch == c_last_exception):
                # this is the case where the last operation of the block will
                # always raise an exception which is immediately caught by
                # an exception handler.  We then only follow the exceptional
                # branches.
                exits = [link for link in block.exits
                              if link.exitcase is not None]

            elif e.op.opname in ('simple_call', 'call_args', 'next'):
                # XXX warning, keep the name of the call operations in sync
                # with the flow object space.  These are the operations for
                # which it is fine to always raise an exception.  We then
                # swallow the BlockedInference and that's it.
                # About 'next': see test_annotate_iter_empty_container().
                return

            else:
                # other cases are problematic (but will hopefully be solved
                # later by reflowing).  Throw the BlockedInference up to
                # processblock().
                raise

        except annmodel.HarmlesslyBlocked:
            return

        else:
            # dead code removal: don't follow all exits if the exitswitch
            # is known
            exits = block.exits
            if isinstance(block.exitswitch, Variable):
                s_exitswitch = self.bindings[block.exitswitch]
                if s_exitswitch.is_constant():
                    exits = [link for link in exits
                                  if link.exitcase == s_exitswitch.const]

        # mapping (exitcase, variable) -> s_annotation
        # that can be attached to booleans, exitswitches
        knowntypedata = getattr(self.bindings.get(block.exitswitch),
                                "knowntypedata", {})

        # filter out those exceptions which cannot
        # occour for this specific, typed operation.
        if block.exitswitch == c_last_exception:
            op = block.operations[-1]
            if op.opname in annmodel.BINARY_OPERATIONS:
                arg1 = self.binding(op.args[0])
                arg2 = self.binding(op.args[1])
                binop = getattr(pair(arg1, arg2), op.opname, None)
                can_only_throw = annmodel.read_can_only_throw(binop, arg1, arg2)
            elif op.opname in annmodel.UNARY_OPERATIONS:
                arg1 = self.binding(op.args[0])
                unop = getattr(arg1, op.opname, None)
                can_only_throw = annmodel.read_can_only_throw(unop, arg1)
            else:
                can_only_throw = None

            if can_only_throw is not None:
                candidates = can_only_throw
                candidate_exits = exits
                exits = []
                for link in candidate_exits:
                    case = link.exitcase
                    if case is None:
                        exits.append(link)
                        continue
                    covered = [c for c in candidates if issubclass(c, case)]
                    if covered:
                        exits.append(link)
                        candidates = [c for c in candidates if c not in covered]

        for link in exits:
            import types
            in_except_block = False

            last_exception_var = link.last_exception # may be None for non-exception link
            last_exc_value_var = link.last_exc_value # may be None for non-exception link
            
            if isinstance(link.exitcase, (types.ClassType, type)) \
                   and issubclass(link.exitcase, py.builtin.BaseException):
                assert last_exception_var and last_exc_value_var
                last_exc_value_object = self.bookkeeper.valueoftype(link.exitcase)
                last_exception_object = annmodel.SomeObject()
                last_exception_object.knowntype = type
                if isinstance(last_exception_var, Constant):
                    last_exception_object.const = last_exception_var.value
                last_exception_object.is_type_of = [last_exc_value_var]

                if isinstance(last_exception_var, Variable):
                    self.setbinding(last_exception_var, last_exception_object)
                if isinstance(last_exc_value_var, Variable):
                    self.setbinding(last_exc_value_var, last_exc_value_object)

                last_exception_object = annmodel.SomeObject()
                last_exception_object.knowntype = type
                if isinstance(last_exception_var, Constant):
                    last_exception_object.const = last_exception_var.value
                #if link.exitcase is Exception:
                #    last_exc_value_object = annmodel.SomeObject()
                #else:
                last_exc_value_vars = []
                in_except_block = True

            ignore_link = False
            cells = []
            renaming = {}
            for a,v in zip(link.args,link.target.inputargs):
                renaming.setdefault(a, []).append(v)
            for a,v in zip(link.args,link.target.inputargs):
                if a == last_exception_var:
                    assert in_except_block
                    cells.append(last_exception_object)
                elif a == last_exc_value_var:
                    assert in_except_block
                    cells.append(last_exc_value_object)
                    last_exc_value_vars.append(v)
                else:
                    cell = self.binding(a)
                    if (link.exitcase, a) in knowntypedata:
                        knownvarvalue = knowntypedata[(link.exitcase, a)]
                        cell = pair(cell, knownvarvalue).improve()
                        # ignore links that try to pass impossible values
                        if cell == annmodel.s_ImpossibleValue:
                            ignore_link = True

                    if hasattr(cell,'is_type_of'):
                        renamed_is_type_of = []
                        for v in cell.is_type_of:
                            new_vs = renaming.get(v,[])
                            renamed_is_type_of += new_vs
                        newcell = annmodel.SomeObject()
                        if cell.knowntype == type:
                            newcell.knowntype = type
                        if cell.is_constant():
                            newcell.const = cell.const
                        cell = newcell
                        cell.is_type_of = renamed_is_type_of

                    if hasattr(cell, 'knowntypedata'):
                        renamed_knowntypedata = {}
                        for (value, v), s in cell.knowntypedata.items():
                            new_vs = renaming.get(v, [])
                            for new_v in new_vs:
                                renamed_knowntypedata[value, new_v] = s
                        assert isinstance(cell, annmodel.SomeBool)
                        newcell = annmodel.SomeBool()
                        if cell.is_constant():
                            newcell.const = cell.const
                        cell = newcell
                        cell.knowntypedata = renamed_knowntypedata

                    cells.append(cell)

            if ignore_link:
                continue

            if in_except_block:
                last_exception_object.is_type_of = last_exc_value_vars

            self.links_followed[link] = True
            self.addpendingblock(graph, link.target, cells)

        if block in self.notify:
            # reflow from certain positions when this block is done
            for callback in self.notify[block]:
                if isinstance(callback, tuple):
                    self.reflowfromposition(callback) # callback is a position
                else:
                    callback()


    #___ creating the annotations based on operations ______

    def consider_op(self, op):
        argcells = [self.binding(a) for a in op.args]
        consider_meth = getattr(self,'consider_op_'+op.opname,
                                None)
        if not consider_meth:
            raise Exception,"unknown op: %r" % op

        # let's be careful about avoiding propagated SomeImpossibleValues
        # to enter an op; the latter can result in violations of the
        # more general results invariant: e.g. if SomeImpossibleValue enters is_
        #  is_(SomeImpossibleValue, None) -> SomeBool
        #  is_(SomeInstance(not None), None) -> SomeBool(const=False) ...
        # boom -- in the assert of setbinding()
        for arg in argcells:
            if isinstance(arg, annmodel.SomeImpossibleValue):
                raise BlockedInference(self, op)
        try:
            resultcell = consider_meth(*argcells)
        except Exception:
            graph = self.bookkeeper.position_key[0]
            raise_nicer_exception(op, str(graph))
        if resultcell is None:
            resultcell = self.noreturnvalue(op)
        elif resultcell == annmodel.s_ImpossibleValue:
            raise BlockedInference(self, op) # the operation cannot succeed
        assert isinstance(resultcell, annmodel.SomeObject)
        assert isinstance(op.result, Variable)
        self.setbinding(op.result, resultcell)  # bind resultcell to op.result

    def noreturnvalue(self, op):
        return annmodel.s_ImpossibleValue  # no return value (hook method)

    # XXX "contains" clash with SomeObject method
    def consider_op_contains(self, seq, elem):
        self.bookkeeper.count("contains", seq)
        return seq.op_contains(elem)

    def consider_op_newtuple(self, *args):
        return annmodel.SomeTuple(items = args)

    def consider_op_newlist(self, *args):
        return self.bookkeeper.newlist(*args)

    def consider_op_newdict(self):
        return self.bookkeeper.newdict()

    def consider_op_newslice(self, start, stop, step):
        self.bookkeeper.count('newslice', start, stop, step)
        return annmodel.SomeSlice(start, stop, step)


    def _registeroperations(cls, model):
        # All unary operations
        d = {}
        for opname in model.UNARY_OPERATIONS:
            fnname = 'consider_op_' + opname
            exec """
def consider_op_%s(self, arg, *args):
    return arg.%s(*args)
""" % (opname, opname) in globals(), d
            setattr(cls, fnname, d[fnname])
        # All binary operations
        for opname in model.BINARY_OPERATIONS:
            fnname = 'consider_op_' + opname
            exec """
def consider_op_%s(self, arg1, arg2, *args):
    return pair(arg1,arg2).%s(*args)
""" % (opname, opname) in globals(), d
            setattr(cls, fnname, d[fnname])
    _registeroperations = classmethod(_registeroperations)

# register simple operations handling
RPythonAnnotator._registeroperations(annmodel)


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
