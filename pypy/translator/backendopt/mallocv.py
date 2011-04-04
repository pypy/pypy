from pypy.objspace.flow.model import Variable, Constant, Block, Link
from pypy.objspace.flow.model import SpaceOperation, FunctionGraph, copygraph
from pypy.objspace.flow.model import checkgraph
from pypy.objspace.flow.model import c_last_exception
from pypy.translator.backendopt.support import log
from pypy.translator.simplify import join_blocks
from pypy.translator.unsimplify import varoftype
from pypy.rpython.typesystem import getfunctionptr
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.lltypesystem.lloperation import llop


def virtualize_mallocs(translator, graphs, verbose=False):
    newgraphs = graphs[:]
    mallocv = MallocVirtualizer(newgraphs, translator.rtyper, verbose)
    while mallocv.remove_mallocs_once():
        pass
    for graph in newgraphs:
        checkgraph(graph)
        join_blocks(graph)
    assert newgraphs[:len(graphs)] == graphs
    del newgraphs[:len(graphs)]
    translator.graphs.extend(newgraphs)

# ____________________________________________________________


class MallocTypeDesc(object):

    def __init__(self, MALLOCTYPE):
        if not isinstance(MALLOCTYPE, lltype.GcStruct):
            raise CannotRemoveThisType
        self.MALLOCTYPE = MALLOCTYPE
        self.check_no_destructor()
        self.names_and_types = []
        self.name2index = {}
        self.name2subtype = {}
        self.initialize_type(MALLOCTYPE)
        #self.immutable_struct = MALLOCTYPE._hints.get('immutable')

    def check_no_destructor(self):
        STRUCT = self.MALLOCTYPE
        try:
            rttiptr = lltype.getRuntimeTypeInfo(STRUCT)
        except ValueError:
            return    # ok
        destr_ptr = getattr(rttiptr._obj, 'destructor_funcptr', None)
        if destr_ptr:
            raise CannotRemoveThisType

    def initialize_type(self, TYPE):
        fieldnames = TYPE._names
        firstname, FIRSTTYPE = TYPE._first_struct()
        if FIRSTTYPE is not None:
            self.initialize_type(FIRSTTYPE)
            fieldnames = fieldnames[1:]
        for name in fieldnames:
            FIELDTYPE = TYPE._flds[name]
            if isinstance(FIELDTYPE, lltype.ContainerType):
                raise CannotRemoveThisType("inlined substructure")
            self.name2index[name] = len(self.names_and_types)
            self.names_and_types.append((name, FIELDTYPE))
            self.name2subtype[name] = TYPE


class SpecNode(object):
    pass


class RuntimeSpecNode(SpecNode):

    def __init__(self, name, TYPE):
        self.name = name
        self.TYPE = TYPE

    def newvar(self):
        v = Variable(self.name)
        v.concretetype = self.TYPE
        return v

    def getfrozenkey(self, memo):
        return 'R'

    def accumulate_nodes(self, rtnodes, vtnodes):
        rtnodes.append(self)

    def copy(self, memo, flagreadonly):
        return RuntimeSpecNode(self.name, self.TYPE)

    def bind_rt_nodes(self, memo, newnodes_iter):
        return newnodes_iter.next()


class VirtualSpecNode(SpecNode):

    def __init__(self, typedesc, fields, readonly=False):
        self.typedesc = typedesc
        self.fields = fields     # list of SpecNodes
        self.readonly = readonly

    def getfrozenkey(self, memo):
        if self in memo:
            return memo[self]
        else:
            memo[self] = len(memo)
            result = [self.typedesc, self.readonly]
            for subnode in self.fields:
                result.append(subnode.getfrozenkey(memo))
            return tuple(result)

    def accumulate_nodes(self, rtnodes, vtnodes):
        if self in vtnodes:
            return
        vtnodes[self] = True
        for subnode in self.fields:
            subnode.accumulate_nodes(rtnodes, vtnodes)

    def copy(self, memo, flagreadonly):
        if self in memo:
            return memo[self]
        readonly = self.readonly or self in flagreadonly
        newnode = VirtualSpecNode(self.typedesc, [], readonly)
        memo[self] = newnode
        for subnode in self.fields:
            newnode.fields.append(subnode.copy(memo, flagreadonly))
        return newnode

    def bind_rt_nodes(self, memo, newnodes_iter):
        if self in memo:
            return memo[self]
        newnode = VirtualSpecNode(self.typedesc, [], self.readonly)
        memo[self] = newnode
        for subnode in self.fields:
            newnode.fields.append(subnode.bind_rt_nodes(memo, newnodes_iter))
        return newnode


