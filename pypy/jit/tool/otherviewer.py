#!/usr/bin/env python
""" Usage: otherviewer.py loopfile
"""

import optparse
import sys
import re
import math

import autopath
from pypy.translator.tool.graphpage import GraphPage
from pypy.translator.tool.make_dot import DotGen
from pypy.tool import logparser

class SubPage(GraphPage):
    def compute(self, graph):
        dotgen = DotGen(str(graph.no))
        dotgen.emit_node(graph.name(), shape="box", label=graph.content)
        self.source = dotgen.generate(target=None)

class Page(GraphPage):
    def compute(self, graphs):
        dotgen = DotGen('trace')
        self.loops = set()
        for graph in graphs:
            graph.grab_loops(self.loops)
        self.links = {}
        self.cache = {}
        for loop in self.loops:
            loop.generate(dotgen)
            loop.getlinks(self.links)
            self.cache["loop" + str(loop.no)] = loop
        self.source = dotgen.generate(target=None)

    def followlink(self, label):
        return SubPage(self.cache[label])

BOX_COLOR = (128, 0, 96)

class BasicBlock(object):
    counter = 0
    startlineno = 0

    def __init__(self, content):
        self.content = content
        self.no = self.counter
        self.__class__.counter += 1

    def name(self):
        return 'node' + str(self.no)

    def getlinks(self, links):
        links[self.linksource] = self.name()

    def generate(self, dotgen):
        dotgen.emit_node(self.name(), label=self.header,
                         shape='box', fillcolor=get_gradient_color(self.ratio))

def get_gradient_color(ratio):
    if ratio == 0:
        return 'white'
    ratio = math.log(ratio)      # from -infinity to +infinity
    #
    # ratio: <---------------------- 1.8 --------------------->
    #        <-- towards green ---- YELLOW ---- towards red -->
    #
    ratio -= 1.8
    ratio = math.atan(ratio * 5) / (math.pi/2)
    # now ratio is between -1 and 1
    if ratio >= 0.0:
        # from yellow (ratio=0) to red (ratio=1)
        return '#FF%02X00' % (int((1.0-ratio)*255.5),)
    else:
        # from yellow (ratio=0) to green (ratio=-1)
        return '#%02XFF00' % (int((1.0+ratio)*255.5),)


class FinalBlock(BasicBlock):
    def __init__(self, content, target):
        self.target = target
        BasicBlock.__init__(self, content)

    def postprocess(self, loops, memo):
        postprocess_loop(self.target, loops, memo)

    def grab_loops(self, loops):
        if self in loops:
            return
        loops.add(self)
        if self.target is not None:
            self.target.grab_loops(loops)

    def generate(self, dotgen):
        BasicBlock.generate(self, dotgen)
        if self.target is not None:
            dotgen.emit_edge(self.name(), self.target.name())

class Block(BasicBlock):
    def __init__(self, content, left, right):
        self.left = left
        self.right = right
        BasicBlock.__init__(self, content)

    def postprocess(self, loops, memo):
        postprocess_loop(self.left, loops, memo)
        postprocess_loop(self.right, loops, memo)

    def grab_loops(self, loops):
        if self in loops:
            return
        loops.add(self)
        self.left.grab_loops(loops)
        self.right.grab_loops(loops)

    def generate(self, dotgen):
        BasicBlock.generate(self, dotgen)
        dotgen.emit_edge(self.name(), self.left.name())
        dotgen.emit_edge(self.name(), self.right.name())

def split_one_loop(allloops, guard_s, guard_content, lineno):
    for i, loop in enumerate(allloops):
        content = loop.content
        pos = content.find(guard_s + '>')
        if pos != -1:
            newpos = content.rfind("\n", 0, pos)
            oldpos = content.find("\n", pos)
            assert newpos != -1
            if oldpos == -1:
                oldpos = len(content)
            allloops[i] = Block(content[:oldpos],
                                FinalBlock(content[oldpos:], None),
                                FinalBlock(content[newpos + 1:oldpos] + "\n" +
                                           guard_content, None))
            allloops[i].guard_s = guard_s
            allloops[i].startlineno = loop.startlineno
            allloops[i].left.startlineno = loop.startlineno + content.count("\n", 0, pos)
            allloops[i].right.startlineno = lineno

def splitloops(loops):
    real_loops = []
    counter = 1
    for loop in loops:
        firstline = loop[:loop.find("\n")]
        m = re.match('# Loop (\d+)', firstline)
        if m:
            no = int(m.group(1))
            assert len(real_loops) == no
            real_loops.append(FinalBlock(loop, None))
            real_loops[-1].startlineno = counter
        else:
            m = re.search("bridge out of Guard (\d+)", firstline)
            assert m
            guard_s = 'Guard' + m.group(1)
            split_one_loop(real_loops, guard_s, loop, counter)
        counter += loop.count("\n") + 2
    return real_loops

def postprocess_loop(loop, loops, memo):
    if loop in memo:
        return
    memo.add(loop)
    if loop is None:
        return
    m = re.search("debug_merge_point\('<code object (.*?)> (.*?)'", loop.content)
    if m is None:
        name = '?'
    else:
        name = m.group(1) + " " + m.group(2)
    opsno = loop.content.count("\n")
    lastline = loop.content[loop.content.rfind("\n", 0, len(loop.content) - 2):]
    m = re.search('descr=<Loop(\d+)', lastline)
    if m is not None:
        assert isinstance(loop, FinalBlock)
        loop.target = loops[int(m.group(1))]
    bcodes = loop.content.count('debug_merge_point')
    loop.linksource = "loop" + str(loop.no)
    loop.header = "%s loop%d\n%d operations\n%d opcodes" % (name, loop.no, opsno,
                                                          bcodes)
    loop.header += "\n" * (opsno / 100)
    if bcodes == 0:
        loop.ratio = opsno
    else:
        loop.ratio = float(opsno) / bcodes
    loop.content = "Logfile at %d" % loop.startlineno
    loop.postprocess(loops, memo)

def postprocess(loops):
    memo = set()
    for loop in loops:
        postprocess_loop(loop, loops, memo)

def main(loopfile, view=True):
    log = logparser.parse_log_file(loopfile)
    loops = logparser.extract_category(log, "jit-log-opt-")
    allloops = splitloops(loops)
    postprocess(allloops)
    if view:
        Page(allloops).display()

if __name__ == '__main__':
    parser = optparse.OptionParser(usage=__doc__)
    options, args = parser.parse_args(sys.argv)
    if len(args) != 2:
        print __doc__
        sys.exit(1)
    main(args[1])
