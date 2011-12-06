
from pypy.translator.tool.graphpage import GraphPage
from pypy.translator.tool.make_dot import DotGen
from pypy.jit.metainterp.history import Box
from pypy.jit.metainterp.resoperation import rop

class SubGraph:
    def __init__(self, suboperations):
        self.suboperations = suboperations
    def get_operations(self):
        return self.suboperations
    def get_display_text(self):
        return None

def display_loops(loops, errmsg=None, highlight_loops={}):
    graphs = [(loop, highlight_loops.get(loop, 0)) for loop in loops]    
    for graph, highlight in graphs:
        for op in graph.get_operations():
            if is_interesting_guard(op):
                graphs.append((SubGraph(op.getdescr()._debug_suboperations),
                               highlight))
    graphpage = ResOpGraphPage(graphs, errmsg)
    graphpage.display()

def is_interesting_guard(op):
    return hasattr(op.getdescr(), '_debug_suboperations')


class ResOpGraphPage(GraphPage):

    def compute(self, graphs, errmsg=None):
        resopgen = ResOpGen()
        for graph, highlight in graphs:
            if getattr(graph, 'token', None) is not None:
                resopgen.jumps_to_graphs[graph.token] = graph
            if getattr(graph, '_looptoken_number', None) is not None:
                resopgen.jumps_to_graphs[graph._looptoken_number] = graph
        
        for graph, highlight in graphs:
            resopgen.add_graph(graph, highlight)
        if errmsg:
            resopgen.set_errmsg(errmsg)
        self.source = resopgen.getsource()
        self.links = resopgen.getlinks()


class ResOpGen(object):
    CLUSTERING = True
    BOX_COLOR = (128, 0, 96)

    def __init__(self):
        self.graphs = []
        self.highlight_graphs = {}
        self.block_starters = {}    # {graphindex: {set-of-operation-indices}}
        self.all_operations = {}
        self.errmsg = None
        self.jumps_to_graphs = {}

    def op_name(self, graphindex, opindex):
        return 'g%dop%d' % (graphindex, opindex)

    def mark_starter(self, graphindex, opindex):
        self.block_starters[graphindex][opindex] = True

    def add_graph(self, graph, highlight=False):
        graphindex = len(self.graphs)
        self.graphs.append(graph)
        self.highlight_graphs[graph] = highlight
        for i, op in enumerate(graph.get_operations()):
            self.all_operations[op] = graphindex, i

    def find_starters(self):
        for graphindex in range(len(self.graphs)):
            self.block_starters[graphindex] = {0: True}
        for graphindex, graph in enumerate(self.graphs):
            last_was_mergepoint = False
            for i, op in enumerate(graph.get_operations()):
                if is_interesting_guard(op):
                    self.mark_starter(graphindex, i+1)
                if op.getopnum() == rop.DEBUG_MERGE_POINT:
                    if not last_was_mergepoint:
                        last_was_mergepoint = True
                        self.mark_starter(graphindex, i)
                else:
                    last_was_mergepoint = False

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
            for i, graph in enumerate(self.graphs):
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
        label = graph.get_display_text()
        if label is not None:
            colorindex = self.highlight_graphs.get(graph, 0)
            if colorindex == 1:
                fillcolor = '#f084c2'    # highlighted graph
            elif colorindex == 2:
                fillcolor = '#808080'    # invalidated graph
            else:
                fillcolor = '#84f0c2'    # normal color
            self.dotgen.emit_node(graphname, shape="octagon",
                                  label=label, fillcolor=fillcolor)
            self.pendingedges.append((graphname,
                                      self.op_name(graphindex, 0),
                                      {}))
        operations = graph.get_operations()
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
        while True:
            op = operations[opindex]
            lines.append(op.repr(graytext=True))
            if is_interesting_guard(op):
                tgt = op.getdescr()._debug_suboperations[0]
                tgt_g, tgt_i = self.all_operations[tgt]
                self.genedge((graphindex, opstartindex),
                             (tgt_g, tgt_i),
                             color='red')
            opindex += 1
            if opindex >= len(operations):
                break
            if opindex in block_starters:
                self.genedge((graphindex, opstartindex),
                             (graphindex, opindex))
                break
        if op.getopnum() == rop.JUMP:
            tgt_g = -1
            tgt = None
            tgt_number = getattr(op, '_jumptarget_number', None)
            if tgt_number is not None:
                tgt = self.jumps_to_graphs.get(tgt_number)
            else:
                tgt_descr = op.getdescr()
                if tgt_descr is None:
                    tgt_g = graphindex
                else:
                    tgt = self.jumps_to_graphs.get(tgt_descr.number)
                    if tgt is None:
                        tgt = self.jumps_to_graphs.get(tgt_descr)
            if tgt is not None:
                tgt_g = self.graphs.index(tgt)
            if tgt_g != -1:
                self.genedge((graphindex, opstartindex),
                             (tgt_g, 0),
                             weight="0")
        lines.append("")
        label = "\\l".join(lines)
        kwds = {}
        #if op in self.highlightops:
        #    kwds['color'] = 'red'
        #    kwds['fillcolor'] = '#ffe8e8'
        self.dotgen.emit_node(blockname, shape="box", label=label, **kwds)

    def getlinks(self):
        boxes = {}
        for op in self.all_operations:
            args = op.getarglist() + [op.result]
            for box in args:
                if getattr(box, 'is_box', False):
                    boxes[box] = True
        links = {}
        for box in boxes:
            links[str(box)] = repr(box), self.BOX_COLOR
        return links
