from pypy.rpython.lltypesystem import lltype
from pypy.objspace.flow import model as flowmodel
from pypy.jit.rtimeshift import STATE_PTR, REDBOX_PTR 
from pypy.jit import rtimeshift
from pypy.jit.hintrtyper import HintRTyper, s_JITState, originalconcretetype

# ___________________________________________________________

class HintTimeshift(object):
    
    def __init__(self, hannotator, rtyper):
        self.hannotator = hannotator
        self.rtyper = rtyper
        self.hrtyper = HintRTyper(hannotator, self)

    def timeshift(self):
        for graph in self.hannotator.translator.graphs:
            self.timeshift_graph(graph)
        # RType the helpers found during timeshifting
        self.rtyper.specialize_more_blocks()

    def timeshift_graph(self, graph):
        originalblocks = list(graph.iterblocks())
        for block in originalblocks:
            self.pre_process_block(block)
        for block in originalblocks:
            self.timeshift_block(block)

    def pre_process_block(self, block):
        # pass 'jitstate' as an extra argument around the whole graph
        if block.operations != ():
            v_jitstate = flowmodel.Variable('jitstate')
            self.hannotator.bindings[v_jitstate] = s_JITState
            block.inputargs.insert(0, v_jitstate)
            for link in block.exits:
                # not for links going to the return/except block
                if link.target.operations != ():
                    link.args.insert(0, v_jitstate)

    def timeshift_block(self, block):
        self.hrtyper.specialize_block(block)

    def originalconcretetype(self, var):
        return originalconcretetype(self.hannotator.binding(var))
