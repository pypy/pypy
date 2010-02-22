#!/usr/bin/env python
""" Usage: otherviewer.py loopfile
"""

import optparse
import sys
import re

import autopath
from pypy.translator.tool.graphpage import GraphPage
from pypy.translator.tool.make_dot import DotGen
from pypy.tool import logparser

class Page(GraphPage):
    def compute(self, graphs):
        dotgen = DotGen('trace')
        memo = set()
        for graph in graphs:
            graph.generate(dotgen, memo)
        self.source = dotgen.generate(target=None)

class BasicBlock(object):
    counter = 0

    def __init__(self, content):
        self.content = content
        self.no = self.counter
        self.__class__.counter += 1

    def name(self):
        return 'node' + str(self.no)

    def getcolor(self):
        if self.ratio > 8:
            return 'red'
        elif self.ratio > 5:
            return 'yellow'
        return 'green'

    def generate(self, dotgen, memo):
        dotgen.emit_node(self.name(), label=self.content,
                         shape='box', fillcolor=self.getcolor())

class FinalBlock(BasicBlock):
    def __init__(self, content, target):
        self.target = target
        BasicBlock.__init__(self, content)

    def postprocess(self, loops, memo):
        postprocess_loop(self.target, loops, memo)

    def generate(self, dotgen, memo):
        if self in memo:
            return
        memo.add(self)
        BasicBlock.generate(self, dotgen, memo)
        if self.target is not None:
            dotgen.emit_edge(self.name(), self.target.name())
            self.target.generate(dotgen, memo)

class Block(BasicBlock):
    def __init__(self, content, left, right):
        self.left = left
        self.right = right
        BasicBlock.__init__(self, content)

    def postprocess(self, loops, memo):
        postprocess_loop(self.left, loops, memo)
        postprocess_loop(self.right, loops, memo)

    def generate(self, dotgen, memo):
        if self in memo:
            return
        memo.add(self)
        BasicBlock.generate(self, dotgen, memo)
        dotgen.emit_edge(self.name(), self.left.name())
        dotgen.emit_edge(self.name(), self.right.name())
        self.left.generate(dotgen, memo)
        self.right.generate(dotgen, memo)

def split_one_loop(allloops, guard_s, guard_content):
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

def splitloops(loops):
    real_loops = []
    for loop in loops:
        firstline = loop[:loop.find("\n")]
        m = re.match('# Loop (\d+)', firstline)
        if m:
            no = int(m.group(1))
            assert len(real_loops) == no
            real_loops.append(FinalBlock(loop, None))
        else:
            m = re.search("bridge out of Guard (\d+)", firstline)
            assert m
            guard_s = 'Guard' + m.group(1)
            split_one_loop(real_loops, guard_s, loop)
    return real_loops

def postprocess_loop(loop, loops, memo):
    if loop in memo:
        return
    memo.add(loop)
    if loop is None:
        return
    m = re.search("debug_merge_point\('<code object (.*?)>", loop.content)
    if m is None:
        name = '?'
    else:
        name = m.group(1)
    opsno = loop.content.count("\n")
    lastline = loop.content[loop.content.rfind("\n", 0, len(loop.content) - 2):]
    m = re.search('descr=<Loop(\d+)', lastline)
    if m is not None:
        assert isinstance(loop, FinalBlock)
        loop.target = loops[int(m.group(1))]
    bcodes = loop.content.count('debug_merge_point')
    loop.content = "%s\n%d operations\n%d opcodes" % (name, opsno,
                                                      bcodes)
    loop.content += "\n" * (opsno / 100)
    if bcodes == 0:
        loop.ratio = opsno
    else:
        loop.ratio = float(opsno) / bcodes
    loop.postprocess(loops, memo)

def postprocess(loops):
    memo = set()
    for loop in loops:
        postprocess_loop(loop, loops, memo)

def main(loopfile):
    log = logparser.parse_log_file(loopfile)
    loops = logparser.extract_category(log, "jit-log-opt-")
    allloops = splitloops(loops)
    postprocess(allloops)
    Page(allloops).display()

if __name__ == '__main__':
    parser = optparse.OptionParser(usage=__doc__)
    options, args = parser.parse_args(sys.argv)
    if len(args) != 2:
        print __doc__
        sys.exit(1)
    main(args[1])
