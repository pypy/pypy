#!/usr/bin/env pypy
from rpython.tool.logparser import extract_category
from rpython.tool.jitlogparser.storage import LoopStorage
from rpython.tool.jitlogparser.parser import import_log,\
    parse_log_counts, SimpleParser

from collections import OrderedDict
import argparse
import os


loop_to_asm = OrderedDict()
global_dumps = OrderedDict()

class SymbolMapParser(SimpleParser):
    def postprocess(self, loop, backend_dump=None, backend_tp=None,
                    dump_start=0, symbols=None):
        if backend_dump is not None:
            if dump_start not in global_dumps:
                global_dumps[dump_start] = (loop, backend_dump)
            start_offset = loop.operations[0].offset
            loop_to_asm[loop] = (dump_start + start_offset,
                                 loop.last_offset - start_offset)
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
        lines = []
        fmt = "%x %x %s\n"
        # fine-grained first seems to work:
        # output last entries first
        for loop, (start, size) in reversed(loop_to_asm.items()):
            lines.append(fmt % (start, size,
                                "JIT: " + loop.name))

        # coarse loop-pieces: they include e.g. frame-reallocation
        # in compiled bridge (whatever jitviewer also doesn't show
        # but is still part of a loop)
        for start, (loop, dump) in reversed(global_dumps.items()):
            lines.append(fmt % (start, len(dump.decode('hex')),
                                "JIT-ext: " + loop.name))

        for line in lines:
            os.write(1, line)
            f.write(line)





if __name__ == '__main__':
    main()
