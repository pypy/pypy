from rpython.flowspace.model import Constant
from rpython.translator.c.support import c_string_constant, cdecl
from rpython.translator.c.node import Node, ContainerNode
from rpython.translator.c.primitive import name_small_integer


class StmHeaderOpaqueDefNode(Node):
    typetag = 'struct'
    dependencies = ()

    def __init__(self, db, T):
        Node.__init__(self, db)
        self.T = T
        self.name = 'stm_object_s'

    def setup(self):
        pass

    def definition(self):
        return []

    def c_struct_field_name(self, _):
        return 'h_tid'


class StmHeader_OpaqueNode(ContainerNode):
    nodekind = 'stmhdr'
    globalcontainer = True
    typename = 'struct stm_object_s @'
    implementationtypename = typename
    _funccodegen_owner = None

    def __init__(self, db, T, obj):
        assert isinstance(obj._name, int)
        self.db = db
        self.T = T
        self.obj = obj

    def initializationexpr(self, decoration=''):
        yield '{ %s | PREBUILT_FLAGS, PREBUILT_REVISION, %dL }' % (
            name_small_integer(self.obj.typeid16, self.db),
            self.obj.prebuilt_hash)


def stm_initialize(funcgen, op):
    return '''stm_initialize();
    stm_clear_on_abort(&pypy_g_ExcData.ed_exc_type,
                       sizeof(struct pypy_object0 *));
    '''

def stm_finalize(funcgen, op):
    return 'stm_finalize();'

def stm_barrier(funcgen, op):
    category_change = op.args[0].value
    frm, middle, to = category_change
    assert middle == '2'
    assert frm < to
    if to == 'W':
        if frm >= 'V':
            funcname = 'stm_repeat_write_barrier'
        else:
            funcname = 'stm_write_barrier'
    elif to == 'V':
        funcname = 'stm_write_barrier_noptr'
    elif to == 'R':
        if frm >= 'Q':
            funcname = 'stm_repeat_read_barrier'
        else:
            funcname = 'stm_read_barrier'
    elif to == 'I':
        funcname = 'stm_immut_read_barrier'
    else:
        raise AssertionError(category_change)
    assert op.args[1].concretetype == op.result.concretetype
    arg = funcgen.expr(op.args[1])
    result = funcgen.expr(op.result)
    return '%s = (%s)%s((gcptr)%s);' % (
        result, cdecl(funcgen.lltypename(op.result), ''),
        funcname, arg)

def stm_ptr_eq(funcgen, op):
    args = [funcgen.expr(v) for v in op.args]
    result = funcgen.expr(op.result)
    # check for prebuilt arguments
    for i, j in [(0, 1), (1, 0)]:
        if isinstance(op.args[j], Constant):
            if op.args[j].value:     # non-NULL
                return ('%s = stm_pointer_equal_prebuilt((gcptr)%s, (gcptr)%s);'
                        % (result, args[i], args[j]))
            else:
                # this case might be unreachable, but better safe than sorry
                return '%s = (%s == NULL);' % (result, args[i])
    #
    return '%s = stm_pointer_equal((gcptr)%s, (gcptr)%s);' % (
        result, args[0], args[1])

def stm_become_inevitable(funcgen, op):
    try:
        info = op.args[0].value
    except IndexError:
        info = "rstm.become_inevitable"    # cannot insert it in 'llop'
    string_literal = c_string_constant(info)
    return 'stm_become_inevitable(%s);' % (string_literal,)

def stm_push_root(funcgen, op):
    arg0 = funcgen.expr(op.args[0])
    return 'stm_push_root((gcptr)%s);' % (arg0,)

def stm_pop_root_into(funcgen, op):
    arg0 = funcgen.expr(op.args[0])
    if isinstance(op.args[0], Constant):
        return '/* %s = */ stm_pop_root();' % (arg0,)
    return '%s = (%s)stm_pop_root();' % (
        arg0, cdecl(funcgen.lltypename(op.args[0]), ''))

def stm_get_adr_of_nursery_current(funcgen, op):
    result = funcgen.expr(op.result)
    return '%s = (%s)&stm_nursery_current;' % (
        result, cdecl(funcgen.lltypename(op.result), ''))

def stm_get_adr_of_nursery_nextlimit(funcgen, op):
    result = funcgen.expr(op.result)
    return '%s = (%s)&stm_nursery_nextlimit;' % (
        result, cdecl(funcgen.lltypename(op.result), ''))

def stm_get_adr_of_active(funcgen, op):
    result = funcgen.expr(op.result)
    return '%s = (%s)&stm_active;' % (
        result, cdecl(funcgen.lltypename(op.result), ''))
    
def stm_get_root_stack_top(funcgen, op):
    result = funcgen.expr(op.result)
    return '%s = (%s)&stm_shadowstack;' % (
        result, cdecl(funcgen.lltypename(op.result), ''))

