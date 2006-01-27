from pypy.translator.backendopt.support import log, all_operations, annotate
import pypy.rpython.raisingops.raisingops
log = log.raisingop2directcall

def raisingop2direct_call(translator):
    """search for operations that could raise an exception and change that
    operation into a direct_call to a function from the raisingops directory.
    This function also needs to be annotated and specialized.
    """
    seen = {}
    for op in all_operations(translator):
        s = op.opname
        if not s.startswith('int_') and not s.startswith('uint_') and not s.startswith('float_'):
            continue
        if not s.endswith('_zer') and not s.endswith('_ovf') and not s.endswith('_val'):
            continue
        func = getattr(pypy.rpython.raisingops.raisingops, s, None)
        assert func, "exception raising operation %s was not found" % s
        if s not in seen:
            seen[s] = 0
            log.info(s)
        seen[s] += 1
        op.args.insert(0, annotate(translator, func, op.result, op.args))
        op.opname = 'direct_call'
    for k, v in seen.iteritems():
        log("%4dx %s" % (v, k))
    if seen != {}:
        translator.rtyper.specialize_more_blocks()
    #translator.view()