class VirtualFrame(object):

    def __init__(self, sourceblock, nextopindex,
                 allnodes, callerframe=None, calledgraphs={}):
        if isinstance(allnodes, dict):
            self.varlist = vars_alive_through_op(sourceblock, nextopindex)
            self.nodelist = [allnodes[v] for v in self.varlist]
        else:
            assert nextopindex == 0
            self.varlist = sourceblock.inputargs
            self.nodelist = allnodes[:]
        self.sourceblock = sourceblock
        self.nextopindex = nextopindex
        self.callerframe = callerframe
        self.calledgraphs = calledgraphs

    def get_nodes_in_use(self):
        return dict(zip(self.varlist, self.nodelist))

    def shallowcopy(self):
        newframe = VirtualFrame.__new__(VirtualFrame)
        newframe.varlist = self.varlist
        newframe.nodelist = self.nodelist
        newframe.sourceblock = self.sourceblock
        newframe.nextopindex = self.nextopindex
        newframe.callerframe = self.callerframe
        newframe.calledgraphs = self.calledgraphs
        return newframe

    def copy(self, memo, flagreadonly={}):
        newframe = self.shallowcopy()
        newframe.nodelist = [node.copy(memo, flagreadonly)
                             for node in newframe.nodelist]
        if newframe.callerframe is not None:
            newframe.callerframe = newframe.callerframe.copy(memo,
                                                             flagreadonly)
        return newframe

    def enum_call_stack(self):
        frame = self
        while frame is not None:
            yield frame
            frame = frame.callerframe

    def getfrozenkey(self):
        memo = {}
        key = []
        for frame in self.enum_call_stack():
            key.append(frame.sourceblock)
            key.append(frame.nextopindex)
            for node in frame.nodelist:
                key.append(node.getfrozenkey(memo))
        return tuple(key)

    def find_all_nodes(self):
        rtnodes = []
        vtnodes = {}
        for frame in self.enum_call_stack():
            for node in frame.nodelist:
                node.accumulate_nodes(rtnodes, vtnodes)
        return rtnodes, vtnodes

    def find_rt_nodes(self):
        rtnodes, vtnodes = self.find_all_nodes()
        return rtnodes

    def find_vt_nodes(self):
        rtnodes, vtnodes = self.find_all_nodes()
        return vtnodes


def copynodes(nodelist, flagreadonly={}):
    memo = {}
    return [node.copy(memo, flagreadonly) for node in nodelist]

def find_all_nodes(nodelist):
    rtnodes = []
    vtnodes = {}
    for node in nodelist:
        node.accumulate_nodes(rtnodes, vtnodes)
    return rtnodes, vtnodes

def is_trivial_nodelist(nodelist):
    for node in nodelist:
        if not isinstance(node, RuntimeSpecNode):
            return False
    return True

def bind_rt_nodes(srcnodelist, newnodes_list):
    """Return srcnodelist with all RuntimeNodes replaced by nodes
    coming from newnodes_list.
    """
    memo = {}
    newnodes_iter = iter(newnodes_list)
    result = [node.bind_rt_nodes(memo, newnodes_iter) for node in srcnodelist]
    rest = list(newnodes_iter)
    assert rest == [], "too many nodes in newnodes_list"
    return result


class CannotVirtualize(Exception):
    pass

class ForcedInline(Exception):
    pass

class CannotRemoveThisType(Exception):
    pass

# ____________________________________________________________