def stm_get_adr_of_private_rev_num(funcgen, op):
    result = funcgen.expr(op.result)
    return '%s = (%s)&stm_private_rev_num;' % (
        result, cdecl(funcgen.lltypename(op.result), ''))

def stm_get_adr_of_read_barrier_cache(funcgen, op):
    result = funcgen.expr(op.result)
    return '%s = (%s)&stm_read_barrier_cache;' % (
        result, cdecl(funcgen.lltypename(op.result), ''))
    
    
def stm_weakref_allocate(funcgen, op):
    arg0 = funcgen.expr(op.args[0])
    arg1 = funcgen.expr(op.args[1])
    arg2 = funcgen.expr(op.args[2])
    result = funcgen.expr(op.result)
    return '%s = stm_weakref_allocate(%s, %s, %s);' % (result, arg0, 
                                                       arg1, arg2)

def stm_allocate_nonmovable_int_adr(funcgen, op):
    arg0 = funcgen.expr(op.args[0])
    result = funcgen.expr(op.result)
    return '%s = stm_allocate_public_integer_address(%s);' % (result, arg0)
    
def stm_allocate(funcgen, op):
    arg0 = funcgen.expr(op.args[0])
    arg1 = funcgen.expr(op.args[1])
    result = funcgen.expr(op.result)
    return '%s = stm_allocate(%s, %s);' % (result, arg0, arg1)

def stm_get_tid(funcgen, op):
    arg0 = funcgen.expr(op.args[0])
    result = funcgen.expr(op.result)
    return '%s = stm_get_tid((gcptr)%s);' % (result, arg0)

def stm_hash(funcgen, op):
    arg0 = funcgen.expr(op.args[0])
    result = funcgen.expr(op.result)
    return '%s = stm_hash((gcptr)%s);' % (result, arg0)

def stm_id(funcgen, op):
    arg0 = funcgen.expr(op.args[0])
    result = funcgen.expr(op.result)
    return '%s = stm_id((gcptr)%s);' % (result, arg0)

def stm_commit_transaction(funcgen, op):
    return '{ int e = errno; stm_commit_transaction(); errno = e; }'

def stm_begin_inevitable_transaction(funcgen, op):
    return '{ int e = errno; stm_begin_inevitable_transaction(); errno = e; }'

def stm_should_break_transaction(funcgen, op):
    result = funcgen.expr(op.result)
    return '%s = stm_should_break_transaction();' % (result,)

def stm_set_transaction_length(funcgen, op):
    arg0 = funcgen.expr(op.args[0])
    return 'stm_set_transaction_length(%s);' % (arg0,)

def stm_change_atomic(funcgen, op):
    arg0 = funcgen.expr(op.args[0])
    return 'stm_atomic(%s);' % (arg0,)

def stm_get_atomic(funcgen, op):
    result = funcgen.expr(op.result)
    return '%s = stm_atomic(0);' % (result,)

def stm_threadlocal_get(funcgen, op):
    result = funcgen.expr(op.result)
    return '%s = (%s)stm_thread_local_obj;' % (
        result, cdecl(funcgen.lltypename(op.result), ''))

def stm_threadlocal_set(funcgen, op):
    arg0 = funcgen.expr(op.args[0])
    return 'stm_thread_local_obj = (gcptr)%s;' % (arg0,)

def stm_perform_transaction(funcgen, op):
    arg0 = funcgen.expr(op.args[0])
    arg1 = funcgen.expr(op.args[1])
    return 'stm_perform_transaction((gcptr)%s, %s);' % (arg0, arg1)

def stm_enter_callback_call(funcgen, op):
    result = funcgen.expr(op.result)
    return '%s = stm_enter_callback_call();' % (result,)

def stm_leave_callback_call(funcgen, op):
    arg0 = funcgen.expr(op.args[0])
    return 'stm_leave_callback_call(%s);' % (arg0,)

def stm_abort_and_retry(funcgen, op):
    return 'stm_abort_and_retry();'

def stm_abort_info_push(funcgen, op):
    arg0 = funcgen.expr(op.args[0])
    arg1 = funcgen.expr(op.args[1])
    return 'stm_abort_info_push((gcptr)%s, %s);' % (arg0, arg1)

def stm_abort_info_pop(funcgen, op):
    arg0 = funcgen.expr(op.args[0])
    return 'stm_abort_info_pop(%s);' % (arg0,)

def stm_inspect_abort_info(funcgen, op):
    result = funcgen.expr(op.result)
    return '%s = stm_inspect_abort_info();' % (result,)

def stm_minor_collect(funcgen, op):
    return 'stm_minor_collect();'

def stm_major_collect(funcgen, op):
    return 'stm_major_collect();'


def op_stm(funcgen, op):
    func = globals()[op.opname]
    return func(funcgen, op)
