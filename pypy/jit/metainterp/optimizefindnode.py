from pypy.jit.metainterp.specnode import SpecNode
from pypy.jit.metainterp.specnode import NotSpecNode, prebuiltNotSpecNode
from pypy.jit.metainterp.specnode import ConstantSpecNode
from pypy.jit.metainterp.specnode import VirtualInstanceSpecNode
from pypy.jit.metainterp.specnode import VirtualArraySpecNode
from pypy.jit.metainterp.specnode import VirtualStructSpecNode
from pypy.jit.metainterp.history import AbstractValue, ConstInt, Const
from pypy.jit.metainterp.resoperation import rop
from pypy.jit.metainterp.executor import execute_nonspec
from pypy.jit.metainterp.optimizeutil import _findall, sort_descrs
from pypy.jit.metainterp.optimizeutil import InvalidLoop

# ____________________________________________________________

UNIQUE_UNKNOWN = '\x00'
UNIQUE_NO      = '\x01'
UNIQUE_INST    = '\x02'
UNIQUE_ARRAY   = '\x03'
UNIQUE_STRUCT  = '\x04'

class InstanceNode(object):
    """An instance of this class is used to match the start and
    the end of the loop, so it contains both 'origfields' that represents
    the field's status at the start and 'curfields' that represents it
    at the current point (== the end when optimizefindnode is complete).
    """
    escaped = False     # if True, then all the rest of the info is pointless
    unique = UNIQUE_UNKNOWN   # for find_unique_nodes()

    # fields used to store the shape of the potential VirtualInstance
    knownclsbox = None  # set only on freshly-allocated or fromstart structures
    origfields = None   # optimization; equivalent to an empty dict
    curfields = None    # optimization; equivalent to an empty dict

    knownvaluebox = None # a Const with the value of this box, if constant

    # fields used to store the shape of the potential VirtualList
    arraydescr = None   # set only on freshly-allocated or fromstart arrays
    #arraysize = ..     # valid if and only if arraydescr is not None
    origitems = None    # optimization; equivalent to an empty dict
    curitems = None     # optimization; equivalent to an empty dict

    # fields used to store the shape of the potential VirtualStruct
    structdescr = None  # set only on freshly-allocated or fromstart structs
    #origfields = ..    # same as above
    #curfields = ..     # same as above

    dependencies = None

    def __init__(self, fromstart=False):
        self.fromstart = fromstart    # for loops only: present since the start

    def is_constant(self):
        return self.knownvaluebox is not None

    def add_escape_dependency(self, other):
        assert not self.escaped
        if self.dependencies is None:
            self.dependencies = []
        self.dependencies.append(other)

    def mark_escaped(self):
        # invariant: if escaped=True, then dependencies is None
        if not self.escaped:
            self.escaped = True
            if self.dependencies is not None:
                deps = self.dependencies
                self.dependencies = None
                for box in deps:
                    box.mark_escaped()
                    # see test_find_nodes_store_into_loop_constant_1 for this:
                    box.unique = UNIQUE_NO

    def set_unique_nodes(self):
        if self.fromstart:
            self.mark_escaped()
        if self.escaped or self.unique != UNIQUE_UNKNOWN:
            # this node is not suitable for being a virtual, or we
            # encounter it more than once when doing the recursion
            self.unique = UNIQUE_NO
        elif self.knownclsbox is not None:
            self.unique = UNIQUE_INST
            if self.curfields is not None:
                for subnode in self.curfields.itervalues():
                    subnode.set_unique_nodes()
        elif self.arraydescr is not None:
            self.unique = UNIQUE_ARRAY
            if self.curitems is not None:
                for subnode in self.curitems.itervalues():
                    subnode.set_unique_nodes()
        elif self.structdescr is not None:
            self.unique = UNIQUE_STRUCT
            if self.curfields is not None:
                for subnode in self.curfields.itervalues():
                    subnode.set_unique_nodes()
        else:
            assert 0, "most probably unreachable"

    def __repr__(self):
        flags = ''
        if self.escaped:     flags += 'e'
        if self.fromstart:   flags += 's'
        if self.knownclsbox: flags += 'c'
        if self.arraydescr:  flags += str(self.arraysize)
        if self.structdescr: flags += 'S'
        return "<InstanceNode (%s)>" % (flags,)

