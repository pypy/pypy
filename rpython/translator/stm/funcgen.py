from rpython.flowspace.model import Constant
from rpython.translator.c.support import c_string_constant, cdecl
from rpython.translator.c.node import Node, ContainerNode
from rpython.translator.c.primitive import name_small_integer
from rpython.rtyper.lltypesystem import lltype, llmemory


class StmHeaderOpaqueDefNode(Node):
    typetag = ''
    dependencies = ()

    def __init__(self, db, T):
        Node.__init__(self, db)
        self.T = T
        self.name = 'object_t'

    def setup(self):
        pass

    def definition(self):
        return []

    def c_struct_field_name(self, _):
        return 'tid'


class StmHeader_OpaqueNode(ContainerNode):
    nodekind = 'stmhdr'
    globalcontainer = True
    typename = 'object_t @'
    implementationtypename = typename
    _funccodegen_owner = None

    def __init__(self, db, T, obj):
        assert isinstance(obj._name, int)
        self.db = db
        self.T = T
        self.obj = obj

    def initializationexpr(self, decoration=''):
        yield '{ { }, %s }' % (
            name_small_integer(self.obj.typeid16, self.db))
        #    self.obj.prebuilt_hash


def stm_register_thread_local(funcgen, op):
    return 'pypy_stm_register_thread_local();'

def stm_unregister_thread_local(funcgen, op):
    return 'pypy_stm_unregister_thread_local();'

def stm_read(funcgen, op):
    assert isinstance(op.args[0].concretetype, lltype.Ptr)
    assert op.args[0].concretetype.TO._gckind == 'gc'
    arg0 = funcgen.expr(op.args[0])
    return 'stm_read((object_t *)%s);' % (arg0,)

def stm_write(funcgen, op):
    assert isinstance(op.args[0].concretetype, lltype.Ptr)
    assert op.args[0].concretetype.TO._gckind == 'gc'
    arg0 = funcgen.expr(op.args[0])
    return 'stm_write((object_t *)%s);' % (arg0,)

def stm_can_move(funcgen, op):
    arg0 = funcgen.expr(op.args[0])
    result = funcgen.expr(op.result)
    return '%s = stm_can_move((object_t *)%s);' % (result, arg0)

def stm_allocate_tid(funcgen, op):
    arg_size    = funcgen.expr(op.args[0])
    arg_type_id = funcgen.expr(op.args[1])
    result      = funcgen.expr(op.result)
    # XXX NULL returns?
    return ('%s = (rpygcchar_t *)stm_allocate(%s); ' % (result, arg_size) +
            '((rpyobj_t *)%s)->tid = %s;' % (result, arg_type_id))

def stm_allocate_weakref(funcgen, op):
    arg_size    = funcgen.expr(op.args[0])
    arg_type_id = funcgen.expr(op.args[1])
    result      = funcgen.expr(op.result)
    # XXX NULL returns?
    return ('%s = (rpygcchar_t *)stm_allocate_weakref(%s); ' % (result, arg_size) +
            '((rpyobj_t *)%s)->tid = %s;' % (result, arg_type_id))

def stm_get_from_obj(funcgen, op):
    assert op.args[0].concretetype == llmemory.GCREF
    arg_obj = funcgen.expr(op.args[0])
    arg_ofs = funcgen.expr(op.args[1])
    result  = funcgen.expr(op.result)
    resulttype = cdecl(funcgen.lltypename(op.result), '')
    return '%s = *(TLPREFIX %s *)(%s + %s);' % (
        result, resulttype, arg_obj, arg_ofs)

stm_get_from_obj_const = stm_get_from_obj

def stm_set_into_obj(funcgen, op):
    assert op.args[0].concretetype == llmemory.GCREF
    arg_obj = funcgen.expr(op.args[0])
    arg_ofs = funcgen.expr(op.args[1])
    arg_val = funcgen.expr(op.args[2])
    valtype = cdecl(funcgen.lltypename(op.args[2]), '')
    return '*(TLPREFIX %s *)(%s + %s) = %s;' % (
        valtype, arg_obj, arg_ofs, arg_val)

def stm_collect(funcgen, op):
    arg0 = funcgen.expr(op.args[0])
    return 'stm_collect(%s);' % (arg0,)

def stm_id(funcgen, op):
    arg0 = funcgen.expr(op.args[0])
    result = funcgen.expr(op.result)
    return '%s = stm_id((object_t *)%s);' % (result, arg0)

def stm_identityhash(funcgen, op):
    arg0 = funcgen.expr(op.args[0])
    result = funcgen.expr(op.result)
    return '%s = stm_identityhash((object_t *)%s);' % (result, arg0)

