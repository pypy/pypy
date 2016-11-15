from rpython.translator.backendopt import graphanalyze
from rpython.rtyper.lltypesystem import lltype
from rpython.tool.ansi_print import AnsiLogger

log = AnsiLogger("finalizer")


class FinalizerError(Exception):
    """__del__() is used for lightweight RPython destructors,
    but the FinalizerAnalyzer found that it is not lightweight.

    The set of allowed operations is restrictive for a good reason
    - it's better to be safe. Specifically disallowed operations:

    * anything that escapes self
    * anything that can allocate
    """

class FinalizerAnalyzer(graphanalyze.BoolGraphAnalyzer):
    """ Analyzer that determines whether a finalizer is lightweight enough
    so it can be called without all the complicated logic in the garbage
    collector.
    """
    ok_operations = ['ptr_nonzero', 'ptr_eq', 'ptr_ne', 'free', 'same_as',
                     'direct_ptradd', 'force_cast', 'track_alloc_stop',
                     'raw_free', 'adr_eq', 'adr_ne',
                     'debug_print', 'stm_hashtable_free',
                     'stm_queue_free']

    def analyze_light_finalizer(self, graph):
        if getattr(graph.func, '_must_be_light_finalizer_', False):
            self._must_be_light = graph
            result = self.analyze_direct_call(graph)
            del self._must_be_light
            if result is self.top_result():
                msg = '%s\nIn %r' % (FinalizerError.__doc__, graph)
                # XXX temporary
                if self.translator.config.translation.stm:
                    from rpython.memory.gctransform.log import log
                    log.WARNING(msg)
                    return result
                raise FinalizerError(msg)
        else:
            result = self.analyze_direct_call(graph)
            #if result is self.top_result():
            #    log.red('old-style non-light finalizer: %r' % (graph,))
        return result

    def analyze_simple_operation(self, op, graphinfo):
        if op.opname in self.ok_operations:
            return self.bottom_result()
        if (op.opname.startswith('int_') or op.opname.startswith('float_')
            or op.opname.startswith('uint_') or op.opname.startswith('cast_')):
            return self.bottom_result()
        ## # All setfields are forbidden.  Commented out in test_finalizer too.
        ## # This is needed for STM and could maybe be justified in general.
        ## if op.opname == 'setfield' or op.opname == 'bare_setfield':
        ##     TP = op.args[2].concretetype
        ##     if not isinstance(TP, lltype.Ptr) or TP.TO._gckind == 'raw':
        ##         # primitive type
        ##         return self.bottom_result()
        # XXX: for STM, even primitive type getfield requires stm_read()
        #      and should therefore not be in light finalizers...
        #      getfield from 'raw' is fine (otherwise there would be a
        #      become_inevitable() op somewhere); also maybe getfield_gc
        #      on dying obj is fine (otherwise light finalizers are pretty
        #      useless).
        if op.opname == 'getfield':
            TP = op.result.concretetype
            if not isinstance(TP, lltype.Ptr) or TP.TO._gckind == 'raw':
                # primitive type
                return self.bottom_result()

        if not hasattr(self, '_must_be_light'):
            return self.top_result()
        msg = '%s\nFound this forbidden operation:\n%r\nin %r\nfrom %r' % (
            FinalizerError.__doc__, op, graphinfo, self._must_be_light)
        if self.translator.config.translation.stm:
            from rpython.memory.gctransform.log import log
            log.WARNING(msg)
            return self.top_result()
        raise FinalizerError(msg)
