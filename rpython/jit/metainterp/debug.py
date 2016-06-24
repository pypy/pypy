from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rlib.jitlog import _log_jit_counter

# YYY very minor leak -- we need the counters to stay alive
# forever, just because we want to report them at the end
# of the process

class DebugStaticData(object):
    def __init__(self):
        self.loop_run_counters = []

debug_sd = DebugStaticData()

DEBUG_COUNTER = lltype.Struct('DEBUG_COUNTER',
    # 'b'ridge, 'l'abel or # 'e'ntry point
    ('i', lltype.Signed),      # first field, at offset 0
    ('type', lltype.Char),
    ('number', lltype.Signed)
)

def flush_debug_counters():
    # this is always called, the jitlog knows if it is enabled
    length = len(debug_sd.loop_run_counters)
    for i in range(length):
        struct = debug_sd.loop_run_counters[i]
        _log_jit_counter(struct)
        # reset the counter, flush in a later point in time will
        # add up the counters!
        struct.i = 0
    # here would be the point to free some counters
    # see YYY comment above! but first we should run this every once in a while
    # not just when jitlog_disable is called