# ____________________________________________________________
# General find_nodes_xxx() interface, for both loops and bridges

class NodeFinder(object):
    """Abstract base class."""
    node_escaped = InstanceNode()
    node_escaped.unique = UNIQUE_NO
    node_escaped.escaped = True

    def __init__(self, cpu):
        self.cpu = cpu
        self.nodes = {}     # Box -> InstanceNode

    def getnode(self, box):
        if isinstance(box, Const):
            return self.set_constant_node(box, box)
        return self.nodes.get(box, self.node_escaped)

    def set_constant_node(self, box, constbox):
        assert isinstance(constbox, Const)
        node = InstanceNode()
        node.unique = UNIQUE_NO
        node.knownvaluebox = constbox
        self.nodes[box] = node
        return node

    def get_constant_box(self, box):
        if isinstance(box, Const):
            return box
        try:
            node = self.nodes[box]
        except KeyError:
            return None
        else:
            return node.knownvaluebox

    def find_nodes(self, operations):
        for op in operations:
            opnum = op.opnum
            for value, func in find_nodes_ops:
                if opnum == value:
                    func(self, op)
                    break
            else:
                self.find_nodes_default(op)

    def find_nodes_default(self, op):
        if op.is_always_pure():
            for arg in op.args:
                if self.get_constant_box(arg) is None:
                    break
            else:
                # all constant arguments: we can constant-fold
                argboxes = [self.get_constant_box(arg) for arg in op.args]
                resbox = execute_nonspec(self.cpu, op.opnum, argboxes, op.descr)
                self.set_constant_node(op.result, resbox.constbox())
        # default case: mark the arguments as escaping
        for box in op.args:
            self.getnode(box).mark_escaped()

    def find_nodes_no_escape(self, op):
        pass    # for operations that don't escape their arguments

    find_nodes_OOIS          = find_nodes_no_escape
    find_nodes_OOISNOT       = find_nodes_no_escape
    find_nodes_INSTANCEOF    = find_nodes_no_escape
    find_nodes_GUARD_NONNULL = find_nodes_no_escape
    find_nodes_GUARD_ISNULL  = find_nodes_no_escape

    def find_nodes_NEW_WITH_VTABLE(self, op):
        instnode = InstanceNode()
        box = op.args[0]
        assert isinstance(box, Const)
        instnode.knownclsbox = box
        self.nodes[op.result] = instnode

    def find_nodes_NEW(self, op):
        instnode = InstanceNode()
        instnode.structdescr = op.descr
        self.nodes[op.result] = instnode

    def find_nodes_NEW_ARRAY(self, op):
        lengthbox = op.args[0]
        lengthbox = self.get_constant_box(lengthbox)
        if lengthbox is None:
            return     # var-sized arrays are not virtual
        arraynode = InstanceNode()
        arraynode.arraysize = lengthbox.getint()
        arraynode.arraydescr = op.descr
        self.nodes[op.result] = arraynode

    def find_nodes_ARRAYLEN_GC(self, op):
        arraynode = self.getnode(op.args[0])
        if arraynode.arraydescr is not None:
            resbox = ConstInt(arraynode.arraysize)
            self.set_constant_node(op.result, resbox)

    def find_nodes_GUARD_CLASS(self, op):
        instnode = self.getnode(op.args[0])
        if instnode.fromstart:    # only useful (and safe) in this case
            box = op.args[1]
            assert isinstance(box, Const)
            instnode.knownclsbox = box

    def find_nodes_GUARD_VALUE(self, op):
        instnode = self.getnode(op.args[0])
        if instnode.fromstart:    # only useful (and safe) in this case
            box = op.args[1]
            assert isinstance(box, Const)
            instnode.knownvaluebox = box

    def find_nodes_SETFIELD_GC(self, op):
        instnode = self.getnode(op.args[0])
        fieldnode = self.getnode(op.args[1])
        if instnode.escaped:
            fieldnode.mark_escaped()
            return     # nothing to be gained from tracking the field
        field = op.descr
        assert isinstance(field, AbstractValue)
        if instnode.curfields is None:
            instnode.curfields = {}
        instnode.curfields[field] = fieldnode
        instnode.add_escape_dependency(fieldnode)

    def find_nodes_GETFIELD_GC(self, op):
        instnode = self.getnode(op.args[0])
        if instnode.escaped:
            return     # nothing to be gained from tracking the field
        field = op.descr
        assert isinstance(field, AbstractValue)
        if instnode.curfields is not None and field in instnode.curfields:
            fieldnode = instnode.curfields[field]
        elif instnode.origfields is not None and field in instnode.origfields:
            fieldnode = instnode.origfields[field]
        elif instnode.fromstart:
            fieldnode = InstanceNode(fromstart=True)
            instnode.add_escape_dependency(fieldnode)
            if instnode.origfields is None:
                instnode.origfields = {}
            instnode.origfields[field] = fieldnode
        else:
            return    # nothing to be gained from tracking the field
        self.nodes[op.result] = fieldnode

    find_nodes_GETFIELD_GC_PURE = find_nodes_GETFIELD_GC

    def find_nodes_SETARRAYITEM_GC(self, op):
        indexbox = op.args[1]
        indexbox = self.get_constant_box(indexbox)
        if indexbox is None:
            self.find_nodes_default(op)            # not a Const index
            return
        arraynode = self.getnode(op.args[0])
        itemnode = self.getnode(op.args[2])
        if arraynode.escaped:
            itemnode.mark_escaped()
            return     # nothing to be gained from tracking the item
        if arraynode.curitems is None:
            arraynode.curitems = {}
        arraynode.curitems[indexbox.getint()] = itemnode
        arraynode.add_escape_dependency(itemnode)

    def find_nodes_GETARRAYITEM_GC(self, op):
        indexbox = op.args[1]
        indexbox = self.get_constant_box(indexbox)
        if indexbox is None:
            self.find_nodes_default(op)            # not a Const index
            return
        arraynode = self.getnode(op.args[0])
        if arraynode.escaped:
            return     # nothing to be gained from tracking the item
        index = indexbox.getint()
        if arraynode.curitems is not None and index in arraynode.curitems:
            itemnode = arraynode.curitems[index]
        elif arraynode.origitems is not None and index in arraynode.origitems:
            itemnode = arraynode.origitems[index]
        elif arraynode.fromstart:
            itemnode = InstanceNode(fromstart=True)
            arraynode.add_escape_dependency(itemnode)
            if arraynode.origitems is None:
                arraynode.origitems = {}
            arraynode.origitems[index] = itemnode
        else:
            return    # nothing to be gained from tracking the item
        self.nodes[op.result] = itemnode

    find_nodes_GETARRAYITEM_GC_PURE = find_nodes_GETARRAYITEM_GC

    def find_nodes_JUMP(self, op):
        # only set up the 'unique' field of the InstanceNodes;
        # real handling comes later (build_result_specnodes() for loops).
        for box in op.args:
            self.getnode(box).set_unique_nodes()

    def find_nodes_FINISH(self, op):
        # only for bridges, and only for the ones that end in a 'return'
        # or 'raise'; all other cases end with a JUMP.
        for box in op.args:
            self.getnode(box).unique = UNIQUE_NO