def stm_addr_get_tid(funcgen, op):
    arg0   = funcgen.expr(op.args[0])
    result = funcgen.expr(op.result)
    return '%s = ((struct rpyobj_s *)%s)->tid;' % (result, arg0)

def stm_become_inevitable(funcgen, op):
    try:
        info = op.args[0].value
    except IndexError:
        info = "?"    # cannot insert it in 'llop'
    try:
        info = '%s:%s' % (funcgen.graph.name, info)
    except AttributeError:
        pass
    string_literal = c_string_constant(info)
    return 'pypy_stm_become_inevitable(%s);' % (string_literal,)

def stm_become_globally_unique_transaction(funcgen, op):
    return 'pypy_stm_become_globally_unique_transaction();'

def stm_push_root(funcgen, op):
    arg0 = funcgen.expr(op.args[0])
    return 'STM_PUSH_ROOT(stm_thread_local, %s);' % (arg0,)

def stm_pop_root_into(funcgen, op):
    arg0 = funcgen.expr(op.args[0])
    if isinstance(op.args[0], Constant):
        return '/* %s = */ STM_POP_ROOT_RET(stm_thread_local);' % (arg0,)
    return 'STM_POP_ROOT(stm_thread_local, %s);' % (arg0,)

def stm_commit_if_not_atomic(funcgen, op):
   return 'pypy_stm_commit_if_not_atomic();'

def stm_start_inevitable_if_not_atomic(funcgen, op):
    return 'pypy_stm_start_inevitable_if_not_atomic();'

def stm_enter_callback_call(funcgen, op):
    result = funcgen.expr(op.result)
    return '%s = pypy_stm_enter_callback_call();' % (result,)

def stm_leave_callback_call(funcgen, op):
    arg0 = funcgen.expr(op.args[0])
    return 'pypy_stm_leave_callback_call(%s);' % (arg0,)

def stm_should_break_transaction(funcgen, op):
    result = funcgen.expr(op.result)
    return '%s = pypy_stm_should_break_transaction();' % (result,)

def stm_set_transaction_length(funcgen, op):
    arg0 = funcgen.expr(op.args[0])
    return 'pypy_stm_set_transaction_length(%s);' % (arg0,)

def stm_threadlocal_get(funcgen, op):
    result = funcgen.expr(op.result)
    return '%s = (%s)stm_thread_local.thread_local_obj;' % (
        result, cdecl(funcgen.lltypename(op.result), ''))

def stm_threadlocal_set(funcgen, op):
    arg0 = funcgen.expr(op.args[0])
    return 'stm_thread_local.thread_local_obj = (object_t *)%s;' % (arg0,)

def stm_perform_transaction(funcgen, op):
    arg0 = funcgen.expr(op.args[0])
    arg1 = funcgen.expr(op.args[1])
    return ('pypy_stm_perform_transaction((object_t *)%s, '
            '(int(*)(object_t *, int))%s);' % (arg0, arg1))

def stm_increment_atomic(funcgen, op):
    return 'pypy_stm_increment_atomic();'

def stm_decrement_atomic(funcgen, op):
    return 'pypy_stm_decrement_atomic();'

def stm_get_atomic(funcgen, op):
    result = funcgen.expr(op.result)
    return '%s = pypy_stm_get_atomic();' % (result,)

def stm_abort_and_retry(funcgen, op):
    return 'stm_abort_transaction();'

def stm_abort_info_push(funcgen, op):
    arg0 = funcgen.expr(op.args[0])
    arg1 = funcgen.expr(op.args[1])
    return '//XXX stm_abort_info_push((gcptr)%s, %s);' % (arg0, arg1)

def stm_abort_info_pop(funcgen, op):
    arg0 = funcgen.expr(op.args[0])
    return '//XXX stm_abort_info_pop(%s);' % (arg0,)

def stm_inspect_abort_info(funcgen, op):
    result = funcgen.expr(op.result)
    return '%s = NULL; //XXX stm_inspect_abort_info();' % (result,)

def stm_ignored_start(funcgen, op):
    return '/* stm_ignored_start */'

def stm_ignored_stop(funcgen, op):
    return '/* stm_ignored_stop */'

def stm_get_root_stack_top(funcgen, op):
    result = funcgen.expr(op.result)
    return '%s = (%s)&stm_thread_local.shadowstack;' % (
        result, cdecl(funcgen.lltypename(op.result), ''))


##def stm_initialize(funcgen, op):
##    return '''stm_initialize();
##    stm_clear_on_abort(&pypy_g_ExcData, sizeof(pypy_g_ExcData));
##    '''

##def stm_finalize(funcgen, op):
##    return 'stm_finalize();'

