import py, random

from pypy.rpython.lltypesystem import lltype, llmemory, rclass
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.lltypesystem.rclass import OBJECT, OBJECT_VTABLE

from pypy.jit.backend.llgraph import runner
from pypy.jit.metainterp.history import (BoxInt, BoxPtr, ConstInt, ConstPtr,
                                         Const, ConstAddr, TreeLoop, BoxObj,
                                         ConstObj, AbstractDescr)
from pypy.jit.metainterp.optimizefindnode import PerfectSpecializationFinder
from pypy.jit.metainterp.optimizefindnode import BridgeSpecializationFinder
from pypy.jit.metainterp.optimizeutil import sort_descrs, InvalidLoop
from pypy.jit.metainterp.specnode import NotSpecNode, prebuiltNotSpecNode
from pypy.jit.metainterp.specnode import VirtualInstanceSpecNode
from pypy.jit.metainterp.specnode import VirtualArraySpecNode
from pypy.jit.metainterp.specnode import VirtualStructSpecNode
from pypy.jit.metainterp.specnode import ConstantSpecNode
from pypy.jit.metainterp.effectinfo import EffectInfo
from pypy.jit.metainterp.test.oparser import parse

def test_sort_descrs():
    class PseudoDescr(AbstractDescr):
        def __init__(self, n):
            self.n = n
        def sort_key(self):
            return self.n
    for i in range(17):
        lst = [PseudoDescr(j) for j in range(i)]
        lst2 = lst[:]
        random.shuffle(lst2)
        sort_descrs(lst2)
        assert lst2 == lst

# ____________________________________________________________

class LLtypeMixin(object):
    type_system = 'lltype'

    def get_class_of_box(self, box):
        return box.getref(rclass.OBJECTPTR).typeptr

    node_vtable = lltype.malloc(OBJECT_VTABLE, immortal=True)
    node_vtable.name = rclass.alloc_array_name('node')
    node_vtable_adr = llmemory.cast_ptr_to_adr(node_vtable)
    node_vtable2 = lltype.malloc(OBJECT_VTABLE, immortal=True)
    node_vtable2.name = rclass.alloc_array_name('node2')
    node_vtable_adr2 = llmemory.cast_ptr_to_adr(node_vtable2)
    cpu = runner.LLtypeCPU(None)

    NODE = lltype.GcForwardReference()
    NODE.become(lltype.GcStruct('NODE', ('parent', OBJECT),
                                        ('value', lltype.Signed),
                                        ('floatval', lltype.Float),
                                        ('next', lltype.Ptr(NODE))))
    NODE2 = lltype.GcStruct('NODE2', ('parent', NODE),
                                     ('other', lltype.Ptr(NODE)))
    node = lltype.malloc(NODE)
    node.parent.typeptr = node_vtable
    nodebox = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, node))
    myptr = nodebox.value
    myptr2 = lltype.cast_opaque_ptr(llmemory.GCREF, lltype.malloc(NODE))
    nodebox2 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, node))
    nodesize = cpu.sizeof(NODE)
    nodesize2 = cpu.sizeof(NODE2)
    valuedescr = cpu.fielddescrof(NODE, 'value')
    floatdescr = cpu.fielddescrof(NODE, 'floatval')
    nextdescr = cpu.fielddescrof(NODE, 'next')
    otherdescr = cpu.fielddescrof(NODE2, 'other')

    NODEOBJ = lltype.GcStruct('NODEOBJ', ('parent', OBJECT),
                                         ('ref', lltype.Ptr(OBJECT)))
    nodeobj = lltype.malloc(NODEOBJ)
    nodeobjvalue = lltype.cast_opaque_ptr(llmemory.GCREF, nodeobj)
    refdescr = cpu.fielddescrof(NODEOBJ, 'ref')

    arraydescr = cpu.arraydescrof(lltype.GcArray(lltype.Signed))
    floatarraydescr = cpu.arraydescrof(lltype.GcArray(lltype.Float))

    # a GcStruct not inheriting from OBJECT
    S = lltype.GcStruct('TUPLE', ('a', lltype.Signed), ('b', lltype.Ptr(NODE)))
    ssize = cpu.sizeof(S)
    adescr = cpu.fielddescrof(S, 'a')
    bdescr = cpu.fielddescrof(S, 'b')
    sbox = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, lltype.malloc(S)))
    arraydescr2 = cpu.arraydescrof(lltype.GcArray(lltype.Ptr(S)))

    T = lltype.GcStruct('TUPLE',
                        ('c', lltype.Signed),
                        ('d', lltype.Ptr(lltype.GcArray(lltype.Ptr(NODE)))))
    tsize = cpu.sizeof(T)
    cdescr = cpu.fielddescrof(T, 'c')
    ddescr = cpu.fielddescrof(T, 'd')
    arraydescr3 = cpu.arraydescrof(lltype.GcArray(lltype.Ptr(NODE)))

    U = lltype.GcStruct('U',
                        ('parent', OBJECT),
                        ('one', lltype.Ptr(lltype.GcArray(lltype.Ptr(NODE)))))
    u_vtable = lltype.malloc(OBJECT_VTABLE, immortal=True)
    u_vtable_adr = llmemory.cast_ptr_to_adr(u_vtable)
    usize = cpu.sizeof(U)
    onedescr = cpu.fielddescrof(U, 'one')

    FUNC = lltype.FuncType([lltype.Signed], lltype.Signed)
    plaincalldescr = cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT)
    nonwritedescr = cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT,
                                    EffectInfo([], [], []))
    writeadescr = cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT,
                                  EffectInfo([], [adescr], []))
    writearraydescr = cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT,
                                      EffectInfo([], [adescr], [arraydescr]))
    readadescr = cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT,
                                 EffectInfo([adescr], [], []))
    mayforcevirtdescr = cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT,
                 EffectInfo([nextdescr], [], [],
                            forces_virtual_or_virtualizable=True))
    class LoopToken(AbstractDescr):
        pass
    asmdescr = LoopToken() # it can be whatever, it's not a descr though

    from pypy.jit.metainterp.virtualref import VirtualRefInfo
    class FakeWarmRunnerDesc:
        pass
    FakeWarmRunnerDesc.cpu = cpu
    vrefinfo = VirtualRefInfo(FakeWarmRunnerDesc)
    virtualtokendescr = vrefinfo.descr_virtual_token
    virtualrefindexdescr = vrefinfo.descr_virtualref_index
    virtualforceddescr = vrefinfo.descr_forced
    jit_virtual_ref_vtable = vrefinfo.jit_virtual_ref_vtable
    jvr_vtable_adr = llmemory.cast_ptr_to_adr(jit_virtual_ref_vtable)

    cpu.class_sizes = {
        cpu.cast_adr_to_int(node_vtable_adr): cpu.sizeof(NODE),
        cpu.cast_adr_to_int(node_vtable_adr2): cpu.sizeof(NODE2),
        cpu.cast_adr_to_int(u_vtable_adr): cpu.sizeof(U),
        cpu.cast_adr_to_int(jvr_vtable_adr): cpu.sizeof(
                                                   vrefinfo.JIT_VIRTUAL_REF),
        }
    namespace = locals()

