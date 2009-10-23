
""" Helpers for parsing various outputs jit produces.
Notably:
1. Statistics of log.ops
2. Parsing what jitprof produces
"""

import re

REGEXES = [
    (('tracing_no', 'tracing_time'), '^Tracing:\s+([\d.]+)\s+([\d.]+)$'),
    (('backend_no', 'backend_time'), '^Backend:\s+([\d.]+)\s+([\d.]+)$'),
    (('asm_no', 'asm_time'), '^Running asm:\s+([\d.]+)\s+([\d.]+)$'),
    (('blackhole_no', 'blackhole_time'),
         '^Blackhole:\s+([\d.]+)\s+([\d.]+)$'),
    (None, '^TOTAL.*$'),
    (('ops.total',), '^ops:\s+(\d+)$'),
    (('ops.calls',), '^\s+calls:\s+(\d+)$'),
    (('ops.pure_calls',), '^\s+pure calls:\s+(\d+)$'),
    (('recorded_ops.total',), '^recorded ops:\s+(\d+)$'),
    (('recorded_ops.calls',), '^\s+calls:\s+(\d+)$'),
    (('recorded_ops.pure_calls',), '^\s+pure calls:\s+(\d+)$'),
    (('guards',), '^guards:\s+(\d+)$'),
    (('blackholed_ops.total',), '^blackholed ops:\s+(\d+)$'),
    (('blackholed_ops.pure_calls',), '^\s+pure calls:\s+(\d+)$'),
    (('opt_ops',), '^opt ops:\s+(\d+)$'),
    (('opt_guards',), '^opt guards:\s+(\d+)$'),
    (('forcings',), '^forcings:\s+(\d+)$'),
    (('trace_too_long',), '^trace too long:\s+(\d+)$'),
    (('bridge_abort',), '^bridge abort:\s+(\d+)$'),    
    ]

class Ops(object):
    total = 0
    calls = 0
    pure_calls = 0

class OutputInfo(object):
    tracing_no = 0
    tracing_time = 0.0
    backend_no = 0
    backend_time = 0.0
    asm_no = 0
    asm_time = 0.0
    guards = 0
    opt_ops = 0
    opt_guards = 0
    trace_too_long = 0
    bridge_abort = 0

    def __init__(self):
        self.ops = Ops()
        self.recorded_ops = Ops()
        self.blackholed_ops = Ops()

def parse_prof(output):
    lines = output.splitlines()
    # assert len(lines) == len(REGEXES)
    info = OutputInfo()
    for (attrs, regexp), line in zip(REGEXES, lines):
        m = re.match(regexp, line)
        assert m is not None, "Error parsing line: %s" % line
        if attrs:
            for i, a in enumerate(attrs):
                v = m.group(i + 1)
                if '.' in v:
                    v = float(v)
                else:
                    v = int(v)
                if '.' in a:
                    before, after = a.split('.')
                    setattr(getattr(info, before), after, v)
                else:
                    setattr(info, a, v)
    return info
