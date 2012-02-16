from pypy.objspace.flow.model import SpaceOperation, Constant, Variable
from pypy.objspace.flow.model import Block, Link, checkgraph
from pypy.annotation import model as annmodel
from pypy.translator.unsimplify import varoftype, copyvar
from pypy.translator.stm.localtracker import StmLocalTracker
from pypy.rpython.lltypesystem import lltype, lloperation
from pypy.rpython import rclass


ALWAYS_ALLOW_OPERATIONS = set([
    'direct_call', 'force_cast', 'keepalive', 'cast_ptr_to_adr',
    'debug_print', 'debug_assert', 'cast_opaque_ptr', 'hint',
    'indirect_call', 'stack_current', 'gc_stack_bottom',
    ])
ALWAYS_ALLOW_OPERATIONS |= set(lloperation.enum_tryfold_ops())

def op_in_set(opname, set):
    return opname in set

# ____________________________________________________________


class STMTransformer(object):

    def __init__(self, translator=None):
        self.translator = translator
        self.count_get_local     = 0
        self.count_get_nonlocal  = 0
        self.count_get_immutable = 0
        self.count_set_local     = 0
        self.count_set_nonlocal  = 0
        self.count_set_immutable = 0

    def transform(self):
        assert not hasattr(self.translator, 'stm_transformation_applied')
        self.start_log()
        for graph in self.translator.graphs:
            pre_insert_stm_writebarrier(graph)
        self.localtracker = StmLocalTracker(self.translator)
        for graph in self.translator.graphs:
            self.transform_graph(graph)
        self.localtracker = None
        self.translator.stm_transformation_applied = True
        self.print_logs()

    def start_log(self):
        from pypy.translator.c.support import log
        log.info("Software Transactional Memory transformation")

    def print_logs(self):
        from pypy.translator.c.support import log
        log('get*:     proven local: %d' % self.count_get_local)
        log('      not proven local: %d' % self.count_get_nonlocal)
        log('             immutable: %d' % self.count_get_immutable)
        log('set*:     proven local: %d' % self.count_set_local)
        log('      not proven local: %d' % self.count_set_nonlocal)
        log('             immutable: %d' % self.count_set_immutable)
        log.info("Software Transactional Memory transformation applied")

    def transform_block(self, block):
        if block.operations == ():
            return
        newoperations = []
        self.current_block = block
        for i, op in enumerate(block.operations):
            self.current_op_index = i
            try:
                meth = getattr(self, 'stt_' + op.opname)
            except AttributeError:
                if (op_in_set(op.opname, ALWAYS_ALLOW_OPERATIONS) or
                        op.opname.startswith('stm_')):
                    meth = list.append
                else:
                    meth = turn_inevitable_and_proceed
                setattr(self.__class__, 'stt_' + op.opname,
                        staticmethod(meth))
            meth(newoperations, op)
        block.operations = newoperations
        self.current_block = None

    def transform_graph(self, graph):
        for block in graph.iterblocks():
            self.transform_block(block)

    # ----------

    # ----------

    def transform_get(self, newoperations, op, stmopname):
        if op.result.concretetype is lltype.Void:
            newoperations.append(op)
            return
        if op.args[0].concretetype.TO._gckind == 'raw':
            turn_inevitable(newoperations, op.opname + '-raw')
            newoperations.append(op)
            return
        if is_immutable(op):
            self.count_get_immutable += 1
            newoperations.append(op)
            return
        if isinstance(op.args[0], Variable):
            if self.localtracker.is_local(op.args[0]):
                self.count_get_local += 1
                newoperations.append(op)
                return
        self.count_get_nonlocal += 1
        op1 = SpaceOperation(stmopname, op.args, op.result)
        newoperations.append(op1)

    def transform_set(self, newoperations, op):
        if op.args[-1].concretetype is lltype.Void:
            newoperations.append(op)
            return
        if op.args[0].concretetype.TO._gckind == 'raw':
            turn_inevitable(newoperations, op.opname + '-raw')
            newoperations.append(op)
            return
        if is_immutable(op):
            self.count_set_immutable += 1
            newoperations.append(op)
            return
        if isinstance(op.args[0], Variable):
            if self.localtracker.is_local(op.args[0]):
                self.count_set_local += 1
                newoperations.append(op)
                return
        self.count_set_nonlocal += 1
        v_arg = op.args[0]
        v_local = varoftype(v_arg.concretetype)
        op0 = SpaceOperation('stm_writebarrier', [v_arg], v_local)
        newoperations.append(op0)
        op1 = SpaceOperation('bare_' + op.opname, [v_local] + op.args[1:],
                             op.result)
        newoperations.append(op1)
        import pdb; pdb.set_trace()


    def stt_getfield(self, newoperations, op):
        self.transform_get(newoperations, op, 'stm_getfield')

    def stt_setfield(self, newoperations, op):
        self.transform_set(newoperations, op)

    def stt_getarrayitem(self, newoperations, op):
        self.transform_get(newoperations, op, 'stm_getarrayitem')

    def stt_setarrayitem(self, newoperations, op):
        self.transform_set(newoperations, op)

    def stt_getinteriorfield(self, newoperations, op):
        self.transform_get(newoperations, op, 'stm_getinteriorfield')

    def stt_setinteriorfield(self, newoperations, op):
        self.transform_set(newoperations, op)

    def stt_malloc(self, newoperations, op):
        flags = op.args[1].value
        if flags['flavor'] == 'gc':
            assert self.localtracker.is_local(op.result)
        else:
            turn_inevitable(newoperations, 'malloc-raw')
        newoperations.append(op)

    stt_malloc_varsize = stt_malloc
    stt_malloc_nonmovable = stt_malloc
    stt_malloc_nonmovable_varsize = stt_malloc


