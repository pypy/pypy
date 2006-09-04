
""" Debug transformer - attach source info to tracebacks generated
out of RPython code
"""

from pypy.translator import unsimplify, simplify
from pypy.translator.unsimplify import varoftype
from pypy.annotation import model as annmodel
from pypy.objspace.flow import model
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.ootypesystem import rclass
from pypy.translator.transformer.basictransform import BasicTransformer
from pypy.interpreter.pytraceback import offset2lineno

from types import FunctionType, MethodType

# this is RPython code which handles proper base elements for
# stack tracing
class TracebackHandler(object):
    def __init__(self):
        self.tb = []
    
    def enter(self, tb_str, data, filename, lineno):
        self.tb.append((tb_str, data, filename, lineno))
    
    def leave(self, tb_str):
        num = len(self.tb) - 1
        while num >= 0:
            if self.tb[num][0] == tb_str:
                self.tb = self.tb[:num]
            num -= 1
    
    def traceback(self):
        # cut of everything which is from entrypoint
        return self.tb

traceback_handler = TracebackHandler()

class DebugTransformer(BasicTransformer):
    def __init__(self, translator):
        BasicTransformer.__init__(self, translator)
        bk = self.bookkeeper
        self.register_helpers()
        self.instance_const = model.Constant(traceback_handler, \
            concretetype=bk.immutablevalue(traceback_handler))
        
    def register_helpers(self):
        return None
        for func_name, func_args in [("traceback", []), 
                ("enter", ["aa", "aa", "aa", 3]), ("leave", ["aa"])]:
            graph = self.flow_method(TracebackHandler, func_name, func_args)
            graph.explicit_traceback = True
    
    def transform_block(self, graph, block):
        next = []
        changed = False
        for op in block.operations:
            # XXX: We need to support indirect calls as well, but
            # just need to do it somehow differently
            if op.opname == 'simple_call' and \
                    isinstance(op.args[0], model.Constant) and \
                    isinstance(op.args[0].value, (FunctionType, MethodType)):
                # XXX or any other call
                opg, v1 = self.genop("getattr", [self.instance_const, 'enter'])
                fun_name = op.args[0].value.func_name
                data, filename, lineno = self.get_info(block, graph, op)
                opc, v2 = self.genop("simple_call", [v1, fun_name, data, \
                    filename, lineno])
                opgl, v3 = self.genop("getattr", [self.instance_const, 'leave'])
                oplc, v4 = self.genop("simple_call", [v3, fun_name])
                next += [opg, opc, op, opgl, oplc]
                changed = True
                #next.append(op)
            else:
                next.append(op)
        block.operations = next
        if changed:
            self.add_block(graph, block)
    
    def get_info(self, block, graph, op):
        """ Returns as much data as we can from our position
        """
        arglist = []
        for arg in op.args[1:]:
            if isinstance(arg, model.Constant):
                arglist.append(repr(arg.value))
            else:
                arglist.append(str(arg))
        call_str = "(%s)" % ", ".join(arglist)
        filename = getattr(graph, 'filename', '<unknown>')
        lineno = offset2lineno(graph.func.func_code, op.offset)
        return call_str, filename, lineno
        
    def transform_graph(self, graph):
        if getattr(graph, 'explicit_traceback', None):
            return
        
        for block in graph.iterblocks():
            self.transform_block(graph, block)
