from pypy.jit import hintmodel
from pypy.rpython.lltypesystem import lltype
from pypy.objspace.flow import model as flowmodel
from pypy.annotation import model as annmodel

# ___________________________________________________________

class HintTimeshift(object):
    
    def __init__(self, hannotator):
        self.hannotator = hannotator
        self.STATE = lltype.GcForwardReference()
        self.STATE_PTR = lltype.Ptr(self.STATE)
        self.REDBOX = lltype.GcForwardReference()
        self.REDBOX_PTR = lltype.Ptr(self.REDBOX)
        
    def timeshift(self):
        for graph in self.hannotator.translator.graphs:
            self.timeshift_graph(graph)

    def timeshift_graph(self, graph):
        for block in graph.iterblocks():
            self.timeshift_block(block)

    def timeshift_block(self, block):
        if not block.exits:   # ignore return/except blocks
            return  # XXX for now
        jitstate = flowmodel.Variable('jitstate')
        jitstate.concretetype = self.STATE_PTR

        self.varcolor = {}

        def introduce_var(v):
            if self.is_green(v):
                color = "green"
            else:
                color = "red"
                v.concretetype = self.REDBOX_PTR
            self.varcolor[v] = color

        for inputarg in block.inputargs:
            introduce_var(inputarg)

        # look for "red" operations
        newops = []
        for op in block.operations:
            green = True
            for arg in op.args:
                if self.varcolor.get(arg, "green") != "green":
                    green = False
            introduce_var(op.result)
            if green and self.varcolor[op.result] == "green":
                # XXX check for side effect ops
                newops.append(op)
                continue
            print "RED", op
            self.timeshift_op(op, newops)
            
        block.operations[:] = newops

        # pass 'jitstate' as an extra argument around the whole graph
        block.inputargs.insert(0, jitstate)
        for link in block.exits:
            link.args.insert(0, jitstate)

    def timeshift_op(self, op, newops):
        pass

    def is_green(self, var):
        hs_var = self.hannotator.binding(var)
        if hs_var == annmodel.s_ImpossibleValue:
            return True
        elif isinstance(hs_var, hintmodel.SomeLLAbstractConstant):
            return hs_var.eager_concrete or hs_var.is_fixed()
        else:
            return False
