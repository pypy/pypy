
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
SHOW_DEFAULT_LINES_OF_CODE = 0

from pypy.interpreter.pytraceback import offset2lineno
import traceback

def source_lines(graph, block, operindex=None, offset=None, long=False, \
    show_lines_of_code=SHOW_DEFAULT_LINES_OF_CODE):
    source = graph.source
    if block is not None:
        if block is graph.returnblock:
            return ['<return>']
    if source is not None:
        graph_lines = graph.source.split("\n")
        if offset is not None:
            linestart = offset2lineno(graph.func.func_code, offset)
            linerange = (linestart, linestart)
            here = None
        else:
            if block is None or not block.operations:
                return []
            def toline(operindex):
                return offset2lineno(graph.func.func_code, block.operations[operindex].offset)
            if operindex is None:
                linerange =  (toline(0), toline(-1))
                if not long:
                    return ['?']
                here = None
            else:
                operline = toline(operindex)
                if long:
                    linerange =  (toline(0), toline(-1))
                    here = operline
                else:
                    linerange = (operline, operline)
                    here = None
        lines = ["Happened at file %s line %d" % (graph.filename, here or linerange[0])]
        for n in range(max(0, linerange[0]-show_lines_of_code), \
            min(linerange[1]+1+show_lines_of_code, len(graph_lines)+graph.startline)):
            lines.append(graph_lines[n-graph.startline])
            if n == here:
                lines.append('^ HERE')
        return lines
    else:
        return ['no source!']

class FlowingError(Exception):
    pass

class AnnotatorError(Exception):
    pass

def gather_error(annotator, block, graph):
    msg = []
    msg.append('-+' * 30)
    msg.append("Operation cannot succeed")
    _, _, operindex = annotator.why_not_annotated[block][1].break_at
    oper = block.operations[operindex]
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
    if SHOW_TRACEBACK:
        msg.extend(traceback.format_exception(*annotator.why_not_annotated[block]))
    msg += source_lines(graph, block, operindex, long=True)
    return "\n".join(msg)

def format_blocked_annotation_error(annotator, blocked_blocks, graph):
    text = ""
    for block in blocked_blocks:
        text += gather_error(annotator, block, graph)
    return text
    
def format_someobject_error(annotator, position_key, what, s_value, called_from_graph):
    #block = getattr(annotator, 'flowin_block', None) or block
    msg = ["annotation of %r degenerated to SomeObject()" % (what,)]
    if position_key is not None:
        graph, block, operindex = position_key
        msg += source_lines(graph, block, operindex, long=True)
        
    if called_from_graph is not None:
        msg.append(".. called from %r" % (called_from_graph,))
    if s_value.origin is not None:
        msg.append(".. SomeObject() origin: %s" % (
            annotator.whereami(s_value.origin),))
    return "\n".join(msg)

def format_global_error(graph, offset, message):
    msg = []
    msg.append('-+' * 30)
    msg.append(message)
    msg += source_lines(graph, None, offset=offset)
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
