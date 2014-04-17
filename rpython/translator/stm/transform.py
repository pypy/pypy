from rpython.translator.stm.inevitable import insert_turn_inevitable
from rpython.translator.stm.readbarrier import insert_stm_read_barrier
from rpython.translator.stm.jitdriver import reorganize_around_jit_driver
from rpython.translator.stm.threadlocalref import transform_tlref
from rpython.translator.stm.breakfinder import TransactionBreakAnalyzer
from rpython.translator.c.support import log


class STMTransformer(object):

    def __init__(self, translator):
        self.translator = translator

    def transform(self):
        assert not hasattr(self.translator, 'stm_transformation_applied')
        self.start_log(1)
        self.transform_jit_driver()
        self.transform_turn_inevitable()
        self.print_logs(1)
        self.translator.stm_transformation_applied = True

    def transform_after_gc(self):
        self.start_log(2)
        self.transform_threadlocalref()
        self.print_logs(2)

    def transform_after_complete(self):
        self.start_log(3)
        self.transform_read_barrier()
        self.print_logs(3)

    def transform_read_barrier(self):
        self.break_analyzer = TransactionBreakAnalyzer(self.translator)
        self.read_barrier_counts = 0
        for graph in self.translator.graphs:
            insert_stm_read_barrier(self, graph)
        log.info("%d read barriers inserted" % (self.read_barrier_counts,))
        del self.break_analyzer

    def transform_turn_inevitable(self):
        for graph in self.translator.graphs:
            insert_turn_inevitable(graph)

    def transform_jit_driver(self):
        for graph in self.translator.graphs:
            reorganize_around_jit_driver(self, graph)

    def transform_threadlocalref(self):
        transform_tlref(self.translator)

    def start_log(self, step):
        log.info("Software Transactional Memory transformation, step %d"
                 % step)

    def print_logs(self, step):
        log.info("Software Transactional Memory transformation, step %d, "
                 "applied" % step)
