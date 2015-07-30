#!/usr/bin/env pypy
from rpython.tool.logparser import extract_category
from rpython.tool.jitlogparser.storage import LoopStorage
from rpython.tool.jitlogparser.parser import import_log,\
    parse_log_counts, SimpleParser

from collections import OrderedDict
import argparse
import os

extended_ranges = {}

class SymbolMapParser(SimpleParser):
    def postprocess(self, loop, backend_dump=None, backend_tp=None,
                    dump_start=0, symbols=None):
        if backend_dump is not None:
            loop.backend_dump = backend_dump
            loop.dump_start = dump_start

            start_offset = loop.operations[0].offset
            last_offset = loop.operations[-1].offset
            loop.range = (start_offset, last_offset)

            prev = extended_ranges.get(backend_dump, loop.range)
            extended_ranges[backend_dump] = (min(start_offset, prev[0]),
                                             max(last_offset, prev[1]))
        return loop




def main():
    parser = argparse.ArgumentParser(
        description = "creates a /tmp/perf-<pid>.map file from a pypylog",
        epilog = "./make_perf_map_from_pypylog.py -l log.pypylog -p 1234",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("-l", "--log", help="specify existing logfile")
    parser.add_argument("-p", "--pid", help="specify original PID (process id)")
    args = parser.parse_args()
    if args.log is None:
        print("--log is required")
        return
    if args.pid is None:
        print("--pid is required")
        return

    filename = args.log
    extra_path = os.path.dirname(filename)

    storage = LoopStorage(extra_path)
    log, loops = import_log(filename, SymbolMapParser)
    parse_log_counts(extract_category(log, 'jit-backend-count'), loops)
    storage.loops = loops

    for loop in storage.loops:
        if hasattr(loop, 'force_asm'):
            loop.force_asm(loop=loop)

        comment = loop.comment
        start, stop = comment.find('('), comment.rfind(')')
        count = loop.count if hasattr(loop, 'count') else '?'
        loop.name = comment[start+1:stop] + " (ran %sx)" % count

    with open('/tmp/perf-%s.map' % args.pid, 'w') as f:
        fmt = "%x %x %s\n"

        for loop in storage.loops:
            if hasattr(loop, 'backend_dump'):
                lower, upper = loop.range
                min_offset, max_offset = extended_ranges[loop.backend_dump]
                if lower == min_offset:
                    # include loop-setup
                    lower = 0
                if upper == max_offset:
                    # include loop-teardown
                    upper = loop.last_offset

                line = fmt % (lower + loop.dump_start,
                              upper - lower,
                              "JIT: " + loop.name)
                f.write(line)
                os.write(1, line)





if __name__ == '__main__':
    main()