class OOtypeMixin(object):
    type_system = 'ootype'

    def get_class_of_box(self, box):
        root = box.getref(ootype.ROOT)
        return ootype.classof(root)
    
    cpu = runner.OOtypeCPU(None)
    NODE = ootype.Instance('NODE', ootype.ROOT, {})
    NODE._add_fields({'value': ootype.Signed,
                      'floatval' : ootype.Float,
                      'next': NODE})
    NODE2 = ootype.Instance('NODE2', NODE, {'other': NODE})

    node_vtable = ootype.runtimeClass(NODE)
    node_vtable_adr = ootype.cast_to_object(node_vtable)
    node_vtable2 = ootype.runtimeClass(NODE2)
    node_vtable_adr2 = ootype.cast_to_object(node_vtable2)

    node = ootype.new(NODE)
    nodebox = BoxObj(ootype.cast_to_object(node))
    myptr = nodebox.value
    myptr2 = ootype.cast_to_object(ootype.new(NODE))
    nodebox2 = BoxObj(ootype.cast_to_object(node))
    valuedescr = cpu.fielddescrof(NODE, 'value')
    floatdescr = cpu.fielddescrof(NODE, 'floatval')
    nextdescr = cpu.fielddescrof(NODE, 'next')
    otherdescr = cpu.fielddescrof(NODE2, 'other')
    nodesize = cpu.typedescrof(NODE)
    nodesize2 = cpu.typedescrof(NODE2)

    arraydescr = cpu.arraydescrof(ootype.Array(ootype.Signed))
    floatarraydescr = cpu.arraydescrof(ootype.Array(ootype.Float))

    # a plain Record
    S = ootype.Record({'a': ootype.Signed, 'b': NODE})
    ssize = cpu.typedescrof(S)
    adescr = cpu.fielddescrof(S, 'a')
    bdescr = cpu.fielddescrof(S, 'b')
    sbox = BoxObj(ootype.cast_to_object(ootype.new(S)))
    arraydescr2 = cpu.arraydescrof(ootype.Array(S))

    T = ootype.Record({'c': ootype.Signed,
                       'd': ootype.Array(NODE)})
    tsize = cpu.typedescrof(T)
    cdescr = cpu.fielddescrof(T, 'c')
    ddescr = cpu.fielddescrof(T, 'd')
    arraydescr3 = cpu.arraydescrof(ootype.Array(NODE))

    U = ootype.Instance('U', ootype.ROOT, {'one': ootype.Array(NODE)})
    usize = cpu.typedescrof(U)
    onedescr = cpu.fielddescrof(U, 'one')
    u_vtable = ootype.runtimeClass(U)
    u_vtable_adr = ootype.cast_to_object(u_vtable)

    # force a consistent order
    valuedescr.sort_key()
    nextdescr.sort_key()
    adescr.sort_key()
    bdescr.sort_key()

    FUNC = lltype.FuncType([lltype.Signed], lltype.Signed)
    nonwritedescr = cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT) # XXX fix ootype

    cpu.class_sizes = {node_vtable_adr: cpu.typedescrof(NODE),
                       node_vtable_adr2: cpu.typedescrof(NODE2),
                       u_vtable_adr: cpu.typedescrof(U)}
    namespace = locals()

class BaseTest(object):
    invent_fail_descr = None

    def parse(self, s, boxkinds=None):
        return parse(s, self.cpu, self.namespace,
                     type_system=self.type_system,
                     boxkinds=boxkinds,
                     invent_fail_descr=self.invent_fail_descr)

    def unpack_specnodes(self, text):
        #
        def constclass(cls_vtable):
            if self.type_system == 'lltype':
                return ConstAddr(llmemory.cast_ptr_to_adr(cls_vtable),
                                 self.cpu)
            else:
                return ConstObj(ootype.cast_to_object(cls_vtable))
        def constant(value):
            if isinstance(lltype.typeOf(value), lltype.Ptr):
                return ConstPtr(value)
            elif isinstance(ootype.typeOf(value), ootype.OOType):
                return ConstObj(ootype.cast_to_object(value))
            else:
                return ConstInt(value)

        def parsefields(kwds_fields):
            fields = []
            for key, value in kwds_fields.items():
                fields.append((self.namespace[key], value))
            fields.sort(key = lambda (x, _): x.sort_key())
            return fields
        def makeConstant(value):
            return ConstantSpecNode(constant(value))
        def makeVirtual(cls_vtable, **kwds_fields):
            fields = parsefields(kwds_fields)
            return VirtualInstanceSpecNode(constclass(cls_vtable), fields)
        def makeVirtualArray(arraydescr, *items):
            return VirtualArraySpecNode(arraydescr, items)
        def makeVirtualStruct(typedescr, **kwds_fields):
            fields = parsefields(kwds_fields)
            return VirtualStructSpecNode(typedescr, fields)
        #
        context = {'Not': prebuiltNotSpecNode,
                   'Constant': makeConstant,
                   'Virtual': makeVirtual,
                   'VArray': makeVirtualArray,
                   'VStruct': makeVirtualStruct}
        lst = eval('[' + text + ']', self.namespace, context)
        return lst

    def check_specnodes(self, specnodes, text):
        lst = self.unpack_specnodes(text)
        assert len(specnodes) == len(lst)
        for x, y in zip(specnodes, lst):
            assert x.equals(y, ge=False)
        return True

