from pypy.tool.tb_server.server import TBRequestHandler
from xpy import html, xml

from std.magic import dyncode

import traceback
import cgi

views = TBRequestHandler.views

class URL(object):
    attrs='scm','netloc','path','params','query','fragment'
    attrindex = dict(zip(attrs, range(len(attrs))))
    # XXX authentication part is not parsed

    def __init__(self, string='', **kw):
        from urlparse import urlparse
        for name,value in zip(self.attrs, urlparse(string, 'http')):
            setattr(self, name, value)
        self.__dict__.update(kw)


class Renderer:
    def render(self, path):
        url = URL(path)
        args = url.path.split('/')[2:]
        query = cgi.parse_qs(url.query)
        try:
            inner = self.render_self(args, query)
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
        
    def render_self(self, args, query):
        lines = html.pre()
        for tb in dyncode.listtb(self.exc[2]):
            filename = tb.tb_frame.f_code.co_filename 
            lineno = tb.tb_lineno
            name = tb.tb_frame.f_code.co_name
            link = '/file' + filename + '?line=' + str(lineno) + '#' + str(lineno)
            lines.append('  File "%s", line %d, in %s\n'%(
                html.a(filename, href=link).to_unicode().encode('utf-8'),
                lineno, name))
            lines.append('        '+dyncode.getline(filename, lineno).lstrip())
        lines.append(xml.escape(
            ''.join(traceback.format_exception_only(self.exc[0], self.exc[1]))))
        return lines


def ln(lineno):
    return html.a(name=str(lineno))

class FileSystemView(Renderer):
    def render_self(self, args, query):        
        fname = '/' + '/'.join(args)
        lines = html.table()
        i = 1
        print query
        hilite = int(query.get('line', [-1])[0])
        for line in open(fname):
            if i == hilite:
                kws = {'style': 'font-weight: bold;'}
            else:
                kws = {}
            row = html.tr(
                html.td(html.a("%03d" % i, name=str(i))),
                html.td(
                    html.pre(xml.escape(line)[:-1],
                             **kws),
                ), 
            )
            lines.append(row) 
            i += 1
        return lines
    
views['file'] = FileSystemView()
                