class MallocVirtualizer(object):

    def __init__(self, graphs, rtyper, verbose=False):
        self.graphs = graphs
        self.rtyper = rtyper
        self.excdata = rtyper.getexceptiondata()
        self.graphbuilders = {}
        self.specialized_graphs = {}
        self.specgraphorigin = {}
        self.inline_and_remove = {}    # {graph: op_to_remove}
        self.inline_and_remove_seen = {}   # set of (graph, op_to_remove)
        self.malloctypedescs = {}
        self.count_virtualized = 0
        self.verbose = verbose
        self.EXCTYPE_to_vtable = self.build_obscure_mapping()

    def build_obscure_mapping(self):
        result = {}
        for rinstance in self.rtyper.instance_reprs.values():
            result[rinstance.lowleveltype.TO] = rinstance.rclass.getvtable()
        return result

    def report_result(self, progress):
        if progress:
            log.mallocv('removed %d mallocs so far' % self.count_virtualized)
        else:
            log.mallocv('done')

    def enum_all_mallocs(self, graph):
        for block in graph.iterblocks():
            for op in block.operations:
                if op.opname == 'malloc':
                    MALLOCTYPE = op.result.concretetype.TO
                    try:
                        self.getmalloctypedesc(MALLOCTYPE)
                    except CannotRemoveThisType:
                        pass
                    else:
                        yield (block, op)
                elif op.opname == 'direct_call':
                    graph = graph_called_by(op)
                    if graph in self.inline_and_remove:
                        yield (block, op)

    def remove_mallocs_once(self):
        self.flush_failed_specializations()
        prev = self.count_virtualized
        count_inline_and_remove = len(self.inline_and_remove)
        for graph in self.graphs:
            seen = {}
            while True:
                for block, op in self.enum_all_mallocs(graph):
                    if op.result not in seen:
                        seen[op.result] = True
                        if self.try_remove_malloc(graph, block, op):
                            break   # graph mutated, restart enum_all_mallocs()
                else:
                    break   # enum_all_mallocs() exhausted, graph finished
        progress1 = self.count_virtualized - prev
        progress2 = len(self.inline_and_remove) - count_inline_and_remove
        progress = progress1 or bool(progress2)
        self.report_result(progress)
        return progress

    def flush_failed_specializations(self):
        for key, (mode, specgraph) in self.specialized_graphs.items():
            if mode == 'fail':
                del self.specialized_graphs[key]

    def fixup_except_block(self, exceptblock):
        # hack: this block's inputargs may be missing concretetypes...
        e1, v1 = exceptblock.inputargs
        e1.concretetype = self.excdata.lltype_of_exception_type
        v1.concretetype = self.excdata.lltype_of_exception_value

    def getmalloctypedesc(self, MALLOCTYPE):
        try:
            dsc = self.malloctypedescs[MALLOCTYPE]
        except KeyError:
            dsc = self.malloctypedescs[MALLOCTYPE] = MallocTypeDesc(MALLOCTYPE)
        return dsc

    def try_remove_malloc(self, graph, block, op):
        if (graph, op) in self.inline_and_remove_seen:
            return False      # no point in trying again
        graphbuilder = GraphBuilder(self, graph)
        if graph in self.graphbuilders:
            graphbuilder.initialize_from_old_builder(self.graphbuilders[graph])
        graphbuilder.start_from_a_malloc(graph, block, op.result)
        try:
            graphbuilder.propagate_specializations()
        except CannotVirtualize, e:
            self.logresult(op, 'failed', e)
            return False
        except ForcedInline, e:
            self.logresult(op, 'forces inlining', e)
            self.inline_and_remove[graph] = op
            self.inline_and_remove_seen[graph, op] = True
            return False
        else:
            self.logresult(op, 'removed')
            graphbuilder.finished_removing_malloc()
            self.graphbuilders[graph] = graphbuilder
            self.count_virtualized += 1
            return True

    def logresult(self, op, msg, exc=None):    # only for nice log outputs
        if self.verbose:
            if exc is None:
                exc = ''
            else:
                exc = ': %s' % (exc,)
            chain = []
            while True:
                chain.append(str(op.result))
                if op.opname != 'direct_call':
                    break
                fobj = op.args[0].value._obj
                op = self.inline_and_remove[fobj.graph]
            log.mallocv('%s %s%s' % ('->'.join(chain), msg, exc))
        elif exc is None:
            log.dot()

    def get_specialized_graph(self, graph, nodelist):
        assert len(graph.getargs()) == len(nodelist)
        if is_trivial_nodelist(nodelist):
            return 'trivial', graph
        if graph in self.specgraphorigin:
            orggraph, orgnodelist = self.specgraphorigin[graph]
            nodelist = bind_rt_nodes(orgnodelist, nodelist)
            graph = orggraph
        virtualframe = VirtualFrame(graph.startblock, 0, nodelist)
        key = virtualframe.getfrozenkey()
        try:
            return self.specialized_graphs[key]
        except KeyError:
            self.build_specialized_graph(graph, key, nodelist)
            return self.specialized_graphs[key]

    def build_specialized_graph(self, graph, key, nodelist):
        graph2 = copygraph(graph)
        virtualframe = VirtualFrame(graph2.startblock, 0, nodelist)
        graphbuilder = GraphBuilder(self, graph2)
        specblock = graphbuilder.start_from_virtualframe(virtualframe)
        specblock.isstartblock = True
        specgraph = graph2
        specgraph.name += '_mallocv'
        specgraph.startblock = specblock
        self.specialized_graphs[key] = ('call', specgraph)
        try:
            graphbuilder.propagate_specializations()
        except ForcedInline, e:
            if self.verbose:
                log.mallocv('%s inlined: %s' % (graph.name, e))
            self.specialized_graphs[key] = ('inline', None)
        except CannotVirtualize, e:
            if self.verbose:
                log.mallocv('%s failing: %s' % (graph.name, e))
            self.specialized_graphs[key] = ('fail', None)
        else:
            self.graphbuilders[specgraph] = graphbuilder
            self.specgraphorigin[specgraph] = graph, nodelist
            self.graphs.append(specgraph)