# ____________________________________________________________

class BaseTestOptimizeFindNode(BaseTest):

    def find_nodes(self, ops, spectext, boxkinds=None):
        assert boxkinds is None or isinstance(boxkinds, dict)
        loop = self.parse(ops, boxkinds=boxkinds)
        perfect_specialization_finder = PerfectSpecializationFinder(self.cpu)
        perfect_specialization_finder.find_nodes_loop(loop)
        self.check_specnodes(loop.token.specnodes, spectext)
        return (loop.getboxes(), perfect_specialization_finder.getnode)

    def test_find_nodes_simple(self):
        ops = """
        [i]
        i0 = int_sub(i, 1)
        guard_value(i0, 0) [i0]
        jump(i0)
        """
        boxes, getnode = self.find_nodes(ops, 'Not')
        assert getnode(boxes.i).fromstart
        assert not getnode(boxes.i0).fromstart

    def test_find_nodes_non_escape(self):
        ops = """
        [p0]
        p1 = getfield_gc(p0, descr=nextdescr)
        i0 = getfield_gc(p1, descr=valuedescr)
        i1 = int_sub(i0, 1)
        p2 = getfield_gc(p0, descr=nextdescr)
        setfield_gc(p2, i1, descr=valuedescr)
        p3 = new_with_vtable(ConstClass(node_vtable))
        jump(p3)
        """
        boxes, getnode = self.find_nodes(ops,
                                         'Virtual(node_vtable, nextdescr=Not)')
        assert not getnode(boxes.p0).escaped
        assert not getnode(boxes.p1).escaped
        assert not getnode(boxes.p2).escaped
        assert getnode(boxes.p0).fromstart
        assert getnode(boxes.p1).fromstart
        assert getnode(boxes.p2).fromstart

    def test_find_nodes_escape(self):
        ops = """
        [p0]
        p1 = getfield_gc(p0, descr=nextdescr)
        p2 = getfield_gc(p1, descr=nextdescr)
        i0 = getfield_gc(p2, descr=valuedescr)
        i1 = int_sub(i0, 1)
        escape(p1)
        p3 = getfield_gc(p0, descr=nextdescr)
        setfield_gc(p3, i1, descr=valuedescr)
        p4 = getfield_gc(p1, descr=nextdescr)
        setfield_gc(p4, i1, descr=valuedescr)
        p5 = new_with_vtable(ConstClass(node_vtable))
        jump(p5)
        """
        boxes, getnode = self.find_nodes(ops,
                                         'Virtual(node_vtable, nextdescr=Not)')
        assert not getnode(boxes.p0).escaped
        assert getnode(boxes.p1).escaped
        assert getnode(boxes.p2).escaped    # forced by p1
        assert getnode(boxes.p3).escaped    # forced because p3 == p1
        assert getnode(boxes.p4).escaped    # forced by p1
        assert getnode(boxes.p0).fromstart
        assert getnode(boxes.p1).fromstart
        assert getnode(boxes.p2).fromstart
        assert getnode(boxes.p3).fromstart
        assert not getnode(boxes.p4).fromstart

    def test_find_nodes_new_1(self):
        ops = """
        [p1]
        p2 = new_with_vtable(ConstClass(node_vtable))
        jump(p2)
        """
        boxes, getnode = self.find_nodes(ops, 'Virtual(node_vtable)')

        boxp1 = getnode(boxes.p1)
        boxp2 = getnode(boxes.p2)
        assert not boxp1.escaped
        assert not boxp2.escaped

        assert not boxp1.origfields
        assert not boxp1.curfields
        assert not boxp2.origfields
        assert not boxp2.curfields

        assert boxp1.fromstart
        assert not boxp2.fromstart

        assert boxp1.knownclsbox is None
        assert boxp2.knownclsbox.value == self.node_vtable_adr

    def test_find_nodes_new_2(self):
        ops = """
        [i1, p1]
        p2 = new_with_vtable(ConstClass(node_vtable))
        p3 = new_with_vtable(ConstClass(node_vtable2))
        setfield_gc(p2, p3, descr=nextdescr)
        setfield_gc(p3, i1, descr=valuedescr)
        jump(i1, p2)
        """
        self.find_nodes(ops,
            '''Not,
               Virtual(node_vtable,
                       nextdescr=Virtual(node_vtable2,
                                         valuedescr=Not))''')

    def test_find_nodes_new_3(self):
        ops = """
        [sum, p1]
        guard_class(p1, ConstClass(node_vtable)) []
        i1 = getfield_gc(p1, descr=valuedescr)
        i2 = int_sub(i1, 1)
        sum2 = int_add(sum, i1)
        p2 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p2, i2, descr=valuedescr)
        p3 = new_with_vtable(ConstClass(node_vtable2))
        setfield_gc(p2, p3, descr=nextdescr)
        jump(sum2, p2)
        """
        boxes, getnode = self.find_nodes(
            ops,
            '''Not,
               Virtual(node_vtable,
                       valuedescr=Not,
                       nextdescr=Virtual(node_vtable2))''',
            boxkinds={'sum': BoxInt, 'sum2': BoxInt})
        assert getnode(boxes.sum) is not getnode(boxes.sum2)
        assert getnode(boxes.p1) is not getnode(boxes.p2)

        boxp1 = getnode(boxes.p1)
        boxp2 = getnode(boxes.p2)
        boxp3 = getnode(boxes.p3)
        assert not boxp1.escaped
        assert not boxp2.escaped
        assert not boxp3.escaped

        assert not boxp1.curfields
        assert boxp1.origfields[self.valuedescr] is getnode(boxes.i1)
        assert not boxp2.origfields
        assert boxp2.curfields[self.nextdescr] is boxp3

        assert boxp1.fromstart
        assert not boxp2.fromstart
        assert not boxp3.fromstart

        assert boxp2.knownclsbox.value == self.node_vtable_adr
        assert boxp3.knownclsbox.value == self.node_vtable_adr2

    def test_find_nodes_new_aliasing_0(self):
        ops = """
        [p1, p2]
        p3 = new_with_vtable(ConstClass(node_vtable))
        jump(p3, p3)
        """
        # both p1 and p2 must be NotSpecNodes; it's not possible to pass
        # the same Virtual both in p1 and p2 (at least so far).
        self.find_nodes(ops, 'Not, Not')

    def test_find_nodes_new_aliasing_1(self):
        ops = """
        [sum, p1]
        guard_class(p1, ConstClass(node_vtable)) []
        p3 = getfield_gc(p1, descr=nextdescr)
        guard_class(p3, ConstClass(node_vtable)) []
        i1 = getfield_gc(p1, descr=valuedescr)
        i2 = int_sub(i1, 1)
        sum2 = int_add(sum, i1)
        p2 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p2, i2, descr=valuedescr)
        setfield_gc(p2, p2, descr=nextdescr)
        jump(sum2, p2)
        """
        # the issue is the cycle "p2->p2", which cannot be represented
        # with SpecNodes so far
        self.find_nodes(ops, 'Not, Not',
                        boxkinds={'sum': BoxInt, 'sum2': BoxInt})

    def test_find_nodes_new_aliasing_2(self):
        ops = """
        [p1, p2]
        escape(p2)
        p3 = new_with_vtable(ConstClass(node_vtable))
        jump(p3, p3)
        """
        # both p1 and p2 must be NotSpecNodes; it's not possible to pass
        # in p1 a Virtual and not in p2, as they both come from the same p3.
        self.find_nodes(ops, 'Not, Not')

    def test_find_nodes_new_mismatch(self):
        ops = """
        [p1]
        guard_class(p1, ConstClass(node_vtable)) []
        p2 = new_with_vtable(ConstClass(node_vtable2))
        jump(p2)
        """
        # this is not a valid loop at all, because of the mismatch
        # between the produced and the consumed class.
        py.test.raises(InvalidLoop, self.find_nodes, ops, None)

    def test_find_nodes_new_aliasing_mismatch(self):
        ops = """
        [p0, p1]
        guard_class(p0, ConstClass(node_vtable)) []
        guard_class(p1, ConstClass(node_vtable2)) []
        p2 = new_with_vtable(ConstClass(node_vtable2))
        jump(p2, p2)
        """
        # this is also not really a valid loop, but it's not detected
        # because p2 is passed more than once in the jump().
        self.find_nodes(ops, 'Not, Not')

    def test_find_nodes_new_escapes(self):
        ops = """
        [p0]
        escape(p0)
        p1 = new_with_vtable(ConstClass(node_vtable))
        jump(p1)
        """
        self.find_nodes(ops, 'Not')

    def test_find_nodes_new_unused(self):
        ops = """
        [p0]
        p1 = new_with_vtable(ConstClass(node_vtable))
        p2 = new_with_vtable(ConstClass(node_vtable))
        p3 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p1, p2, descr=nextdescr)
        setfield_gc(p2, p3, descr=nextdescr)
        jump(p1)
        """
        self.find_nodes(ops, '''
            Virtual(node_vtable,
                    nextdescr=Virtual(node_vtable,
                                      nextdescr=Virtual(node_vtable)))''')

    def test_find_nodes_oois(self):
        ops = """
        [p3, p4, p2]
        p0 = new_with_vtable(ConstClass(node_vtable))
        p1 = new_with_vtable(ConstClass(node_vtable))
        guard_nonnull(p0) []
        i3 = ooisnot(p0, NULL)
        guard_true(i3) []
        i4 = oois(p0, NULL)
        guard_false(i4) []
        i5 = ooisnot(NULL, p0)
        guard_true(i5) []
        i6 = oois(NULL, p0)
        guard_false(i6) []
        i7 = ooisnot(p0, p1)
        guard_true(i7) []
        i8 = oois(p0, p1)
        guard_false(i8) []
        i9 = ooisnot(p0, p2)
        guard_true(i9) []
        i10 = oois(p0, p2)
        guard_false(i10) []
        i11 = ooisnot(p2, p1)
        guard_true(i11) []
        i12 = oois(p2, p1)
        guard_false(i12) []
        jump(p0, p1, p2)
        """
        self.find_nodes(ops, '''Virtual(node_vtable),
                                Virtual(node_vtable),
                                Not''')

    def test_find_nodes_call(self):
        ops = """
        [i0, p2]
        p0 = new_with_vtable(ConstClass(node_vtable))
        i1 = call_pure(i0, p0)     # forces p0 to not be virtual
        jump(i1, p0)
        """
        self.find_nodes(ops, 'Not, Not')

    def test_find_nodes_default_field(self):
        ops = """
        [p0]
        i0 = getfield_gc(p0, descr=valuedescr)
        guard_value(i0, 5) []
        p1 = new_with_vtable(ConstClass(node_vtable))
        # the field 'value' has its default value of 0
        jump(p1)
        """
        # The answer must contain the 'value' field, because otherwise
        # we might get incorrect results: when tracing, i0 was 5.
        self.find_nodes(ops, 'Virtual(node_vtable, valuedescr=Not)')

    def test_find_nodes_nonvirtual_guard_class(self):
        ops = """
        [p1]
        guard_class(p1, ConstClass(node_vtable)) [p1]
        jump(p1)
        """
        self.find_nodes(ops, 'Not')

    def test_find_nodes_p12_simple(self):
        ops = """
        [p1]
        i3 = getfield_gc(p1, descr=valuedescr)
        escape(i3)
        jump(p1)
        """
        self.find_nodes(ops, 'Not')

    def test_find_nodes_p123_simple(self):
        ops = """
        [i1, p2, p3]
        i3 = getfield_gc(p3, descr=valuedescr)
        escape(i3)
        p1 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p1, i1, descr=valuedescr)
        jump(i1, p1, p2)
        """
        # We cannot track virtuals that survive for more than two iterations.
        self.find_nodes(ops, 'Not, Not, Not')

    def test_find_nodes_p1234_simple(self):
        ops = """
        [i1, p2, p3, p4]
        i4 = getfield_gc(p4, descr=valuedescr)
        escape(i4)
        p1 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p1, i1, descr=valuedescr)
        jump(i1, p1, p2, p3)
        """
        # We cannot track virtuals that survive for more than two iterations.
        self.find_nodes(ops, 'Not, Not, Not, Not')

    def test_find_nodes_p123_guard_class(self):
        ops = """
        [i1, p2, p3]
        guard_class(p3, ConstClass(node_vtable)) [i1, p2, p3]
        i3 = getfield_gc(p3, descr=valuedescr)
        escape(i3)
        p1 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p1, i1, descr=valuedescr)
        jump(i1, p1, p2)
        """
        # We cannot track virtuals that survive for more than two iterations.
        self.find_nodes(ops, 'Not, Not, Not')

    def test_find_nodes_p123_rec(self):
        ops = """
        [i1, p2, p0d]
        p3 = getfield_gc(p0d, descr=nextdescr)
        i3 = getfield_gc(p3, descr=valuedescr)
        escape(i3)
        p1 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p1, i1, descr=valuedescr)
        p0c = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p0c, p2, descr=nextdescr)
        jump(i1, p1, p0c)
        """
        # We cannot track virtuals that survive for more than two iterations.
        self.find_nodes(ops, '''Not,
                                Not,
                                Virtual(node_vtable, nextdescr=Not)''')

    def test_find_nodes_setfield_bug(self):
        ops = """
        [p1, p2]
        escape(p1)
        setfield_gc(p1, p2, descr=nextdescr)
        p3 = new_with_vtable(ConstClass(node_vtable))
        jump(p1, p3)
        """
        self.find_nodes(ops, 'Not, Not')

    def test_find_nodes_array_virtual_1(self):
        ops = """
        [i1, p2]
        i2 = getarrayitem_gc(p2, 1, descr=arraydescr)
        escape(i2)
        p3 = new_array(3, descr=arraydescr)
        setarrayitem_gc(p3, 1, i1, descr=arraydescr)
        jump(i1, p3)
        """
        self.find_nodes(ops, 'Not, VArray(arraydescr, Not, Not, Not)')

    def test_find_nodes_array_virtual_2(self):
        ops = """
        [i1, p2]
        i2 = arraylen_gc(p2, descr=arraydescr)
        escape(i2)
        p3 = new_array(3, descr=arraydescr)
        setarrayitem_gc(p3, 1, i1, descr=arraydescr)
        jump(i1, p3)
        """
        self.find_nodes(ops, 'Not, VArray(arraydescr, Not, Not, Not)')

    def test_find_nodes_array_virtual_3(self):
        ops = """
        [pvalue1, p2]
        pvalue2 = new_with_vtable(ConstClass(node_vtable2))
        ps2 = getarrayitem_gc(p2, 1, descr=arraydescr)
        setfield_gc(ps2, pvalue2, descr=nextdescr)
        ps3 = getarrayitem_gc(p2, 1, descr=arraydescr)
        pvalue3 = getfield_gc(ps3, descr=nextdescr)
        ps1 = new_with_vtable(ConstClass(node_vtable))
        p3 = new_array(3, descr=arraydescr)
        setarrayitem_gc(p3, 1, ps1, descr=arraydescr)
        jump(pvalue3, p3)
        """
        self.find_nodes(ops, 'Virtual(node_vtable2), VArray(arraydescr, Not, Virtual(node_vtable), Not)')

    def test_find_nodes_array_virtual_empty(self):
        ops = """
        [i1, p2]
        p3 = new_array(3, descr=arraydescr)
        jump(i1, p3)
        """
        self.find_nodes(ops, 'Not, VArray(arraydescr, Not, Not, Not)')

    def test_find_nodes_array_nonvirtual_1(self):
        ops = """
        [i1, p2]
        i2 = getarrayitem_gc(p2, i1, descr=arraydescr)
        escape(i2)
        p3 = new_array(4, descr=arraydescr)
        setarrayitem_gc(p3, i1, i2, descr=arraydescr)
        jump(i1, p3)
        """
        # Does not work because of the variable index, 'i1'.
        self.find_nodes(ops, 'Not, Not')

    def test_find_nodes_array_forced_1(self):
        ops = """
        [p1, i1]
        p2 = new_array(1, descr=arraydescr)
        setarrayitem_gc(p2, 0, p1, descr=arraydescr)
        p3 = getarrayitem_gc(p2, i1, descr=arraydescr)
        p4 = new_with_vtable(ConstClass(node_vtable))
        jump(p4, i1)
        """
        # escapes because getarrayitem_gc uses a non-constant index
        self.find_nodes(ops, 'Not, Not')

    def test_find_nodes_arrayitem_forced(self):
        ops = """
        [p1]
        p2 = new_array(1, descr=arraydescr)
        escape(p2)
        p4 = new_with_vtable(ConstClass(node_vtable))
        setarrayitem_gc(p2, 0, p4, descr=arraydescr)
        jump(p4)
        """
        self.find_nodes(ops, 'Not')

    def test_find_nodes_struct_virtual_1(self):
        ops = """
        [i1, p2]
        i2 = getfield_gc(p2, descr=adescr)
        escape(i2)
        p3 = new(descr=ssize)
        setfield_gc(p3, i1, descr=adescr)
        jump(i1, p3)
        """
        self.find_nodes(ops, 'Not, VStruct(ssize, adescr=Not)')

    def test_find_nodes_struct_nonvirtual_1(self):
        ops = """
        [i1, p2]
        i2 = getfield_gc(p2, descr=adescr)
        escape(p2)
        p3 = new(descr=ssize)
        setfield_gc(p3, i1, descr=adescr)
        jump(i1, p3)
        """
        self.find_nodes(ops, 'Not, Not')

    def test_find_nodes_guard_value_constant(self):
        ops = """
        [p1]
        guard_value(p1, ConstPtr(myptr)) []
        jump(ConstPtr(myptr))
        """
        self.find_nodes(ops, 'Constant(myptr)')

    def test_find_nodes_guard_value_constant_mismatch(self):
        ops = """
        [p1]
        guard_value(p1, ConstPtr(myptr2)) []
        jump(ConstPtr(myptr))
        """
        py.test.raises(InvalidLoop, self.find_nodes, ops, None)

    def test_find_nodes_guard_value_escaping_constant(self):
        ops = """
        [p1]
        escape(p1)
        guard_value(p1, ConstPtr(myptr)) []
        jump(ConstPtr(myptr))
        """
        self.find_nodes(ops, 'Constant(myptr)')

    def test_find_nodes_guard_value_same_as_constant(self):
        ops = """
        [p1]
        guard_value(p1, ConstPtr(myptr)) []
        p2 = same_as(ConstPtr(myptr))
        jump(p2)
        """
        self.find_nodes(ops, 'Constant(myptr)')

    def test_find_nodes_store_into_loop_constant_1(self):
        ops = """
        [i0, p1, p4]
        p2 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p1, p2, descr=nextdescr)
        jump(i0, p1, p2)
        """
        self.find_nodes(ops, 'Not, Not, Not')

    def test_find_nodes_store_into_loop_constant_2(self):
        ops = """
        [i0, p4, p1]
        p2 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p1, p2, descr=nextdescr)
        jump(i0, p2, p1)
        """
        self.find_nodes(ops, 'Not, Not, Not')

    def test_find_nodes_store_into_loop_constant_3(self):
        ops = """
        [i0, p1]
        p2 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p1, p2, descr=nextdescr)
        call(i0)
        jump(i0, p1)
        """
        self.find_nodes(ops, 'Not, Not')

    def test_find_nodes_arithmetic_propagation_bug_0(self):
        ops = """
        [p1]
        i1 = getarrayitem_gc(p1, 0, descr=arraydescr)
        escape(i1)
        i2 = int_add(0, 1)
        p2 = new_array(i2, descr=arraydescr)
        i3 = escape()
        setarrayitem_gc(p2, 0, i3, descr=arraydescr)
        jump(p2)
        """
        self.find_nodes(ops, 'VArray(arraydescr, Not)')

    def test_find_nodes_arithmetic_propagation_bug_1(self):
        ops = """
        [p1]
        i1 = getarrayitem_gc(p1, 0, descr=arraydescr)
        escape(i1)
        i2 = same_as(1)
        p2 = new_array(i2, descr=arraydescr)
        setarrayitem_gc(p2, 0, 5)
        jump(p2)
        """
        self.find_nodes(ops, 'VArray(arraydescr, Not)')

    def test_find_nodes_arithmetic_propagation_bug_2(self):
        ops = """
        [p1]
        i0 = int_sub(17, 17)
        i1 = getarrayitem_gc(p1, i0, descr=arraydescr)
        escape(i1)
        i2 = int_add(0, 1)
        p2 = new_array(i2, descr=arraydescr)
        i3 = escape()
        setarrayitem_gc(p2, i0, i3, descr=arraydescr)
        jump(p2)
        """
        self.find_nodes(ops, 'VArray(arraydescr, Not)')

    def test_find_nodes_arithmetic_propagation_bug_3(self):
        ops = """
        [p1]
        i1 = getarrayitem_gc(p1, 0, descr=arraydescr)
        escape(i1)
        p3 = new_array(1, descr=arraydescr)
        i2 = arraylen_gc(p3, descr=arraydescr)
        p2 = new_array(i2, descr=arraydescr)
        i3 = escape()
        setarrayitem_gc(p2, 0, i3, descr=arraydescr)
        jump(p2)
        """
        self.find_nodes(ops, 'VArray(arraydescr, Not)')

    def test_find_nodes_bug_1(self):
        ops = """
        [p12]
        guard_nonnull(p12) []
        guard_class(p12, ConstClass(node_vtable)) []
        guard_class(p12, ConstClass(node_vtable)) []
        i22 = getfield_gc_pure(p12, descr=valuedescr)
        escape(i22)
        guard_nonnull(p12) []
        guard_class(p12, ConstClass(node_vtable)) []
        guard_class(p12, ConstClass(node_vtable)) []
        i29 = getfield_gc_pure(p12, descr=valuedescr)
        i31 = int_add_ovf(i29, 1)
        guard_no_overflow() []
        p33 = new_with_vtable(ConstClass(node_vtable))      # NODE
        setfield_gc(p33, i31, descr=valuedescr)
        #
        p35 = new_array(1, descr=arraydescr3)               # Array(NODE)
        setarrayitem_gc(p35, 0, p33, descr=arraydescr3)
        p38 = new_with_vtable(ConstClass(u_vtable))         # U
        setfield_gc(p38, p35, descr=onedescr)
        guard_nonnull(p38) []
        guard_nonnull(p38) []
        guard_class(p38, ConstClass(u_vtable)) []
        p42 = getfield_gc(p38, descr=onedescr)              # Array(NODE)
        i43 = arraylen_gc(p42, descr=arraydescr3)
        i45 = int_sub(i43, 0)
        p46 = new(descr=tsize)                              # T
        setfield_gc(p46, i45, descr=cdescr)
        p47 = new_array(i45, descr=arraydescr3)             # Array(NODE)
        setfield_gc(p46, p47, descr=ddescr)
        i48 = int_lt(0, i43)
        guard_true(i48) []
        p49 = getarrayitem_gc(p42, 0, descr=arraydescr3)    # NODE
        p50 = getfield_gc(p46, descr=ddescr)                # Array(NODE)
        setarrayitem_gc(p50, 0, p49, descr=arraydescr3)
        i52 = int_lt(1, i43)
        guard_false(i52) []
        i53 = getfield_gc(p46, descr=cdescr)
        i55 = int_ne(i53, 1)
        guard_false(i55) []
        p56 = getfield_gc(p46, descr=ddescr)                # Array(NODE)
        p58 = getarrayitem_gc(p56, 0, descr=arraydescr3)    # NODE
        guard_nonnull(p38) []
        jump(p58)
        """
        self.find_nodes(ops, 'Virtual(node_vtable, valuedescr=Not)')

    # ------------------------------
    # Bridge tests

    def find_bridge(self, ops, inputspectext, outputspectext, boxkinds=None,
                    mismatch=False):
        assert boxkinds is None or isinstance(boxkinds, dict)
        inputspecnodes = self.unpack_specnodes(inputspectext)
        outputspecnodes = self.unpack_specnodes(outputspectext)
        bridge = self.parse(ops, boxkinds=boxkinds)
        bridge_specialization_finder = BridgeSpecializationFinder(self.cpu)
        bridge_specialization_finder.find_nodes_bridge(bridge, inputspecnodes)
        matches = bridge_specialization_finder.bridge_matches(outputspecnodes)
        if mismatch:
            assert not matches
        else:
            assert matches

    def test_bridge_simple(self):
        ops = """
        [i0]
        i1 = int_add(i0, 1)
        jump(i1)
        """
        self.find_bridge(ops, 'Not', 'Not')
        self.find_bridge(ops, 'Not', 'Virtual(node_vtable)', mismatch=True)

    def test_bridge_simple_known_class(self):
        ops = """
        [p0]
        setfield_gc(p0, 123, descr=valuedescr)
        jump(p0)
        """
        self.find_bridge(ops, 'Not', 'Not')

    def test_bridge_simple_constant(self):
        ops = """
        []
        jump(ConstPtr(myptr))
        """
        self.find_bridge(ops, '', 'Not')
        self.find_bridge(ops, '', 'Constant(myptr)')
        self.find_bridge(ops, '', 'Constant(myptr2)', mismatch=True)

    def test_bridge_simple_constant_mismatch(self):
        ops = """
        [p0]
        jump(p0)
        """
        self.find_bridge(ops, 'Not', 'Not')
        self.find_bridge(ops, 'Not', 'Constant(myptr)', mismatch=True)

    def test_bridge_simple_virtual_1(self):
        ops = """
        [i0]
        p0 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p0, i0, descr=valuedescr)
        jump(p0)
        """
        self.find_bridge(ops, 'Not', 'Not')
        self.find_bridge(ops, 'Not', 'Virtual(node_vtable, valuedescr=Not)')
        self.find_bridge(ops, 'Not',
                         '''Virtual(node_vtable,
                                    valuedescr=Not,
                                    nextdescr=Not)''')
        #
        self.find_bridge(ops, 'Not', 'Virtual(node_vtable)',
                         mismatch=True)   # missing valuedescr
        self.find_bridge(ops, 'Not', 'Virtual(node_vtable, nextdescr=Not)',
                         mismatch=True)   # missing valuedescr
        self.find_bridge(ops, 'Not', 'Virtual(node_vtable2, valuedescr=Not)',
                         mismatch=True)   # bad class

    def test_bridge_simple_virtual_struct(self):
        ops = """
        [i0]
        p0 = new(descr=ssize)
        setfield_gc(p0, i0, descr=adescr)
        jump(p0)
        """
        self.find_bridge(ops, 'Not', 'Not')
        self.find_bridge(ops, 'Not', 'VStruct(ssize, adescr=Not)')

    def test_bridge_simple_virtual_struct_non_unique(self):
        ops = """
        [i0]
        p0 = new(descr=ssize)
        setfield_gc(p0, i0, descr=adescr)
        jump(p0, p0)
        """
        self.find_bridge(ops, 'Not', 'Not, Not')
        self.find_bridge(ops, 'Not', 'VStruct(ssize), VStruct(ssize)',
                         mismatch=True)


    def test_bridge_simple_virtual_2(self):
        ops = """
        [p0]
        setfield_gc(p0, 123, descr=valuedescr)
        jump(p0)
        """
        self.find_bridge(ops, 'Virtual(node_vtable)', 'Not')
        self.find_bridge(ops, 'Virtual(node_vtable)',
                              'Virtual(node_vtable, valuedescr=Not)')
        self.find_bridge(ops, 'Virtual(node_vtable, valuedescr=Not)',
                              'Virtual(node_vtable, valuedescr=Not)')
        self.find_bridge(ops, 'Virtual(node_vtable, valuedescr=Not)',
                            '''Virtual(node_vtable,
                                       valuedescr=Not,
                                       nextdescr=Not)''')
        self.find_bridge(ops, '''Virtual(node_vtable,
                                         valuedescr=Not,
                                         nextdescr=Not)''',
                              '''Virtual(node_vtable,
                                         valuedescr=Not,
                                         nextdescr=Not)''')
        #
        self.find_bridge(ops, 'Virtual(node_vtable)', 'Virtual(node_vtable)',
                         mismatch=True)    # because of missing valuedescr
        self.find_bridge(ops, 'Virtual(node_vtable)',
                         'Virtual(node_vtable2, valuedescr=Not)',
                         mismatch=True)    # bad class

    def test_bridge_virtual_mismatch_1(self):
        ops = """
        [i0]
        p0 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p0, i0, descr=valuedescr)
        jump(p0, p0)
        """
        self.find_bridge(ops, 'Not', 'Not, Not')
        #
        self.find_bridge(ops, 'Not',
                         '''Virtual(node_vtable, valuedescr=Not),
                            Virtual(node_vtable, valuedescr=Not)''',
                         mismatch=True)    # duplicate p0

    def test_bridge_guard_class(self):
        ops = """
        [p1]
        p2 = getfield_gc(p1, descr=nextdescr)
        guard_class(p2, ConstClass(node_vtable)) []
        jump(p2)
        """
        self.find_bridge(ops, 'Not', 'Not')
        self.find_bridge(ops, 'Virtual(node_vtable2, nextdescr=Not)', 'Not')
        self.find_bridge(ops,
            '''Virtual(node_vtable,
                       nextdescr=Virtual(node_vtable,
                                         nextdescr=Not))''',
            '''Virtual(node_vtable,
                       nextdescr=Not)''')
        #
        self.find_bridge(ops, 'Not', 'Virtual(node_vtable)',
                         mismatch=True)

    def test_bridge_unused(self):
        ops = """
        []
        p1 = new_with_vtable(ConstClass(node_vtable))
        p2 = new_with_vtable(ConstClass(node_vtable))
        p3 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p1, p2, descr=nextdescr)
        setfield_gc(p2, p3, descr=nextdescr)
        jump(p1)
        """
        self.find_bridge(ops, '',
            '''Not''')
        self.find_bridge(ops, '',
            '''Virtual(node_vtable,
                       nextdescr=Not)''')
        self.find_bridge(ops, '',
            '''Virtual(node_vtable,
                       nextdescr=Virtual(node_vtable,
                                         nextdescr=Not))''')
        self.find_bridge(ops, '',
            '''Virtual(node_vtable,
                       nextdescr=Virtual(node_vtable,
                                         nextdescr=Virtual(node_vtable)))''')
        self.find_bridge(ops, '',
            '''Virtual(node_vtable,
                       nextdescr=Virtual(node_vtable,
                                         nextdescr=Virtual(node_vtable,
                                                           nextdescr=Not)))''')

    def test_bridge_to_finish(self):
        ops = """
        [i1]
        i2 = int_add(i1, 5)
        finish(i2)
        """
        self.find_bridge(ops, 'Not', 'Not')

    def test_bridge_virtual_to_finish(self):
        ops = """
        [i1]
        p1 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p1, i1, descr=valuedescr)
        finish(p1)
        """
        self.find_bridge(ops, 'Not', 'Not')
        self.find_bridge(ops, 'Not',
                         'Virtual(node_vtable, valuedescr=Not)',
                         mismatch=True)

    def test_bridge_array_virtual_1(self):
        ops = """
        [i1]
        p1 = new_array(3, descr=arraydescr)
        setarrayitem_gc(p1, 0, i1, descr=arraydescr)
        jump(p1)
        """
        self.find_bridge(ops, 'Not', 'Not')
        self.find_bridge(ops, 'Not', 'VArray(arraydescr, Not, Not, Not)')

    def test_bridge_array_virtual_size_mismatch(self):
        ops = """
        [i1]
        p1 = new_array(5, descr=arraydescr)
        setarrayitem_gc(p1, 0, i1, descr=arraydescr)
        jump(p1)
        """
        self.find_bridge(ops, 'Not', 'Not')
        self.find_bridge(ops, 'Not', 'VArray(arraydescr, Not, Not, Not)',
                         mismatch=True)

    def test_bridge_array_virtual_2(self):
        ops = """
        [i1]
        p1 = new_array(3, descr=arraydescr)
        setarrayitem_gc(p1, 0, i1, descr=arraydescr)
        escape(p1)
        jump(p1)
        """
        self.find_bridge(ops, 'Not', 'Not')
        self.find_bridge(ops, 'Not', 'VArray(arraydescr, Not, Not, Not)',
                         mismatch=True)

    def test_bridge_nested_structs(self):
        ops = """
        []
        p1 = new_with_vtable(ConstClass(node_vtable))
        p2 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p1, p2, descr=nextdescr)
        jump(p1)
        """
        self.find_bridge(ops, '', 'Not')
        self.find_bridge(ops, '', 'Virtual(node_vtable, nextdescr=Not)')
        self.find_bridge(ops, '',
                   'Virtual(node_vtable, nextdescr=Virtual(node_vtable))')
        self.find_bridge(ops, '',
                   'Virtual(node_vtable, nextdescr=Virtual(node_vtable2))',
                   mismatch=True)


class TestLLtype(BaseTestOptimizeFindNode, LLtypeMixin):
    pass

class TestOOtype(BaseTestOptimizeFindNode, OOtypeMixin):

    def test_find_nodes_instanceof(self):
        ops = """
        [i0]
        p0 = new_with_vtable(ConstClass(node_vtable))
        i1 = instanceof(p0, descr=nodesize)
        jump(i1)
        """
        boxes, getnode = self.find_nodes(ops, 'Not')
        assert not getnode(boxes.p0).escaped
