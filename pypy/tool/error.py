
""" error handling features, just a way of displaying errors
"""

from pypy.tool.ansi_print import ansi_log, raise_nicer_exception
from pypy.objspace.flow.model import Constant, Variable

import py
log = py.log.Producer("annrpython") 
py.log.setconsumer("annrpython", ansi_log) 

SHOW_TRACEBACK = False
SHOW_ANNOTATIONS = True

from pypy.interpreter.pytraceback import offset2lineno
import traceback

def gather_error(annotator, block, graph):
    oper = block.operations[annotator.why_not_annotated[block][1].break_at[2]]
    offset = oper.offset
    lineno = offset2lineno(graph.func.func_code, offset)
    msg = []
    msg.append('-+' * 30)
    msg.append("Operation cannot succeed")
    msg.append(" " + str(oper))
    if SHOW_ANNOTATIONS:
        msg.append("Known variable annotations:")
        for arg in oper.args + [oper.result]:
            if isinstance(arg, Variable):
                try:
                    msg.append(" " + str(arg) + " = " + str(annotator.binding(arg)))
                except KeyError:
                    pass
        msg.append("")
    msg.append("Happened at file %s line %d" % (graph.filename, lineno))    
    if SHOW_TRACEBACK:
        msg.extend(traceback.format_exception(*annotator.why_not_annotated[block]))
    graph_lines = graph.source.split("\n")
    graph_lineno = lineno - graph.startline
    msg.append("")
    str_num = (len(graph_lines[graph_lineno]) - 6)/2
    for num, line in enumerate(graph_lines + [""]):
        msg.append(line)
        if num == graph_lineno:
            msg.append("^" * str_num + " HERE " + "^" * str_num)
    msg.append('-+' * 30)
    return "\n".join(msg)

def format_someobject_error(annotator, graph, block):
    block_start = offset2lineno(graph.func.func_code, block.operations[0].offset) - graph.startline - 1
    block_end = offset2lineno(graph.func.func_code, block.operations[-1].offset) - graph.startline - 1
    msg = []
    graph_lines = graph.source.split("\n")
    msg.append("Somewhere here:")
    for num, line in enumerate(graph_lines + [""]):
        msg.append(line)
        if num == block_start:
            str_num = (len(graph_lines[num + 1]) - 6)/2
            msg.append("-"*str_num + " BELOW " + "-"*str_num)
        elif num == block_end:
            str_num = (len(graph_lines[num]) - 6)/2
            msg.append("^"*str_num + " ABOVE " + "^"*str_num)
    return "\n".join(msg)

def format_annotation_error(annotator, blocked_blocks, graph):
    text = ""
    for block in blocked_blocks:
        text += gather_error(annotator, block, graph)
    return text
