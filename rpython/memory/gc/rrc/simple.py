from rpython.memory.gc.rrc.base import RawRefCountBaseGC

class RawRefCountSimpleGC(RawRefCountBaseGC):

    def major_collection_trace_step(self):
        self.p_list_old.foreach(self._major_trace, (False, False))
        return True