def transform_graph(graph):
    # for tests: only transforms one graph
    STMTransformer().transform_graph(graph)


def turn_inevitable(newoperations, info):
    c_info = Constant(info, lltype.Void)
    op1 = SpaceOperation('stm_become_inevitable', [c_info],
                         varoftype(lltype.Void))
    newoperations.append(op1)

def turn_inevitable_and_proceed(newoperations, op):
    turn_inevitable(newoperations, op.opname)
    newoperations.append(op)

def unwraplist(list_v):
    for v in list_v:
        if isinstance(v, Constant):
            yield v.value
        elif isinstance(v, Variable):
            yield None    # unknown
        else:
            raise AssertionError(v)

def is_immutable(op):
    if op.opname in ('getfield', 'setfield'):
        STRUCT = op.args[0].concretetype.TO
        return STRUCT._immutable_field(op.args[1].value)
    if op.opname in ('getarrayitem', 'setarrayitem'):
        ARRAY = op.args[0].concretetype.TO
        return ARRAY._immutable_field()
    if op.opname == 'getinteriorfield':
        OUTER = op.args[0].concretetype.TO
        return OUTER._immutable_interiorfield(unwraplist(op.args[1:]))
    if op.opname == 'setinteriorfield':
        OUTER = op.args[0].concretetype.TO
        return OUTER._immutable_interiorfield(unwraplist(op.args[1:-1]))
    raise AssertionError(op)

def pre_insert_stm_writebarrier(graph):
    # put a number of 'stm_writebarrier' operations, one before each
    # relevant 'set*'.  Then try to avoid the situation where we have
    # one variable on which we do 'stm_writebarrier', but there are
    # also other variables that contain the same pointer, e.g. casted
    # to a different precise type.
    from pypy.translator.stm.gcsource import COPIES_POINTER
    #
    def emit(op):
        for v1 in op.args:
            if v1 in renames:
                # one argument at least is in 'renames', so we need
                # to make a new SpaceOperation
                args1 = [renames.get(v, v) for v in op.args]
                op1 = SpaceOperation(op.opname, args1, op.result)
                newoperations.append(op1)
                return
        # no argument is in 'renames', so we can just emit the op
        newoperations.append(op)
    #
    for block in graph.iterblocks():
        if block.operations == ():
            continue
        #
        # figure out the variables on which we want an stm_writebarrier
        copies = {}
        wants_a_writebarrier = {}
        for op in block.operations:
            if op.opname in COPIES_POINTER:
                assert len(op.args) == 1
                copies[op.result] = op
            elif (op.opname in ('setfield', 'setarrayitem',
                                'setinteriorfield') and
                  op.args[-1].concretetype is not lltype.Void and
                  op.args[0].concretetype.TO._gckind == 'gc' and
                  not is_immutable(op)):
                wants_a_writebarrier.setdefault(op.args[0], op)
        #
        # back-propagate the write barrier locations through the cast_pointers
        writebarrier_locations = {}
        for v, op in wants_a_writebarrier.items():
            while v in copies:
                op = copies[v]
                v = op.args[0]
            protect = writebarrier_locations.setdefault(op, set())
            protect.add(v)
        #
        # now insert the 'stm_writebarrier's
        renames = {}      # {original-var: renamed-var}
        newoperations = []
        for op in block.operations:
            locs = writebarrier_locations.get(op, None)
            if locs:
                for v1 in locs:
                    if v1 not in renames:
                        v2 = varoftype(v1.concretetype)
                        op1 = SpaceOperation('stm_writebarrier', [v1], v2)
                        emit(op1)
                        renames[v1] = v2
            emit(op)
        #
        if renames:
            for link in block.exits:
                link.args = [renames.get(v, v) for v in link.args]
        block.operations = newoperations
