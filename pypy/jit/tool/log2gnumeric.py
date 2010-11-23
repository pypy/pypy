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
    xml = gzip.open('log-template.gnumeric').read()
    #
    xml = replace_sheet(xml, 'translation-task', tasks_rows(data))
    xml = replace_sheet(xml, 'gc-collect', gc_collect_rows(data))
    #
    out = gzip.open(outname, 'wb')
    out.write(xml)
    out.close()


def replace_sheet(xml, sheet_name, data):
    pattern = '(<gnm:Sheet .*?<gnm:Name>%s</gnm:Name>.*?)<gnm:Cells>.*?</gnm:Cells>'
    regex = re.compile(pattern % sheet_name, re.DOTALL)
    cells = gen_cells(data)
    xml2 = regex.sub(r'\1%s' % cells, xml)
    assert xml != xml2
    return xml2

def gen_cells(data):
    parts = []
    parts.append('      <gnm:Cells>')
    for i, row in enumerate(data):
        for j, val in enumerate(row):
            cell = '         <gnm:Cell Row="%d" Col="%d">%s</gnm:Cell>'
            parts.append(cell % (i, j, val))
    parts.append('      </gnm:Cells>')
    return ''.join(parts)
    

def gc_collect_rows(data, show_header=True):
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
    for a,b,c,d,e,f in r.findall(data):
        yield int(f, 16), int(a)+int(b), int(c)+int(d)

def tasks_rows(data):
    s = r"""
\{translation-task
starting ([\w-]+)
\[([0-9a-f]+)\] translation-task\}"""
    #
    r = re.compile(s.replace('\n', ''))
    for a,b in r.findall(data):
        yield int(b, 16), 1, a


if __name__ == '__main__':
    main()
