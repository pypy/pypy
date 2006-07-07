
""" error handling features, just a way of displaying errors
"""

from pypy.tool.ansi_print import ansi_log, raise_nicer_exception
from pypy.objspace.flow.model import Constant, Variable
import sys

import py
log = py.log.Producer("error") 
py.log.setconsumer("error", ansi_log) 

SHOW_TRACEBACK = False
SHOW_ANNOTATIONS = True

from pypy.interpreter.pytraceback import offset2lineno
import traceback

class AnnotatorError(Exception):
    pass

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
    add_graph(msg, graph, lineno)
    return "\n".join(msg)

def add_graph(msg, graph, lineno):
    graph_lines = graph.source.split("\n")
    graph_lineno = lineno - graph.startline
    msg.append("")
    str_num = (len(graph_lines[graph_lineno]) - 6)/2
    for num, line in enumerate(graph_lines + [""]):
        msg.append(line)
        if num == graph_lineno:
            msg.append("^" * str_num + " HERE " + "^" * str_num)
    msg.append('-+' * 30)
    
def format_someobject_error(annotator, graph, block, what):
    #block = getattr(annotator, 'flowin_block', None) or block
    offset1 = offset2 = 0
    if block.operations:
        offset1 = block.operations[0].offset
        offset2 = block.operations[-1].offset
        
    block_start = offset2lineno(graph.func.func_code, offset1) - graph.startline - 1
    block_end = offset2lineno(graph.func.func_code, offset2) - graph.startline - 1
    msg = ["annotation of %r degenerated to SomeObject()" % (what,)]
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

def format_global_error(graph, offset, message):
    msg = []
    msg.append('-+' * 30)
    lineno = offset2lineno(graph.func.func_code, offset)
    msg.append(message)
    add_graph(msg, graph, lineno)
    return "\n".join(msg)

def debug(drv):
    # XXX unify some code with pypy.translator.goal.translate
    from pypy.translator.tool.pdbplus import PdbPlusShow
    from pypy.translator.driver import log
    t = drv.translator
    class options:
        huge = 100

    tb = None
    import traceback
    errmsg = ["Error:\n"]
    exc, val, tb = sys.exc_info()
    
    errmsg.extend([" %s" % line for line in traceback.format_exception(exc, val, [])])
    block = getattr(val, '__annotator_block', None)
    if block:
        class FileLike:
            def write(self, s):
                errmsg.append(" %s" % s)
        errmsg.append("Processing block:\n")
        t.about(block, FileLike())
    log.ERROR(''.join(errmsg))

    log.event("start debugger...")

    def server_setup(port=None):
        if port is not None:
            from pypy.translator.tool.graphserver import run_async_server
            serv_start, serv_show, serv_stop = self.async_server = run_async_server(t, options, port)
            return serv_start, serv_show, serv_stop
        else:
            from pypy.translator.tool.graphserver import run_server_for_inprocess_client
            return run_server_for_inprocess_client(t, options)

    pdb_plus_show = PdbPlusShow(t)
    pdb_plus_show.start(tb, server_setup, graphic=True)
