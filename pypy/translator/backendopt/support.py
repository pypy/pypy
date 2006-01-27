# logging

import py
from pypy.tool.ansi_print import ansi_log
log = py.log.Producer("backendopt")
py.log.setconsumer("backendopt", ansi_log)

def graph_operations(graph):
    for block in graph.iterblocks():
        for op in block.operations: 
            yield op

def all_operations(translator):
    for graph in translator.graphs:
        for block in graph.iterblocks():
            for op in block.operations: 
                yield op