find_nodes_ops = _findall(NodeFinder, 'find_nodes_')

# ____________________________________________________________
# Perfect specialization -- for loops only

class PerfectSpecializationFinder(NodeFinder):
    node_fromstart = InstanceNode(fromstart=True)

    def find_nodes_loop(self, loop):
        self.setup_input_nodes(loop.inputargs)
        self.find_nodes(loop.operations)
        self.build_result_specnodes(loop)

    def setup_input_nodes(self, inputargs):
        inputnodes = []
        for box in inputargs:
            instnode = InstanceNode(fromstart=True)
            inputnodes.append(instnode)
            self.nodes[box] = instnode
        self.inputnodes = inputnodes

    def build_result_specnodes(self, loop):
        # Build the list of specnodes based on the result
        # computed by NodeFinder.find_nodes().
        op = loop.operations[-1]
        assert op.opnum == rop.JUMP
        specnodes = []
        assert len(self.inputnodes) == len(op.args)
        for i in range(len(op.args)):
            inputnode = self.inputnodes[i]
            exitnode = self.getnode(op.args[i])
            specnodes.append(self.intersect(inputnode, exitnode))
        loop.token.specnodes = specnodes

    def intersect(self, inputnode, exitnode):
        assert inputnode.fromstart
        if inputnode.is_constant() and \
           exitnode.is_constant():
            if inputnode.knownvaluebox.same_constant(exitnode.knownvaluebox):
                return ConstantSpecNode(inputnode.knownvaluebox)
            else:
                raise InvalidLoop
        if inputnode.escaped:
            return prebuiltNotSpecNode
        unique = exitnode.unique
        if unique == UNIQUE_NO:
            return prebuiltNotSpecNode
        if unique == UNIQUE_INST:
            return self.intersect_instance(inputnode, exitnode)
        if unique == UNIQUE_ARRAY:
            return self.intersect_array(inputnode, exitnode)
        if unique == UNIQUE_STRUCT:
            return self.intersect_struct(inputnode, exitnode)
        assert 0, "unknown value for exitnode.unique: %d" % ord(unique)

    def compute_common_fields(self, orig, d):
        fields = []
        if orig is not None:
            if d is not None:
                d = d.copy()
            else:
                d = {}
            for ofs in orig:
                d.setdefault(ofs, self.node_escaped)
        if d is not None:
            lst = d.keys()
            # we always use the "standardized" order of fields
            sort_descrs(lst)
            for ofs in lst:
                try:
                    if orig is None:
                        raise KeyError
                    node = orig[ofs]
                except KeyError:
                    # field stored at exit, but not read at input.  Must
                    # still be allocated, otherwise it will be incorrectly
                    # uninitialized after a guard failure.
                    node = self.node_fromstart
                specnode = self.intersect(node, d[ofs])
                fields.append((ofs, specnode))
        return fields

    def intersect_instance(self, inputnode, exitnode):
        if (inputnode.knownclsbox is not None and
            not inputnode.knownclsbox.same_constant(exitnode.knownclsbox)):
            # unique match, but the class is known to be a mismatch
            raise InvalidLoop
        #
        fields = self.compute_common_fields(inputnode.origfields,
                                            exitnode.curfields)
        return VirtualInstanceSpecNode(exitnode.knownclsbox, fields)

    def intersect_array(self, inputnode, exitnode):
        assert inputnode.arraydescr is None
        #
        items = []
        for i in range(exitnode.arraysize):
            if exitnode.curitems is None:
                exitsubnode = self.node_escaped
            else:
                exitsubnode = exitnode.curitems.get(i, self.node_escaped)
            if inputnode.origitems is None:
                node = self.node_fromstart
            else:
                node = inputnode.origitems.get(i, self.node_fromstart)
            specnode = self.intersect(node, exitsubnode)
            items.append(specnode)
        return VirtualArraySpecNode(exitnode.arraydescr, items)

    def intersect_struct(self, inputnode, exitnode):
        assert inputnode.structdescr is None
        #
        fields = self.compute_common_fields(inputnode.origfields,
                                            exitnode.curfields)
        return VirtualStructSpecNode(exitnode.structdescr, fields)

