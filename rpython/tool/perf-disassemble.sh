#!/bin/bash
#
# Using this script instead of objdump enables perf to disassemble
# and annotate any JIT code (given a symbol file).
#
# To run perf without root:
#   kernel.perf_event_paranoid = -1
# To trace a process without root:
#   kernel.yama.ptrace_scope = 0
#
# Example usage:
# $ dolphin-emu -P /tmp -b -e $game
# $ perf top -p $(pidof dolphin-emu) --objdump ./Tools/perf-disassemble.sh

flavor=intel
#raw=r
raw=
src=

echo $@ > ~/bla

[[ "${@: -1}" != /tmp/perf-*.map ]] && { objdump "$@"; exit; }

pid=0
start=0
stop=0

for a in "$@"; do
    case "$a" in
        /tmp/perf-*.map)
          pid="${a#/tmp/perf-}"
          pid="${pid%.map}"
          shift
          ;;
        -M | --no-show-raw | -S | -C | -l | -d)
          shift
            ;;
        --start-address=*)
            start="${a##--start-address=}"
            shift
            ;;
        --stop-address=*)
            stop="${a##--stop-address=}"
            shift
            ;;
        -*)
            echo "Unknown parameter '$1'" >&2
            exit 1
            ;;
    esac
done
gdb -q -p $pid -ex "set disassembly $flavor" -ex "disas /$raw$src $start,$stop" -ex q -batch | sed "s/=>/  /g"