class GraphBuilder(object):

    def __init__(self, mallocv, graph):
        self.mallocv = mallocv
        self.graph = graph
        self.specialized_blocks = {}
        self.pending_specializations = []

    def initialize_from_old_builder(self, oldbuilder):
        self.specialized_blocks.update(oldbuilder.specialized_blocks)

    def start_from_virtualframe(self, startframe):
        spec = BlockSpecializer(self)
        spec.initialize_renamings(startframe)
        self.pending_specializations.append(spec)
        return spec.specblock

    def start_from_a_malloc(self, graph, block, v_result):
        assert v_result in [op.result for op in block.operations]
        nodelist = []
        for v in block.inputargs:
            nodelist.append(RuntimeSpecNode(v, v.concretetype))
        trivialframe = VirtualFrame(block, 0, nodelist)
        spec = BlockSpecializer(self, v_result)
        spec.initialize_renamings(trivialframe, keep_inputargs=True)
        self.pending_specializations.append(spec)
        self.pending_patch = (block, spec.specblock)

    def finished_removing_malloc(self):
        (srcblock, specblock) = self.pending_patch
        srcblock.inputargs = specblock.inputargs
        srcblock.operations = specblock.operations
        srcblock.exitswitch = specblock.exitswitch
        srcblock.recloseblock(*specblock.exits)

    def create_outgoing_link(self, currentframe, targetblock,
                             nodelist, renamings, v_expand_malloc=None):
        assert len(nodelist) == len(targetblock.inputargs)
        #
        if is_except(targetblock):
            v_expand_malloc = None
            while currentframe.callerframe is not None:
                currentframe = currentframe.callerframe
                newlink = self.handle_catch(currentframe, nodelist, renamings)
                if newlink:
                    return newlink
            else:
                targetblock = self.exception_escapes(nodelist, renamings)
                assert len(nodelist) == len(targetblock.inputargs)

        if (currentframe.callerframe is None and
              is_trivial_nodelist(nodelist)):
            # there is no more VirtualSpecNodes being passed around,
            # so we can stop specializing
            rtnodes = nodelist
            specblock = targetblock
        else:
            if is_return(targetblock):
                v_expand_malloc = None
                newframe = self.return_to_caller(currentframe, nodelist[0])
            else:
                targetnodes = dict(zip(targetblock.inputargs, nodelist))
                newframe = VirtualFrame(targetblock, 0, targetnodes,
                                        callerframe=currentframe.callerframe,
                                        calledgraphs=currentframe.calledgraphs)
            rtnodes = newframe.find_rt_nodes()
            specblock = self.get_specialized_block(newframe, v_expand_malloc)

        linkargs = [renamings[rtnode] for rtnode in rtnodes]
        return Link(linkargs, specblock)

    def return_to_caller(self, currentframe, retnode):
        callerframe = currentframe.callerframe
        if callerframe is None:
            raise ForcedInline("return block")
        nodelist = callerframe.nodelist
        callerframe = callerframe.shallowcopy()
        callerframe.nodelist = []
        for node in nodelist:
            if isinstance(node, FutureReturnValue):
                node = retnode
            callerframe.nodelist.append(node)
        return callerframe

    def handle_catch(self, catchingframe, nodelist, renamings):
        if not self.has_exception_catching(catchingframe):
            return None
        [exc_node, exc_value_node] = nodelist
        v_exc_type = renamings.get(exc_node)
        if isinstance(v_exc_type, Constant):
            exc_type = v_exc_type.value
        elif isinstance(exc_value_node, VirtualSpecNode):
            EXCTYPE = exc_value_node.typedesc.MALLOCTYPE
            exc_type = self.mallocv.EXCTYPE_to_vtable[EXCTYPE]
        else:
            raise CannotVirtualize("raising non-constant exc type")
        excdata = self.mallocv.excdata
        assert catchingframe.sourceblock.exits[0].exitcase is None
        for catchlink in catchingframe.sourceblock.exits[1:]:
            if excdata.fn_exception_match(exc_type, catchlink.llexitcase):
                # Match found.  Follow this link.
                mynodes = catchingframe.get_nodes_in_use()
                for node, attr in zip(nodelist,
                                      ['last_exception', 'last_exc_value']):
                    v = getattr(catchlink, attr)
                    if isinstance(v, Variable):
                        mynodes[v] = node
                #
                nodelist = []
                for v in catchlink.args:
                    if isinstance(v, Variable):
                        node = mynodes[v]
                    else:
                        node = getconstnode(v, renamings)
                    nodelist.append(node)
                return self.create_outgoing_link(catchingframe,
                                                 catchlink.target,
                                                 nodelist, renamings)
        else:
            # No match at all, propagate the exception to the caller
            return None

    def has_exception_catching(self, catchingframe):
        if catchingframe.sourceblock.exitswitch != c_last_exception:
            return False
        else:
            operations = catchingframe.sourceblock.operations
            assert 1 <= catchingframe.nextopindex <= len(operations)
            return catchingframe.nextopindex == len(operations)

    def exception_escapes(self, nodelist, renamings):
        # the exception escapes
        if not is_trivial_nodelist(nodelist):
            # start of hacks to help handle_catch()
            [exc_node, exc_value_node] = nodelist
            v_exc_type = renamings.get(exc_node)
            if isinstance(v_exc_type, Constant):
                # cannot improve: handle_catch() would already be happy
                # by seeing the exc_type as a constant
                pass
            elif isinstance(exc_value_node, VirtualSpecNode):
                # can improve with a strange hack: we pretend that
                # the source code jumps to a block that itself allocates
                # the exception, sets all fields, and raises it by
                # passing a constant type.
                typedesc = exc_value_node.typedesc
                return self.get_exc_reconstruction_block(typedesc)
            else:
                # cannot improve: handle_catch() will have no clue about
                # the exception type
                pass
            raise CannotVirtualize("except block")
        targetblock = self.graph.exceptblock
        self.mallocv.fixup_except_block(targetblock)
        return targetblock

    def get_exc_reconstruction_block(self, typedesc):
        exceptblock = self.graph.exceptblock
        self.mallocv.fixup_except_block(exceptblock)
        TEXC = exceptblock.inputargs[0].concretetype
        TVAL = exceptblock.inputargs[1].concretetype
        #
        v_ignored_type = varoftype(TEXC)
        v_incoming_value = varoftype(TVAL)
        block = Block([v_ignored_type, v_incoming_value])
        #
        c_EXCTYPE = Constant(typedesc.MALLOCTYPE, lltype.Void)
        v = varoftype(lltype.Ptr(typedesc.MALLOCTYPE))
        c_flavor = Constant({'flavor': 'gc'}, lltype.Void)
        op = SpaceOperation('malloc', [c_EXCTYPE, c_flavor], v)
        block.operations.append(op)
        #
        for name, FIELDTYPE in typedesc.names_and_types:
            EXACTPTR = lltype.Ptr(typedesc.name2subtype[name])
            c_name = Constant(name)
            c_name.concretetype = lltype.Void
            #
            v_in = varoftype(EXACTPTR)
            op = SpaceOperation('cast_pointer', [v_incoming_value], v_in)
            block.operations.append(op)
            #
            v_field = varoftype(FIELDTYPE)
            op = SpaceOperation('getfield', [v_in, c_name], v_field)
            block.operations.append(op)
            #
            v_out = varoftype(EXACTPTR)
            op = SpaceOperation('cast_pointer', [v], v_out)
            block.operations.append(op)
            #
            v0 = varoftype(lltype.Void)
            op = SpaceOperation('setfield', [v_out, c_name, v_field], v0)
            block.operations.append(op)
        #
        v_exc_value = varoftype(TVAL)
        op = SpaceOperation('cast_pointer', [v], v_exc_value)
        block.operations.append(op)
        #
        exc_type = self.mallocv.EXCTYPE_to_vtable[typedesc.MALLOCTYPE]
        c_exc_type = Constant(exc_type, TEXC)
        block.closeblock(Link([c_exc_type, v_exc_value], exceptblock))
        return block

    def get_specialized_block(self, virtualframe, v_expand_malloc=None):
        key = virtualframe.getfrozenkey()
        specblock = self.specialized_blocks.get(key)
        if specblock is None:
            orgblock = virtualframe.sourceblock
            assert len(orgblock.exits) != 0
            spec = BlockSpecializer(self, v_expand_malloc)
            spec.initialize_renamings(virtualframe)
            self.pending_specializations.append(spec)
            specblock = spec.specblock
            self.specialized_blocks[key] = specblock
        return specblock

    def propagate_specializations(self):
        while self.pending_specializations:
            spec = self.pending_specializations.pop()
            spec.specialize_operations()
            spec.follow_exits()