# ____________________________________________________________
# A subclass of NodeFinder for bridges only

class __extend__(SpecNode):
    def make_instance_node(self):
        raise NotImplementedError
    def matches_instance_node(self, exitnode):
        raise NotImplementedError

class __extend__(NotSpecNode):
    def make_instance_node(self):
        return NodeFinder.node_escaped
    def matches_instance_node(self, exitnode):
        return True

class __extend__(ConstantSpecNode):
    def make_instance_node(self):
        raise AssertionError, "not implemented (but not used actually)"
    def matches_instance_node(self, exitnode):
        if exitnode.knownvaluebox is None:
            return False
        return self.constbox.same_constant(exitnode.knownvaluebox)

class __extend__(VirtualInstanceSpecNode):
    def make_instance_node(self):
        instnode = InstanceNode()
        instnode.knownclsbox = self.known_class
        instnode.curfields = {}
        for ofs, subspecnode in self.fields:
            instnode.curfields[ofs] = subspecnode.make_instance_node()
        return instnode

    def matches_instance_node(self, exitnode):
        if exitnode.unique == UNIQUE_NO:
            return False
        #
        assert exitnode.unique == UNIQUE_INST
        if not self.known_class.same_constant(exitnode.knownclsbox):
            # unique match, but the class is known to be a mismatch
            return False
        #
        return matches_fields(self.fields, exitnode.curfields)

