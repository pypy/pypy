from pypy.rpython.l3interp import model
from pypy.rpython.memory import lladdress

class LLException(Exception):
    def __init__(self):
        pass

class LLInterpreter(object):
    def __init__(self, globals):
        self.globals = globals
    def eval_graph_int(self, graph, args):
        frame = LLFrame(graph, self)
        returnlink = frame.eval(args)
        return frame.get_int(0)

class LLFrame(object):
    def __init__(self, graph, lli):
        self.interp = lli
        self.graph = graph
        self.int_vars = [0] * graph.max_num_ints

    def eval(self, int_values):
        link = self.graph.startlink
        self.copy_startlink_vars(link, int_values)
        while not link.stop_graph_evaluation:
            link = self.eval_block(link.target)
            self.copy_link_vars(link)
        return link

    def eval_block(self, block):
        for op in block.operations:
#            print op.opimpl, op.result, op.args, self.int_vars
            op.opimpl(self, op.result, op.args)
        exitswitch = block.exitswitch
        if exitswitch >= 0:
            link = block.exits[self.int_vars[exitswitch]]
            return link
        return block.exits[0]
        
    def copy_startlink_vars(self, link, int_values):
#        print "copy_startlink_vars", int_values, link.move_int_registers
        if link.move_int_registers is None:
            return
        for i in range(0, len(link.move_int_registers), 2):
            source = link.move_int_registers[i]
            target = link.move_int_registers[i + 1]
            self.set_int(target, int_values[source])

    def copy_link_vars(self, link):
#        print "copy_link_vars", link.move_int_registers, self.int_vars
        if link.move_int_registers is None: 
            return
        for i in range(0, len(link.move_int_registers), 2):
            source = link.move_int_registers[i]
            target = link.move_int_registers[i + 1]
            self.set_int(target, self.get_int(source))

    def get_int(self, index):
        if index < 0:
            return self.graph.constants_int[~index]
        else:
            return self.int_vars[index]

    def set_int(self, index, val):
        self.int_vars[index] = val

    def op_int_add(self, result, args):
        int1 = self.get_int(args[0])
        int2 = self.get_int(args[1])
        self.set_int(result, int1 + int2)
        
    def op_int_is_true(self, result, args):
        int1 = self.get_int(args[0])
        self.set_int(result, bool(int1))

    def op_call_graph_int(self, result, args):
        graph = self.interp.globals.graphs[args[0]]
        concrete_args = [self.get_int(arg) for arg in args[1:]]
        r = self.interp.eval_graph_int(graph, concrete_args)
        self.set_int(result, r)