class BlockSpecializer(object):

    def __init__(self, graphbuilder, v_expand_malloc=None):
        self.graphbuilder = graphbuilder
        self.v_expand_malloc = v_expand_malloc
        self.specblock = Block([])

    def initialize_renamings(self, virtualframe, keep_inputargs=False):
        # we make a copy of the original 'virtualframe' because the
        # specialize_operations() will mutate some of its content.
        virtualframe = virtualframe.copy({})
        self.virtualframe = virtualframe
        self.nodes = virtualframe.get_nodes_in_use()
        self.renamings = {}    # {RuntimeSpecNode(): Variable()}
        if keep_inputargs:
            assert virtualframe.varlist == virtualframe.sourceblock.inputargs
        specinputargs = []
        for i, rtnode in enumerate(virtualframe.find_rt_nodes()):
            if keep_inputargs:
                v = virtualframe.varlist[i]
                assert v.concretetype == rtnode.TYPE
            else:
                v = rtnode.newvar()
            self.renamings[rtnode] = v
            specinputargs.append(v)
        self.specblock.inputargs = specinputargs

    def setnode(self, v, node):
        assert v not in self.nodes
        self.nodes[v] = node

    def getnode(self, v):
        if isinstance(v, Variable):
            return self.nodes[v]
        else:
            return getconstnode(v, self.renamings)

    def rename_nonvirtual(self, v, where=None):
        if not isinstance(v, Variable):
            return v
        node = self.nodes[v]
        if not isinstance(node, RuntimeSpecNode):
            raise CannotVirtualize(where)
        return self.renamings[node]

    def expand_nodes(self, nodelist):
        rtnodes, vtnodes = find_all_nodes(nodelist)
        return [self.renamings[rtnode] for rtnode in rtnodes]

    def specialize_operations(self):
        newoperations = []
        self.ops_produced_by_last_op = 0
        # note that 'self.virtualframe' can be changed during the loop!
        while True:
            operations = self.virtualframe.sourceblock.operations
            try:
                op = operations[self.virtualframe.nextopindex]
                self.virtualframe.nextopindex += 1
            except IndexError:
                break

            meth = getattr(self, 'handle_op_' + op.opname,
                           self.handle_default)
            newops_for_this_op = meth(op)
            newoperations += newops_for_this_op
            self.ops_produced_by_last_op = len(newops_for_this_op)
        for op in newoperations:
            if op.opname == 'direct_call':
                graph = graph_called_by(op)
                if graph in self.virtualframe.calledgraphs:
                    raise CannotVirtualize("recursion in residual call")
        self.specblock.operations = newoperations

    def follow_exits(self):
        block = self.virtualframe.sourceblock
        self.specblock.exitswitch = self.rename_nonvirtual(block.exitswitch,
                                                           'exitswitch')
        links = block.exits
        catch_exc = self.specblock.exitswitch == c_last_exception

        if not catch_exc and isinstance(self.specblock.exitswitch, Constant):
            # constant-fold the switch
            for link in links:
                if link.exitcase == 'default':
                    break
                if link.llexitcase == self.specblock.exitswitch.value:
                    break
            else:
                raise Exception("exit case not found?")
            links = (link,)
            self.specblock.exitswitch = None

        if catch_exc and self.ops_produced_by_last_op == 0:
            # the last op of the sourceblock did not produce any
            # operation in specblock, so we need to discard the
            # exception-catching.
            catch_exc = False
            links = links[:1]
            assert links[0].exitcase is None  # the non-exception-catching case
            self.specblock.exitswitch = None

        newlinks = []
        for link in links:
            is_catch_link = catch_exc and link.exitcase is not None
            if is_catch_link:
                extravars = []
                for attr in ['last_exception', 'last_exc_value']:
                    v = getattr(link, attr)
                    if isinstance(v, Variable):
                        rtnode = RuntimeSpecNode(v, v.concretetype)
                        self.setnode(v, rtnode)
                        self.renamings[rtnode] = v = rtnode.newvar()
                    extravars.append(v)

            linkargsnodes = [self.getnode(v1) for v1 in link.args]
            #
            newlink = self.graphbuilder.create_outgoing_link(
                self.virtualframe, link.target, linkargsnodes,
                self.renamings, self.v_expand_malloc)
            #
            if self.specblock.exitswitch is not None:
                newlink.exitcase = link.exitcase
                if hasattr(link, 'llexitcase'):
                    newlink.llexitcase = link.llexitcase
                if is_catch_link:
                    newlink.extravars(*extravars)
            newlinks.append(newlink)

        self.specblock.closeblock(*newlinks)

    def make_rt_result(self, v_result):
        newrtnode = RuntimeSpecNode(v_result, v_result.concretetype)
        self.setnode(v_result, newrtnode)
        v_new = newrtnode.newvar()
        self.renamings[newrtnode] = v_new
        return v_new

    def make_const_rt_result(self, v_result, value):
        newrtnode = RuntimeSpecNode(v_result, v_result.concretetype)
        self.setnode(v_result, newrtnode)
        if v_result.concretetype is not lltype.Void:
            assert v_result.concretetype == lltype.typeOf(value)
        c_value = Constant(value)
        c_value.concretetype = v_result.concretetype
        self.renamings[newrtnode] = c_value

    def handle_default(self, op):
        newargs = [self.rename_nonvirtual(v, op) for v in op.args]
        constresult = try_fold_operation(op.opname, newargs,
                                         op.result.concretetype)
        if constresult:
            self.make_const_rt_result(op.result, constresult[0])
            return []
        else:
            newresult = self.make_rt_result(op.result)
            return [SpaceOperation(op.opname, newargs, newresult)]

    def handle_unreachable(self, op):
        from pypy.rpython.lltypesystem.rstr import string_repr
        msg = 'unreachable: %s' % (op,)
        ll_msg = string_repr.convert_const(msg)
        c_msg = Constant(ll_msg, lltype.typeOf(ll_msg))
        newresult = self.make_rt_result(op.result)
        return [SpaceOperation('debug_fatalerror', [c_msg], newresult)]

    def handle_op_getfield(self, op):
        node = self.getnode(op.args[0])
        if isinstance(node, VirtualSpecNode):
            fieldname = op.args[1].value
            index = node.typedesc.name2index[fieldname]
            self.setnode(op.result, node.fields[index])
            return []
        else:
            return self.handle_default(op)

    def handle_op_setfield(self, op):
        node = self.getnode(op.args[0])
        if isinstance(node, VirtualSpecNode):
            if node.readonly:
                raise ForcedInline(op)
            fieldname = op.args[1].value
            index = node.typedesc.name2index[fieldname]
            node.fields[index] = self.getnode(op.args[2])
            return []
        else:
            return self.handle_default(op)

    def handle_op_same_as(self, op):
        node = self.getnode(op.args[0])
        if isinstance(node, VirtualSpecNode):
            node = self.getnode(op.args[0])
            self.setnode(op.result, node)
            return []
        else:
            return self.handle_default(op)

    def handle_op_cast_pointer(self, op):
        node = self.getnode(op.args[0])
        if isinstance(node, VirtualSpecNode):
            node = self.getnode(op.args[0])
            SOURCEPTR = lltype.Ptr(node.typedesc.MALLOCTYPE)
            TARGETPTR = op.result.concretetype
            try:
                if lltype.castable(TARGETPTR, SOURCEPTR) < 0:
                    raise lltype.InvalidCast
            except lltype.InvalidCast:
                return self.handle_unreachable(op)
            self.setnode(op.result, node)
            return []
        else:
            return self.handle_default(op)

    def handle_op_ptr_nonzero(self, op):
        node = self.getnode(op.args[0])
        if isinstance(node, VirtualSpecNode):
            self.make_const_rt_result(op.result, True)
            return []
        else:
            return self.handle_default(op)

    def handle_op_ptr_iszero(self, op):
        node = self.getnode(op.args[0])
        if isinstance(node, VirtualSpecNode):
            self.make_const_rt_result(op.result, False)
            return []
        else:
            return self.handle_default(op)

    def handle_op_ptr_eq(self, op):
        node0 = self.getnode(op.args[0])
        node1 = self.getnode(op.args[1])
        if (isinstance(node0, VirtualSpecNode) or
            isinstance(node1, VirtualSpecNode)):
            self.make_const_rt_result(op.result, node0 is node1)
            return []
        else:
            return self.handle_default(op)

    def handle_op_ptr_ne(self, op):
        node0 = self.getnode(op.args[0])
        node1 = self.getnode(op.args[1])
        if (isinstance(node0, VirtualSpecNode) or
            isinstance(node1, VirtualSpecNode)):
            self.make_const_rt_result(op.result, node0 is not node1)
            return []
        else:
            return self.handle_default(op)

    def handle_op_malloc(self, op):
        if op.result is self.v_expand_malloc:
            MALLOCTYPE = op.result.concretetype.TO
            typedesc = self.graphbuilder.mallocv.getmalloctypedesc(MALLOCTYPE)
            virtualnode = VirtualSpecNode(typedesc, [])
            self.setnode(op.result, virtualnode)
            for name, FIELDTYPE in typedesc.names_and_types:
                fieldnode = RuntimeSpecNode(name, FIELDTYPE)
                virtualnode.fields.append(fieldnode)
                c = Constant(FIELDTYPE._defl())
                c.concretetype = FIELDTYPE
                self.renamings[fieldnode] = c
            self.v_expand_malloc = None      # done
            return []
        else:
            return self.handle_default(op)

    def handle_op_direct_call(self, op):
        graph = graph_called_by(op)
        if graph is None:
            return self.handle_default(op)
        nb_args = len(op.args) - 1
        assert nb_args == len(graph.getargs())
        newnodes = [self.getnode(v) for v in op.args[1:]]
        myframe = self.get_updated_frame(op)
        mallocv = self.graphbuilder.mallocv

        if op.result is self.v_expand_malloc:
            # move to inlining the callee, and continue looking for the
            # malloc to expand in the callee's graph
            op_to_remove = mallocv.inline_and_remove[graph]
            self.v_expand_malloc = op_to_remove.result
            return self.handle_inlined_call(myframe, graph, newnodes)

        argnodes = copynodes(newnodes, flagreadonly=myframe.find_vt_nodes())
        kind, newgraph = mallocv.get_specialized_graph(graph, argnodes)
        if kind == 'trivial':
            return self.handle_default(op)
        elif kind == 'inline':
            return self.handle_inlined_call(myframe, graph, newnodes)
        elif kind == 'call':
            return self.handle_residual_call(op, newgraph, newnodes)
        elif kind == 'fail':
            raise CannotVirtualize(op)
        else:
            raise ValueError(kind)

    def get_updated_frame(self, op):
        sourceblock = self.virtualframe.sourceblock
        nextopindex = self.virtualframe.nextopindex
        self.nodes[op.result] = FutureReturnValue(op)
        myframe = VirtualFrame(sourceblock, nextopindex, self.nodes,
                               self.virtualframe.callerframe,
                               self.virtualframe.calledgraphs)
        del self.nodes[op.result]
        return myframe

    def handle_residual_call(self, op, newgraph, newnodes):
        fspecptr = getfunctionptr(newgraph)
        newargs = [Constant(fspecptr,
                            concretetype=lltype.typeOf(fspecptr))]
        newargs += self.expand_nodes(newnodes)
        newresult = self.make_rt_result(op.result)
        newop = SpaceOperation('direct_call', newargs, newresult)
        return [newop]

    def handle_inlined_call(self, myframe, graph, newnodes):
        assert len(graph.getargs()) == len(newnodes)
        targetnodes = dict(zip(graph.getargs(), newnodes))
        calledgraphs = myframe.calledgraphs.copy()
        if graph in calledgraphs:
            raise CannotVirtualize("recursion during inlining")
        calledgraphs[graph] = True
        calleeframe = VirtualFrame(graph.startblock, 0,
                                   targetnodes, myframe, calledgraphs)
        self.virtualframe = calleeframe
        self.nodes = calleeframe.get_nodes_in_use()
        return []

    def handle_op_indirect_call(self, op):
        v_func = self.rename_nonvirtual(op.args[0], op)
        if isinstance(v_func, Constant):
            op = SpaceOperation('direct_call', [v_func] + op.args[1:-1],
                                op.result)
            return self.handle_op_direct_call(op)
        else:
            return self.handle_default(op)


