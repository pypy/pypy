#!/usr/bin/env pypy
from rpython.tool.logparser import extract_category
from rpython.tool.jitlogparser.storage import LoopStorage
from rpython.tool.jitlogparser.parser import adjust_bridges, import_log,\
    parse_log_counts, SimpleParser


import argparse
import os


loop_to_asm = {}

class SymbolMapParser(SimpleParser):
    def postprocess(self, loop, backend_dump=None, backend_tp=None,
                    dump_start=0, symbols=None):
        if backend_dump is not None:
            loop_to_asm[loop] = (dump_start+loop.operations[0].offset,
                                 loop.last_offset)#len(backend_dump.decode('hex')))

            #import pdb;pdb.set_trace()
            # print loop.comment
            # print hex(dump_start), loop.last_offset
            # print len(backend_dump), len(backend_dump.decode('hex'))

            # raw_asm = self._asm_disassemble(backend_dump.decode('hex'),
            #                                 backend_tp, dump_start)
            # start = 0
            # for elem in raw_asm:
            #     if len(elem.split("\t")) < 3:
            #         continue
            #     e = elem.split("\t")
            #     adr = e[0]
            #     if not start:
            #         start = int(adr.strip(":"), 16)
            #         break
            # print "real start", hex(start)
        #return SimpleParser.postprocess(self, loop, backend_dump, backend_tp, dump_start, symbols)
        return loop


def mangle_descr(descr):
    if descr.startswith('TargetToken('):
        return descr[len('TargetToken('):-1]
    if descr.startswith('<Guard'):
        return 'bridge-' + str(int(descr[len('<Guard0x'):-1], 16))
    if descr.startswith('<Loop'):
        return 'entry-' + descr[len('<Loop'):-1]
    return descr.replace(" ", '-')


def create_loop_dict(loops):
    d = {}
    for loop in loops:
        d[mangle_descr(loop.descr)] = loop
    return d


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
    storage.loop_dict = create_loop_dict(loops)

    for loop in storage.loops:
        if hasattr(loop, 'force_asm'):
            loop.force_asm(loop=loop)

        comment = loop.comment
        start, stop = comment.find('('), comment.rfind(')')
        loop.name = comment[start+1:stop]

    with open('/tmp/perf-%s.map' % args.pid, 'w') as f:
        for loop, (start, size) in loop_to_asm.items():
            line = "%x %x %s\n" % (start, size, loop.name)
            os.write(1, line)
            f.write(line)




if __name__ == '__main__':
    main()
