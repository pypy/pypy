
class STMTransformer(object):

    def __init__(self, translator):
        self.translator = translator

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
        from rpython.translator.backendopt.writeanalyze import WriteAnalyzer
        from rpython.translator.stm.writebarrier import insert_stm_barrier
        #
        self.write_analyzer = WriteAnalyzer(self.translator)
        for graph in self.translator.graphs:
            insert_stm_barrier(self, graph)
        del self.write_analyzer

    def transform_turn_inevitable(self):
        from rpython.translator.stm.inevitable import insert_turn_inevitable
        #
        for graph in self.translator.graphs:
            insert_turn_inevitable(graph)

    def transform_jit_driver(self):
        from rpython.translator.stm.jitdriver import reorganize_around_jit_driver
        #
        for graph in self.translator.graphs:
            reorganize_around_jit_driver(self, graph)

    def transform_threadlocalref(self):
        from rpython.translator.stm.threadlocalref import transform_tlref
        transform_tlref(self.translator)

    def start_log(self):
        from rpython.translator.c.support import log
        log.info("Software Transactional Memory transformation")

    def print_logs(self):
        from rpython.translator.c.support import log
        log.info("Software Transactional Memory transformation applied")

    def print_logs_after_gc(self):
        from rpython.translator.c.support import log
        log.info("Software Transactional Memory transformation-after-gc done")
