from rpython.translator.stm.inevitable import insert_turn_inevitable
from rpython.translator.stm.readbarrier import insert_stm_read_barrier
from rpython.translator.stm.breakfinder import TransactionBreakAnalyzer
from rpython.translator.c.support import log


class STMTransformer(object):

    def __init__(self, translator):
        self.translator = translator

    def transform(self):
        assert not hasattr(self.translator, 'stm_transformation_applied')
        self.start_log(1)
        self.transform_turn_inevitable()
        self.print_logs(1)
        self.translator.stm_transformation_applied = True

    def transform_after_gc(self):
        pass     # nothing to do here in the current version

    def transform_after_complete(self):
        self.start_log(2)
        self.transform_read_barrier()
        self.print_logs(2)

    def transform_read_barrier(self):
        self.read_barrier_counts = 0

        self.break_analyzer = TransactionBreakAnalyzer(self.translator)
        for graph in self.translator.graphs:
            insert_stm_read_barrier(self, graph)
        del self.break_analyzer

        log.info("%d read barriers inserted" % (self.read_barrier_counts,))

    def transform_turn_inevitable(self):
        self.break_analyzer = TransactionBreakAnalyzer(self.translator)
        for graph in self.translator.graphs:
            insert_turn_inevitable(self, graph)
        del self.break_analyzer


    def start_log(self, step):
        log.info("Software Transactional Memory transformation, step %d"
                 % step)

    def print_logs(self, step):
        log.info("Software Transactional Memory transformation, step %d, "
                 "applied" % step)
