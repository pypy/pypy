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
    def __init__(self, exc):
        self.name = 'traceback%d' % len(views) 
        views[self.name] = self
        self.exc = exc
        
    def render_self(self, args):
        lines = html.pre()
        for tb in dyncode.listtb(self.exc[2]):
            filename = tb.tb_frame.f_code.co_filename 
            lineno = tb.tb_lineno
            name = tb.tb_frame.f_code.co_name
            lines.append('  File "%s", line %d, in %s\n'%(
                html.a(filename, href='/file' + filename + '#' + str(lineno)).to_unicode().encode('utf-8'),
                lineno, name))
            lines.append('        '+dyncode.getline(filename, lineno).lstrip())
        lines.append(xml.escape(
            ''.join(traceback.format_exception_only(self.exc[0], self.exc[1]))))
        return lines


def ln(lineno):
    return html.a(name=str(lineno))

class FileSystemView(Renderer):
    def render_self(self, args):
        fname = '/' + '/'.join(args)
        lines = html.table()
        i = 1
        for line in open(fname):
            row = html.tr(
                html.td(html.a("%03d" % i, name=str(i)), 
                        style='text-align: left;'),
                html.td(
                    html.pre(xml.escape(line)[:-1]),
                        #style="white-space: pre; font-family: monospace;"
                ), 
            )
            lines.append(row) 
            i += 1
        return lines
    
views['file'] = FileSystemView()
                
