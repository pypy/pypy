from rpython.translator.backendopt.writeanalyze import WriteAnalyzer
from rpython.translator.stm.writebarrier import insert_stm_barrier
from rpython.translator.stm.inevitable import insert_turn_inevitable
from rpython.translator.stm.jitdriver import reorganize_around_jit_driver
from rpython.translator.stm.threadlocalref import transform_tlref
from rpython.translator.stm.breakfinder import TransactionBreakAnalyzer
from rpython.translator.c.support import log
from rpython.memory.gctransform.framework import CollectAnalyzer


class STMTransformer(object):

    def __init__(self, translator):
        self.translator = translator
        self.barrier_counts = {}

    def transform(self):
        assert not hasattr(self.translator, 'stm_transformation_applied')
        self.start_log()
        self.transform_jit_driver()
        self.transform_write_barrier()
        self.transform_turn_inevitable()
        self.print_logs()
        self.translator.stm_transformation_applied = True

    def transform_after_gc(self):
        self.transform_threadlocalref()
        self.print_logs_after_gc()

    def transform_write_barrier(self):
        self.write_analyzer = WriteAnalyzer(self.translator)
        self.collect_analyzer = CollectAnalyzer(self.translator)
        self.break_analyzer = TransactionBreakAnalyzer(self.translator)
        for graph in self.translator.graphs:
            insert_stm_barrier(self, graph)
        for key, value in sorted(self.barrier_counts.items()):
            log("%s: %d barriers" % (key, value[0]))
        del self.write_analyzer
        del self.collect_analyzer
        del self.break_analyzer

    def transform_turn_inevitable(self):
        for graph in self.translator.graphs:
            insert_turn_inevitable(graph)

    def transform_jit_driver(self):
        for graph in self.translator.graphs:
            reorganize_around_jit_driver(self, graph)

    def transform_threadlocalref(self):
        transform_tlref(self.translator)

    def start_log(self):
        log.info("Software Transactional Memory transformation")

    def print_logs(self):
        log.info("Software Transactional Memory transformation applied")

    def print_logs_after_gc(self):
        log.info("Software Transactional Memory transformation-after-gc done")
