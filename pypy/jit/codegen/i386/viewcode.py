#! /usr/bin/env python
"""
Viewer for the CODE_DUMP output of compiled programs generating code.

Try:
    ./viewcode.py dumpfile.txt
or
    /tmp/usession-xxx/testing_1/testing_1 -var 4  2>&1  |  ./viewcode.py
"""

import autopath
import operator, sys, os, re, py

# don't use pypy.tool.udir here to avoid removing old usessions which
# might still contain interesting executables
udir = py.path.local.make_numbered_dir(prefix='viewcode-', keep=2)
tmpfile = str(udir.join('dump.tmp'))

# ____________________________________________________________
# Some support code from Psyco.  There is more over there,
# I am porting it in a lazy fashion...  See py-utils/xam.py

# the disassembler to use. 'objdump' writes GNU-style instructions.
# 'ndisasm' uses Intel syntax.  XXX ndisasm output parsing is missing...

objdump = 'objdump -b binary -m i386 --adjust-vma=%(origin)d -D %(file)s'
#objdump = 'ndisasm -o %(origin)d -u %(file)s'
if sys.platform == "win32":
    XXX   # lots more in Psyco

def machine_code_dump(data, originaddr):
    f = open(tmpfile, 'wb')
    f.write(data)
    f.close()
    g = os.popen(objdump % {'file': tmpfile, 'origin': originaddr}, 'r')
    result = g.readlines()
    g.close()
    return result

re_addr = re.compile(r'[\s,$]0x([0-9a-fA-F]+)')

def lineaddresses(line):
    result = []
    i = 0
    while 1:
        match = re_addr.search(line, i)
        if not match:
            break
        i = match.end()
        addr = long(match.group(1), 16)
        result.append(addr)
    return result

# ____________________________________________________________

class CodeRange(object):
    fallthrough = False

    def __init__(self, addr, data):
        self.addr = addr
        self.data = data

    def update(self, other):
        if other.addr < self.addr:
            delta = self.addr - other.addr
            self.addr -= delta
            self.offset += delta
            self.data = '\x00'*delta + self.data
        ofs1 = other.addr - self.addr
        ofs2 = ofs1 + len(other.data)
        self.data = self.data[:ofs1] + other.data + self.data[ofs2:]

    def cmpop(op):
        def _cmp(self, other):
            if not isinstance(other, CodeRange):
                return NotImplemented
            return op((self.addr, self.data), (other.addr, other.data))
        return _cmp
    __lt__ = cmpop(operator.lt)
    __le__ = cmpop(operator.le)
    __eq__ = cmpop(operator.eq)
    __ne__ = cmpop(operator.ne)
    __gt__ = cmpop(operator.gt)
    __ge__ = cmpop(operator.ge)
    del cmpop

    def disassemble(self):
        if not hasattr(self, 'text'):
            lines = machine_code_dump(self.data, self.addr)
            self.text = ''.join(lines[6:])   # drop some objdump cruft
        return self.text

    def findjumps(self):
        text = self.disassemble()
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if '\tj' not in line: # poor heuristic to recognize lines that
                continue          # could be jump instructions
            addrs = list(lineaddresses(line))
            if not addrs:
                continue
            addr = addrs[-1]
            yield i, addr
        if self.fallthrough:
            yield len(lines), self.addr + len(self.data)


class World(object):

    def __init__(self):
        self.ranges = []
        self.labeltargets = {}
        self.jumps = {}

    def parse(self, f):
        for line in f:
            if line.startswith('CODE_DUMP '):
                pieces = line.split()
                assert pieces[1].startswith('@')
                assert pieces[2].startswith('+')
                baseaddr = long(pieces[1][1:], 16) & 0xFFFFFFFFL
                offset = int(pieces[2][1:])
                addr = baseaddr + offset
                data = pieces[3].replace(':', '').decode('hex')
                coderange = CodeRange(addr, data)
                # XXX sloooooooow!
                for r in self.ranges:
                    if addr < r.addr+len(r.data) and r.addr < addr+len(data):
                        r.update(coderange)
                        break
                else:
                    self.ranges.append(coderange)
        # find cross-references between blocks
        for r in self.ranges:
            for lineno, targetaddr in r.findjumps():
                self.labeltargets[targetaddr] = True
        # split blocks at labeltargets
        # XXX slooooow!
        t = self.labeltargets
        print t
        for r in self.ranges:
            print r.addr, r.addr + len(r.data)
            for i in range(r.addr + 1, r.addr + len(r.data)):
                if i in t:
                    print i
                    ofs = i - r.addr
                    self.ranges.append(CodeRange(i, r.data[ofs:]))
                    r.data = r.data[:ofs]
                    r.fallthrough = True
                    del r.text
                    break
        # hack hack hacked

    def show(self):
        g1 = Graph('codedump')
        for r in self.ranges:
            text, width = tab2columns(r.disassemble())
            text = '0x%x\n\n%s' % (r.addr, text)
            g1.emit_node('N_%x' % r.addr, shape="box", label=text,
                         width=str(width*0.125))
            for lineno, targetaddr in r.findjumps():
                g1.emit_edge('N_%x' % r.addr, 'N_%x' % targetaddr)
        g1.display()


def tab2columns(text):
    lines = text.split('\n')
    columnwidth = []
    for line in lines:
        columns = line.split('\t')
        while len(columnwidth) < len(columns):
            columnwidth.append(0)
        for i, s in enumerate(columns):
            width = len(s.strip())
            if not s.endswith(':'):
                width += 2
            columnwidth[i] = max(columnwidth[i], width)
    result = []
    for line in lines:
        columns = line.split('\t')
        text = []
        for width, s in zip(columnwidth, columns):
            text.append(s.strip().ljust(width))
        result.append(' '.join(text))
    if result:
        totalwidth = len(result[0])
    else:
        totalwidth = 1
    return '\\l'.join(result), totalwidth

# ____________________________________________________________
# XXX pasted from
# http://codespeak.net/svn/user/arigo/hack/misc/graphlib.py
# but needs to be a bit more subtle later

from pypy.translator.tool.make_dot import DotGen
from pypy.translator.tool.pygame.graphclient import display_layout

class Graph(DotGen):

    def highlight(self, word, text, linked_to=None):
        if not hasattr(self, '_links'):
            self._links = {}
            self._links_to = {}
        self._links[word] = text
        if linked_to:
            self._links_to[word] = linked_to

    def display(self):
        "Display a graph page locally."
        display_layout(_Page(self))


class NoGraph(Exception):
    pass

class _Page:
    def __init__(self, graph_builder):
        if callable(graph_builder):
            graph = graph_builder()
        else:
            graph = graph_builder
        if graph is None:
            raise NoGraph
        self.graph_builder = graph_builder

    def content(self):
        return _PageContent(self.graph_builder)

class _PageContent:
    fixedfont = True

    def __init__(self, graph_builder):
        if callable(graph_builder):
            graph = graph_builder()
        else:
            graph = graph_builder
        assert graph is not None
        self.graph_builder = graph_builder
        self.graph = graph
        self.links = getattr(graph, '_links', {})
        if not hasattr(graph, '_source'):
            graph._source = graph.generate(target=None)
        self.source = graph._source

    def followlink(self, link):
        try:
            return _Page(self.graph._links_to[link])
        except NoGraph:
            return _Page(self.graph_builder)

# ____________________________________________________________

if __name__ == '__main__':
    if len(sys.argv) == 1:
        f = sys.stdin
    else:
        f = open(sys.argv[1], 'r')
    world = World()
    world.parse(f)
    world.show()
