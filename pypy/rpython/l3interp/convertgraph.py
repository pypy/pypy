from pypy.rpython.l3interp import model
from pypy.rpython.l3interp import l3interp
from pypy.objspace.flow import model as flowmodel

def convert(entrygraph):
    cvter = LL2L3Converter(entrygraph)
    return cvter.globals

class LL2L3Converter(object):
    def __init__(self, entrygraph):
        self.globals = model.Globals()
        self.convert_graph(entrygraph)

    def convert_graph(self, graph):
        graph_cvter = LL2L3GraphConverter(graph, self)
        l3graph = graph_cvter.l3graph
        self.globals.graphs.append(l3graph)
        return l3graph

class LL2L3GraphConverter(object):
    def __init__(self, graph, cvter):
        self.cvter = cvter
        self.graph = graph
        self.blocks_ll2l3 = {}
        self.constants_to_index = {}
        self.constants = []
        startlink = self.convert_startlink(graph.startblock)
        self.l3graph = model.Graph(graph.name, startlink)
        self.l3graph.constants_int = self.constants

    def convert_startlink(self, block):
        var_to_register = dict([(var, i)
                                    for i, var in enumerate(block.inputargs)])
        target = self.convert_block(block, var_to_register)
        startlink = model.Link(target)
        startlink.move_int_register = [i // 2
            for i in range(len(block.inputargs) * 2)]
        return startlink
        
    def convert_block(self, block, var_to_register):
        if block in self.blocks_ll2l3:
            return self.blocks_ll2l3[block]
        def get_reg_number(var):
            if var not in var_to_register:
                var_to_register[var] = len(var_to_register)
            return var_to_register[var]
        l3ops = []
        for op in block.operations:
            l3ops.append(self.convert_op(op, get_reg_number))
        assert block.exitswitch is None
        l3block = model.Block()
        self.blocks_ll2l3[block] = l3block
        l3block.exitswitch = model.ONE_EXIT
        l3block.exits = [self.convert_link(block.exits[0], var_to_register)]
        l3block.operations = l3ops
        return l3block

    def convert_link(self, link, var_to_register):
        if link.target is self.graph.returnblock:
            l3link = model.ReturnLink(var_to_register[link.args[0]])
            return l3link
        assert 0, "not yet implemented"

    def convert_op(self, op, get_reg_number):
        c_op = getattr(self, "op_" + op.opname, None)
        if c_op is not None:
            return c_op(op, get_reg_number)
        l3args = []
        for arg in op.args:
            if isinstance(arg, flowmodel.Variable):
                l3args.append(get_reg_number(arg))
            else:
                l3args.append(self.convert_const(arg))
        l3op = model.Operation(getattr(l3interp.LLFrame, "op_" + op.opname),
                               get_reg_number(op.result), l3args) 
        return l3op

    def convert_const(self, arg):
        arg = int(arg.value)
        if arg in self.constants_to_index:
            return self.constants_to_index[arg]
        index = len(self.constants)
        self.constants.append(arg)
        self.constants_to_index[arg] = index
        return ~index