class FutureReturnValue(object):
    def __init__(self, op):
        self.op = op    # for debugging
    def getfrozenkey(self, memo):
        return None
    def accumulate_nodes(self, rtnodes, vtnodes):
        pass
    def copy(self, memo, flagreadonly):
        return self

# ____________________________________________________________
# helpers

def vars_alive_through_op(block, index):
    # NB. make sure this always returns the variables in the same order
    if len(block.exits) == 0:
        return block.inputargs   # return or except block
    result = []
    seen = {}
    def see(v):
        if isinstance(v, Variable) and v not in seen:
            result.append(v)
            seen[v] = True
    # don't include the variables produced by the current or future operations
    for op in block.operations[index:]:
        seen[op.result] = True
    # don't include the extra vars produced by exception-catching links
    for link in block.exits:
        for v in link.getextravars():
            seen[v] = True
    # but include the variables consumed by the current or any future operation
    for op in block.operations[index:]:
        for v in op.args:
            see(v)
    see(block.exitswitch)
    for link in block.exits:
        for v in link.args:
            see(v)
    return result

def is_return(block):
    return len(block.exits) == 0 and len(block.inputargs) == 1

def is_except(block):
    return len(block.exits) == 0 and len(block.inputargs) == 2

class CannotConstFold(Exception):
    pass

def try_fold_operation(opname, args_v, RESTYPE):
    args = []
    for c in args_v:
        if not isinstance(c, Constant):
            return
        args.append(c.value)
    try:
        op = getattr(llop, opname)
    except AttributeError:
        return
    if not op.is_pure(args_v):
        return
    try:
        result = op(RESTYPE, *args)
    except TypeError:
        pass
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception, e:
        pass
        #log.WARNING('constant-folding %s%r:' % (opname, args_v))
        #log.WARNING('  %s: %s' % (e.__class__.__name__, e))
    else:
        return (result,)

def getconstnode(v, renamings):
    rtnode = RuntimeSpecNode(None, v.concretetype)
    renamings[rtnode] = v
    return rtnode

def graph_called_by(op):
    assert op.opname == 'direct_call'
    fobj = op.args[0].value._obj
    graph = getattr(fobj, 'graph', None)
    return graph
