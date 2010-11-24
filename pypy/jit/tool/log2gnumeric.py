#! /usr/bin/env python
"""
Usage: log2gnumeric logfile

Produces a logfile.gnumeric file which contains the data extracted from the
logfile generated with the PYPYLOG env variable.

Currently, it expects log to contain the translation-task and gc-collect
categories.

You can freely edit the graph in log-template.gnumeric: this script will
create a new file replacing the 'translation-task' and 'gc-collect' sheets.
"""

import re, sys
import gzip


def main():
    logname = sys.argv[1]
    outname = logname + '.gnumeric'
    data = open(logname).read()
    data = data.replace('\n', '')
    maxclock = find_max_clock(data)
    #
    xml = gzip.open('log-template.gnumeric').read()
    xml = replace_sheet(xml, 'translation-task', tasks_rows(data))
    xml = replace_sheet(xml, 'gc-collect', gc_collect_rows(data))
    xml = replace_sheet(xml, 'memusage', memusage_rows(logname + '.memusage', maxclock))
    #
    out = gzip.open(outname, 'wb')
    out.write(xml)
    out.close()


def replace_sheet(xml, sheet_name, data):
    pattern = '<gnm:Sheet .*?<gnm:Name>%s</gnm:Name>.*?(<gnm:Cells>.*?</gnm:Cells>)'
    regex = re.compile(pattern % sheet_name, re.DOTALL)
    cells = gen_cells(data)
    match = regex.search(xml)
    if not match:
        print 'Cannot find sheet %s' % sheet_name
        return xml
    a, b = match.span(1)
    xml2 = xml[:a] + cells + xml[b:]
    return xml2

def gen_cells(data):
    # values for the ValueType attribute
    ValueType_Empty  = 'ValueType="10"'
    ValueType_Number = 'ValueType="40"'
    ValueType_String = 'ValueType="60"'
    #
    parts = []
    parts.append('<gnm:Cells>')
    for i, row in enumerate(data):
        for j, val in enumerate(row):
            if val is None:
                attr = ValueType_Empty
                val = ''
            elif isinstance(val, (int, long, float)):
                attr = ValueType_Number
            else:
                attr = ValueType_String
            cell = '        <gnm:Cell Row="%d" Col="%d" %s>%s</gnm:Cell>'
            parts.append(cell % (i, j, attr, val))
    parts.append('      </gnm:Cells>')
    return '\n'.join(parts)
    

def gc_collect_rows(data):
    s = r"""
----------- Full collection ------------------
\| used before collection:
\|          in ArenaCollection:      (\d+) bytes
\|          raw_malloced:            (\d+) bytes
\| used after collection:
\|          in ArenaCollection:      (\d+) bytes
\|          raw_malloced:            (\d+) bytes
\| number of major collects:         (\d+)
`----------------------------------------------
\[([0-9a-f]+)\] gc-collect\}"""
    #
    r = re.compile(s.replace('\n', ''))
    yield 'clock', 'gc-before', 'gc-after'
    for a,b,c,d,e,f in r.findall(data):
        yield int(f, 16), int(a)+int(b), int(c)+int(d)

def tasks_rows(data):
    s = r"""
\{translation-task
starting ([\w-]+)
\[([0-9a-f]+)\] translation-task\}"""
    #
    r = re.compile(s.replace('\n', ''))
    yield 'clock', None, 'task'
    for a,b in r.findall(data):
        yield int(b, 16), 1, a

def memusage_rows(filename, maxclock):
    try:
        lines = open(filename)
    except IOError:
        print 'Warning: cannot find file %s, skipping the memusage sheet'
        lines = []
    yield 'n', 'computed clock', 'VmRSS'
    for i, line in enumerate(lines):
        mem = int(line)
        yield i, "=max('gc-collect'!$A$1:$A$65536)*(A2/max($A$1:$A$65536)))", mem

def find_max_clock(data):
    s = r"\[([0-9a-f]+)\] "
    r = re.compile(s)
    clocks = [int(x, 16) for x in r.findall(data)]
    return max(clocks)

if __name__ == '__main__':
    main()
