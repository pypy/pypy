import py
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi, rstr
from rpython.rtyper.lltypesystem.lloperation import LL_OPERATIONS
from rpython.translator.c.support import cdecl
from rpython.rlib import exports, revdb


def extra_files():
    srcdir = py.path.local(__file__).join('..', 'src-revdb')
    return [
        srcdir / 'revdb.c',
    ]

def prepare_function(funcgen):
    stack_bottom = False
    for block in funcgen.graph.iterblocks():
        for op in block.operations:
            if op.opname == 'gc_stack_bottom':
                stack_bottom = True
    if stack_bottom:
        name = funcgen.functionname
        funcgen.db.stack_bottom_funcnames.append(name)
        extra_enter_text = '\n'.join(
            ['RPY_REVDB_CALLBACKLOC(RPY_CALLBACKLOC_%s);' % name] +
            ['\t' + emit('/*arg*/', funcgen.lltypename(v), funcgen.expr(v))
                for v in funcgen.graph.getargs()])
        extra_return_text = '/* RPY_CALLBACK_LEAVE(); */'
        return extra_enter_text, extra_return_text
    else:
        return None, None

def emit_void(normal_code):
    return 'RPY_REVDB_EMIT_VOID(%s);' % (normal_code,)

def emit(normal_code, tp, value):
    if tp == 'void @':
        return emit_void(normal_code)
    return 'RPY_REVDB_EMIT(%s, %s, %s);' % (normal_code, cdecl(tp, '_e'), value)

def emit_residual_call(funcgen, call_code, v_result, expr_result):
    if getattr(getattr(funcgen.graph, 'func', None),
               '_revdb_do_all_calls_', False):
        return call_code   # a hack for ll_call_destructor() to mean
                           # that the calls should really be done
    # haaaaack
    if call_code in ('RPyGilRelease();', 'RPyGilAcquire();'):
        return '/* ' + call_code + ' */'
    #
    tp = funcgen.lltypename(v_result)
    if tp == 'void @':
        return 'RPY_REVDB_CALL_VOID(%s);' % (call_code,)
    return 'RPY_REVDB_CALL(%s, %s, %s);' % (call_code, cdecl(tp, '_e'),
                                            expr_result)

def record_malloc_uid(expr):
    return ' RPY_REVDB_REC_UID(%s);' % (expr,)

def boehm_register_finalizer(funcgen, op):
    return 'rpy_reverse_db_register_destructor(%s, %s);' % (
        funcgen.expr(op.args[0]), funcgen.expr(op.args[1]))

def cast_gcptr_to_int(funcgen, op):
    return '%s = RPY_REVDB_CAST_PTR_TO_INT(%s);' % (
        funcgen.expr(op.result), funcgen.expr(op.args[0]))

set_revdb_protected = set(opname for opname, opdesc in LL_OPERATIONS.items()
                                 if opdesc.revdb_protect)


def prepare_database(db):
    FUNCPTR = lltype.Ptr(lltype.FuncType([revdb._CMDPTR, lltype.Ptr(rstr.STR)],
                                         lltype.Void))
    ALLOCFUNCPTR = lltype.Ptr(lltype.FuncType([rffi.LONGLONG, llmemory.GCREF],
                                              lltype.Void))

    bk = db.translator.annotator.bookkeeper
    cmds = getattr(db.translator, 'revdb_commands', {})
    numcmds = [(num, func) for (num, func) in cmds.items()
                           if isinstance(num, int)]

    S = lltype.Struct('RPY_REVDB_COMMANDS',
                  ('names', lltype.FixedSizeArray(rffi.INT, len(numcmds) + 1)),
                  ('funcs', lltype.FixedSizeArray(FUNCPTR, len(numcmds))),
                  ('alloc', ALLOCFUNCPTR))
    s = lltype.malloc(S, flavor='raw', immortal=True, zero=True)

    i = 0
    for name, func in cmds.items():
        fnptr = lltype.getfunctionptr(bk.getdesc(func).getuniquegraph())
        if isinstance(name, int):
            assert name != 0
            s.names[i] = rffi.cast(rffi.INT, name)
            s.funcs[i] = fnptr
            i += 1
        elif name == "ALLOCATING":
            s.alloc = fnptr
        else:
            raise AssertionError("bad tag in register_debug_command(): %r"
                                 % (name,))

    exports.EXPORTS_obj2name[s._as_obj()] = 'rpy_revdb_commands'
    db.get(s)

    db.stack_bottom_funcnames = []

def write_revdb_def_file(db, target_path):
    funcnames = sorted(db.stack_bottom_funcnames)
    f = target_path.open('w')
    for i, fn in enumerate(funcnames):
        print >> f, '#define RPY_CALLBACKLOC_%s %d' % (fn, i)
    print >> f
    print >> f, '#define RPY_CALLBACKLOCS \\'
    funcnames = funcnames or ['NULL']
    for i, fn in enumerate(funcnames):
        if i == len(funcnames) - 1:
            tail = ''
        else:
            tail = ', \\'
        print >> f, '\t(void *)%s%s' % (fn, tail)
    f.close()