##def stm_barrier(funcgen, op):
##    category_change = op.args[0].value
##    # XXX: how to unify the stm_barrier llop generation in
##    #      writebarrier.py and threadlocalref.py?
##    if isinstance(category_change, str):
##        frm, middle, to = category_change
##    else: # rstr
##        frm, middle, to = (category_change.chars[0],
##                           category_change.chars[1],
##                           category_change.chars[2])
##    assert middle == '2'
##    assert frm < to
##    if to == 'W':
##        if frm >= 'V':
##            funcname = 'stm_repeat_write_barrier'
##        else:
##            funcname = 'stm_write_barrier'
##    elif to == 'V':
##        funcname = 'stm_write_barrier_noptr'
##    elif to == 'R':
##        if frm >= 'Q':
##            funcname = 'stm_repeat_read_barrier'
##        else:
##            funcname = 'stm_read_barrier'
##    elif to == 'I':
##        funcname = 'stm_immut_read_barrier'
##    else:
##        raise AssertionError(category_change)
##    assert op.args[1].concretetype == op.result.concretetype
##    arg = funcgen.expr(op.args[1])
##    result = funcgen.expr(op.result)
##    return '%s = (%s)%s((gcptr)%s);' % (
##        result, cdecl(funcgen.lltypename(op.result), ''),
##        funcname, arg)

##def stm_ptr_eq(funcgen, op):
##    args = [funcgen.expr(v) for v in op.args]
##    result = funcgen.expr(op.result)
##    # check for prebuilt arguments
##    for i, j in [(0, 1), (1, 0)]:
##        if isinstance(op.args[j], Constant):
##            if op.args[j].value:     # non-NULL
##                return ('%s = stm_pointer_equal_prebuilt((gcptr)%s, (gcptr)%s);'
##                        % (result, args[i], args[j]))
##            else:
##                # this case might be unreachable, but better safe than sorry
##                return '%s = (%s == NULL);' % (result, args[i])
##    #
##    return '%s = stm_pointer_equal((gcptr)%s, (gcptr)%s);' % (
##        result, args[0], args[1])

##def stm_stop_all_other_threads(funcgen, op):
##    return 'stm_stop_all_other_threads();'

##def stm_partial_commit_and_resume_other_threads(funcgen, op):
##    return 'stm_partial_commit_and_resume_other_threads();'

##def stm_get_adr_of_nursery_current(funcgen, op):
##    result = funcgen.expr(op.result)
##    return '%s = (%s)&stm_nursery_current;' % (
##        result, cdecl(funcgen.lltypename(op.result), ''))

##def stm_get_adr_of_nursery_nextlimit(funcgen, op):
##    result = funcgen.expr(op.result)
##    return '%s = (%s)&stm_nursery_nextlimit;' % (
##        result, cdecl(funcgen.lltypename(op.result), ''))

##def stm_get_adr_of_active(funcgen, op):
##    result = funcgen.expr(op.result)
##    return '%s = (%s)&stm_active;' % (
##        result, cdecl(funcgen.lltypename(op.result), ''))

##def stm_get_adr_of_private_rev_num(funcgen, op):
##    result = funcgen.expr(op.result)
##    return '%s = (%s)&stm_private_rev_num;' % (
##        result, cdecl(funcgen.lltypename(op.result), ''))

##def stm_get_adr_of_read_barrier_cache(funcgen, op):
##    result = funcgen.expr(op.result)
##    return '%s = (%s)&stm_read_barrier_cache;' % (
##        result, cdecl(funcgen.lltypename(op.result), ''))
    
    
##def stm_weakref_allocate(funcgen, op):
##    arg0 = funcgen.expr(op.args[0])
##    arg1 = funcgen.expr(op.args[1])
##    arg2 = funcgen.expr(op.args[2])
##    result = funcgen.expr(op.result)
##    return '%s = stm_weakref_allocate(%s, %s, %s);' % (result, arg0, 
##                                                       arg1, arg2)

##def stm_allocate_nonmovable_int_adr(funcgen, op):
##    arg0 = funcgen.expr(op.args[0])
##    result = funcgen.expr(op.result)
##    return '%s = stm_allocate_public_integer_address(%s);' % (result, arg0)

##def stm_get_tid(funcgen, op):
##    arg0 = funcgen.expr(op.args[0])
##    result = funcgen.expr(op.result)
##    return '%s = ((struct rpyobj_s*)%s)->tid;' % (result, arg0)

##def stm_enter_callback_call(funcgen, op):
##    result = funcgen.expr(op.result)
##    return '%s = stm_enter_callback_call();' % (result,)

##def stm_leave_callback_call(funcgen, op):
##    arg0 = funcgen.expr(op.args[0])
##    return 'stm_leave_callback_call(%s);' % (arg0,)

##def stm_minor_collect(funcgen, op):
##    return 'stm_minor_collect();'

##def stm_major_collect(funcgen, op):
##    return 'stm_major_collect();'