def matches_fields(fields, d):
    seen = 0
    for ofs, subspecnode in fields:
        try:
            if d is None:
                raise KeyError
            instnode = d[ofs]
            seen += 1
        except KeyError:
            instnode = NodeFinder.node_escaped
        if not subspecnode.matches_instance_node(instnode):
            return False
    if d is not None and len(d) > seen:
        return False          # some key is in d but not in fields
    return True

class __extend__(VirtualArraySpecNode):
    def make_instance_node(self):
        raise AssertionError, "not implemented (but not used actually)"
    def matches_instance_node(self, exitnode):
        if exitnode.unique == UNIQUE_NO:
            return False
        #
        assert exitnode.unique == UNIQUE_ARRAY
        assert self.arraydescr == exitnode.arraydescr
        if len(self.items) != exitnode.arraysize:
            # the size is known to be a mismatch
            return False
        #
        d = exitnode.curitems
        for i in range(exitnode.arraysize):
            try:
                if d is None:
                    raise KeyError
                itemnode = d[i]
            except KeyError:
                itemnode = NodeFinder.node_escaped
            subspecnode = self.items[i]
            if not subspecnode.matches_instance_node(itemnode):
                return False
        return True

class __extend__(VirtualStructSpecNode):
    def make_instance_node(self):
        raise AssertionError, "not implemented (but not used actually)"
    def matches_instance_node(self, exitnode):
        if exitnode.unique == UNIQUE_NO:
            return False
        #
        assert exitnode.unique == UNIQUE_STRUCT
        assert self.typedescr == exitnode.structdescr
        #
        return matches_fields(self.fields, exitnode.curfields)


class BridgeSpecializationFinder(NodeFinder):

    def find_nodes_bridge(self, bridge, specnodes=None):
        if specnodes is not None:      # not used actually
            self.setup_bridge_input_nodes(specnodes, bridge.inputargs)
        self.find_nodes(bridge.operations)
        self.jump_op = bridge.operations[-1]

    def setup_bridge_input_nodes(self, specnodes, inputargs):
        assert len(specnodes) == len(inputargs)
        for i in range(len(inputargs)):
            instnode = specnodes[i].make_instance_node()
            box = inputargs[i]
            self.nodes[box] = instnode

    def bridge_matches(self, nextloop_specnodes):
        jump_op = self.jump_op
        assert len(jump_op.args) == len(nextloop_specnodes)
        for i in range(len(nextloop_specnodes)):
            exitnode = self.getnode(jump_op.args[i])
            if not nextloop_specnodes[i].matches_instance_node(exitnode):
                return False
        return True
