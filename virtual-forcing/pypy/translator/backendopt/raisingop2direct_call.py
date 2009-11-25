from pypy.translator.backendopt.support import log, all_operations, annotate
import pypy.rpython.raisingops.raisingops
log = log.raisingop2directcall

def is_raisingop(op):
    s = op.opname
    if (not s.startswith('int_') and not s.startswith('uint_') and
        not s.startswith('float_') and not s.startswith('llong_')):
       return False
    if not s.endswith('_zer') and not s.endswith('_ovf') and not s.endswith('_val'): #not s in special_operations:
       return False
    return True

def raisingop2direct_call(translator, graphs=None):
    """search for operations that could raise an exception and change that
    operation into a direct_call to a function from the raisingops directory.
    This function also needs to be annotated and specialized.

    note: this could be extended to allow for any operation to be changed into
          a direct_call to a (RPython) function!
    """
    #special_operations = "int_floordiv int_mod".split()
    if graphs is None:
        graphs = translator.graphs


    log('starting')
    seen = {}
    for op in all_operations(graphs):
        if not is_raisingop(op):
            continue
        func = getattr(pypy.rpython.raisingops.raisingops, op.opname, None)
        if not func:
            log.warning("%s not found" % op.opname)
            continue
        if op.opname not in seen:
            seen[op.opname] = 0
        seen[op.opname] += 1
        op.args.insert(0, annotate(translator, func, op.result, op.args))
        op.opname = 'direct_call'

    #statistics...
    for k, v in seen.iteritems():
        log("%dx %s" % (v, k))

    #specialize newly annotated functions
    if seen != {}:
        translator.rtyper.specialize_more_blocks()

    #rename some operations (that were introduced in the newly specialized graphs)
    #so this transformation becomes idempotent... 
    #for op in all_operations(graphs):
    #   if op.opname in special_operations:
    #       log('renamed %s to %s_' % (op.opname, op.opname))
    #       op.opname += '_' 

    #selfdiagnostics... assert that there are no more raisingops
    for op in all_operations(graphs):
        if is_raisingop(op):
            log.warning("%s not transformed" % op.opname)

    #translator.view()
    log('finished')
