from rpython.memory.gc.rrc.base import RawRefCountBaseGC

class RawRefCountSimpleGC(RawRefCountBaseGC):

    UNTRACK_TUPLES_DEFAULT = False

    def major_collection_trace_step(self):
        self._untrack_tuples()
        self.p_list_old.foreach(self._major_trace, (False, False))
        return True

    def visit_pyobj(self, gcobj):
        pass