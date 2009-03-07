
from pypy.translator.tool.graphpage import GraphPage
from pypy.translator.tool.make_dot import DotGen
from pypy.jit.metainterp.history import Box


class ResOpGraphPage(GraphPage):

    def compute(self, graphs, errmsg=None, highlightops={}):
        resopgen = ResOpGen(highlightops)
        for graph in graphs:
            resopgen.add_graph(graph)
        if errmsg:
            resopgen.set_errmsg(errmsg)
        self.source = resopgen.getsource()
        self.links = resopgen.getlinks()


class ResOpGen(object):
    CLUSTERING = True
    BOX_COLOR = (128, 0, 96)

    def __init__(self, highlightops):
        self.graphs = []
        self.block_starters = {}    # {graphindex: {set-of-operation-indices}}
        self.all_operations = {}
        self.highlightops = highlightops
        self.errmsg = None

    def op_name(self, graphindex, opindex):
        return 'g%dop%d' % (graphindex, opindex)

    def mark_starter(self, graphindex, opindex):
        self.block_starters[graphindex][opindex] = True

    def add_graph(self, graph):
        graphindex = len(self.graphs)
        self.graphs.append(graph)
        for i, op in enumerate(graph.get_operations()):
            self.all_operations[op] = graphindex, i

    def find_starters(self):
        for graphindex in range(len(self.graphs)):
            self.block_starters[graphindex] = {0: True}
        for graphindex, graph in enumerate(self.graphs):
            prevop = None
            for i, op in enumerate(graph.get_operations()):
                for attrname, delta in [('jump_target', 0),
                                        ('_jump_target_prev', 1)]:
                    tgt = getattr(op, attrname, None)
                    if tgt is not None and tgt in self.all_operations:
                        tgt_g, tgt_i = self.all_operations[tgt]
                        self.mark_starter(tgt_g, tgt_i+delta)
                        self.mark_starter(graphindex, i+1)
                if (op in self.highlightops) != (prevop in self.highlightops):
                    self.mark_starter(graphindex, i)
                prevop = op

    def set_errmsg(self, errmsg):
        self.errmsg = errmsg

    def getsource(self):
        self.find_starters()
        self.pendingedges = []
        self.dotgen = DotGen('resop')
        self.dotgen.emit('clusterrank="local"')
        self.generrmsg()
        _prev = Box._extended_display
        try:
            Box._extended_display = False
            #if len(self.graphs) > 1:
            #    graphs = self.graphs[1:]
            #else:
            graphs = self.graphs
            for i, graph in enumerate(graphs):
                self.gengraph(graph, i)
        finally:
            Box._extended_display = _prev
        # we generate the edges at the end of the file; otherwise, and edge
        # could mention a node before it's declared, and this can cause the
        # node declaration to occur too early -- in the wrong subgraph.
        for frm, to, kwds in self.pendingedges:
            self.dotgen.emit_edge(frm, to, **kwds)
        return self.dotgen.generate(target=None)

    def generrmsg(self):
        if self.errmsg:
            self.dotgen.emit_node('errmsg', label=self.errmsg,
                                  shape="box", fillcolor="red")
            if self.graphs and self.block_starters[0]:
                opindex = max(self.block_starters[0])
                blockname = self.op_name(0, opindex)
                self.pendingedges.append((blockname, 'errmsg', {}))

    def getgraphname(self, graphindex):
        return 'graph%d' % graphindex

    def gengraph(self, graph, graphindex):
        graphname = self.getgraphname(graphindex)
        if self.CLUSTERING:
            self.dotgen.emit('subgraph cluster%d {' % graphindex)
        self.dotgen.emit_node(graphname, shape="octagon",
                              label=graph.get_display_text(),
                              fillcolor=graph.color)

        operations = graph.get_operations()
        if operations:
            self.pendingedges.append((graphname,
                                      self.op_name(graphindex, 0),
                                      {}))
            for opindex in self.block_starters[graphindex]:
                self.genblock(operations, graphindex, opindex)
        if self.CLUSTERING:
            self.dotgen.emit('}')   # closes the subgraph

    def genedge(self, frm, to, **kwds):
        self.pendingedges.append((self.op_name(*frm),
                                  self.op_name(*to),
                                  kwds))

    def genblock(self, operations, graphindex, opstartindex):
        if opstartindex >= len(operations):
            return
        blockname = self.op_name(graphindex, opstartindex)
        block_starters = self.block_starters[graphindex]
        lines = []
        opindex = opstartindex
        op = None
        while True:
            op = operations[opindex]
            lines.append(repr(op))
            #if op.opname == 'jump':
            #    self.genjump(blockname, op)
            for attrname, delta in [('jump_target', 0),
                                    ('_jump_target_prev', 1)]:
                tgt = getattr(op, attrname, None)
                if tgt is not None and tgt in self.all_operations:
                    tgt_g, tgt_i = self.all_operations[tgt]
                    kwds = {}
                    if op.opname == 'jump':
                        #kwds['constraint'] = 'false'
                        #kwds['headport'] = ':n'
                        pass
                    self.genedge((graphindex, opstartindex),
                                 (tgt_g, tgt_i+delta),
                                 color='red',
                                 **kwds)
            opindex += 1
            if opindex >= len(operations):
                break
            if opindex in block_starters:
                kwds = {}
                if op.opname == 'jump':
                    kwds['color'] = '#d0d0ff'
                self.genedge((graphindex, opstartindex),
                             (graphindex, opindex), **kwds)
                break
        lines.append("")
        label = "\\l".join(lines)
        kwds = {}
        if op in self.highlightops:
            kwds['color'] = 'red'
            kwds['fillcolor'] = '#ffe8e8'
        self.dotgen.emit_node(blockname, shape="box", label=label, **kwds)

    def genjump(self, srcblockname, op):
        graph1 = op.gettargetloop().graph
        try:
            graphindex = self.graphs.index(graph1)
        except ValueError:
            return
        self.pendingedges.append((srcblockname,
                                  self.op_name(graphindex, 0),
                                  {'color': graph1.color,
                                   #'headport': ':n',
                                   }))

    def getlinks(self):
        boxes = {}
        for op in self.all_operations:
            for box in op.args + op.results:
                if isinstance(box, Box):
                    boxes[box] = True
        links = {}
        for box in boxes:
            links[str(box)] = repr(box), self.BOX_COLOR
        return links
