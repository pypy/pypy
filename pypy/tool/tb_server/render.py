from pypy.tool.tb_server.server import TBRequestHandler
from xpy import html, xml

from std.magic import dyncode

import traceback

views = TBRequestHandler.views

class Renderer:
    def render(self, args):
        try:
            inner = self.render_self(args)
        except:
            import sys, traceback
            lines = traceback.format_exception(*sys.exc_info())
            inner =  html.pre(
                xml.escape(''.join(
                ['Internal Rendering Error, traceback follows\n'] + lines)))
            
        tag = html.html(
            html.head(),
            html.body(
                inner
            )
        )
        return tag.to_unicode()
    

class TracebackView(Renderer):
    def __init__(self, tb):
        self.name = 'traceback%d' % len(views) 
        views[self.name] = self
        self.tb = tb 
        
    def render_self(self, args):
        lines = html.pre()
        for tb in dyncode.listtb(self.tb):
            filename = tb.tb_frame.f_code.co_filename 
            lineno = tb.tb_lineno
            name = tb.tb_frame.f_code.co_name
            lines.append('  File "%s", line %d, in %s\n'%(
                html.a(filename, href='/file' + filename + '#' + str(lineno)).to_unicode().encode('utf-8'),
                lineno, name))
            lines.append(dyncode.getline(filename, lineno))
        return lines


def ln(lineno):
    return html.a(name=str(lineno))

class FileSystemView(Renderer):
    def render_self(self, args):
        fname = '/' + '/'.join(args)
        lines = html.pre()
        i = 1
        for line in open(fname):
            lines.append(ln(i))
            lines.append(xml.escape(line)[:-1])
            i += 1
        return lines
    
views['file'] = FileSystemView()
                
