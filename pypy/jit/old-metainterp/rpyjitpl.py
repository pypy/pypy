import py
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.llinterp import LLInterpreter
from pypy.rpython import annlowlevel
from pypy.annotation import model as annmodel

from pypy.jit.metainterp.pyjitpl import (build_meta_interp, debug_checks,
                                         generate_bootstrapping_code, MIFrame)
from pypy.jit.metainterp.history import ResOperation, Const, Box, BoxInt, log
from pypy.jit.metainterp import history, specnode


def rpython_ll_meta_interp(function, args, loops=None, **kwds):
    global _cache
    key = (function, tuple([lltype.typeOf(arg) for arg in args]))
    if key != _cache[0]:
        _cache = (None,)
        type_system = 'lltype'
        kwds['translate_support_code'] = True
        metainterp = build_meta_interp(function, args, type_system, **kwds)
        boot_graph = set_ll_helper(metainterp,
                                   [lltype.typeOf(arg) for arg in args])
        metainterp.cpu.mixlevelann.finish()
        del metainterp.cpu.mixlevelann
        _cache = (key, metainterp, boot_graph)
    metainterp = _cache[1]
    boot_graph = _cache[2]
    history.ConstAddr.ever_seen = False
    log('---------- Test starting ----------')
    llinterp = LLInterpreter(metainterp.cpu.rtyper)
    results = llinterp.eval_graph(boot_graph, args)
    log('---------- Test done ----------')
    debug_checks()
    RESULT = metainterp.maingraph.getreturnvar().concretetype
    result = lltype._cast_whatever(RESULT, results.item0)
    if loops is not None:
        actual_loops = results.item1
        assert actual_loops == loops
    return result

_cache = (None,)


def boot(metainterp, name, *args):
    start_mp, redboxes = generate_bootstrapping_code(metainterp, *args)
    cpu = metainterp.cpu
    resultbox = cpu.execute_operations_in_new_frame(name, start_mp, redboxes,
                                                    'int')
    return resultbox.get_()


def set_ll_helper(metainterp, argtypes):
    name = '%s bootstrap' % (metainterp.maingraph.name,)
    annhelper = metainterp.cpu.mixlevelann

    def boot1(*args):
        result = boot(metainterp, name, *args)
        return (result, len(metainterp.stats.loops))

    args_s = [annmodel.lltype_to_annotation(T) for T in argtypes]
    s_result = annmodel.SomeTuple([annmodel.SomeInteger(),
                                   annmodel.SomeInteger()])
    boot_graph = annhelper.getgraph(boot1, args_s, s_result)
    return boot_graph
