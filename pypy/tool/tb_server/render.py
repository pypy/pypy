from pypy.tool.tb_server.server import TBRequestHandler
from xpy import html, xml

from std.magic import dyncode

import traceback

views = TBRequestHandler.views


class TracebackView:
    def __init__(self, tb):
        self.name = 'traceback%d' % len(views) 
        views[self.name] = self
        self.tb = tb 

    def render(self, args): 
        tag = html.html(
            html.head(),
            html.body(
                self.render_tb(args) 
            )
        )
        return tag.to_unicode()

    def render_tb(self, args):
        try:
            return self.render_tb_really(args)
        except:
            import sys, traceback
            lines = traceback.format_tb(sys.exc_info()[2])
            return html.pre(
                xml.escape(''.join(['Internal Rendering Error, traceback follows\n'] + lines)))
        
    def render_tb_really(self, args):
        lines = html.pre()
        for tb in dyncode.listtb(self.tb):
            filename = tb.tb_frame.f_code.co_filename 
            lineno = tb.tb_lineno
            name = tb.tb_frame.f_code.co_name
            lines.append('  File "%s", line %d, in %s\n'%(
                html.a(filename, href=filename).to_unicode().encode('utf-8'),
                lineno, name))
            lines.append(dyncode.getline(filename, lineno))
        return lines
            
            
            
            
                
