#!/usr/bin/env pypy
from rpython.tool.logparser import extract_category
from rpython.tool.jitlogparser.parser import (
    parse_log_file, parse_addresses)

import argparse
import os


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
    log = parse_log_file(filename)

    addrs = []
    full_dumps = {}
    def address_cb(addr, stop_addr, bootstrap_addr, name, code_name):
        addrs.append((addr, stop_addr, bootstrap_addr, name, code_name))
        min_start_addr = full_dumps.setdefault(bootstrap_addr, addr)
        full_dumps[bootstrap_addr] = min(min_start_addr, addr)

    parse_addresses(extract_category(log, 'jit-backend-addr'),
                    callback=address_cb)

    with open('/tmp/perf-%s.map' % args.pid, 'w') as f:
        fmt = "%x %x JIT: %s - %s\n"
        for addr, stop_addr, bootstrap_addr, name, code_name in addrs:
            line = fmt % (addr, stop_addr - addr,
                          name, code_name)
            f.write(line)
            os.write(1, line)

        fmt = "%x %x JIT: loop bootstrapping %x\n"
        for bootstrap_addr, min_start_addr in full_dumps.items():
            if bootstrap_addr != min_start_addr:
                line = fmt % (bootstrap_addr,
                              min_start_addr - bootstrap_addr,
                              bootstrap_addr)
                f.write(line)
                os.write(1, line)


if __name__ == '__main__':
    main()
