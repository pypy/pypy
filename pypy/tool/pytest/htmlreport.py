#! /usr/bin/env python

"""
the html test reporter 

"""
import sys, os, re
import pprint
import py 
from pypy.tool.pytest import result
from pypy.tool.pytest.overview import ResultCache 

# 
# various interesting path objects 
#

html = py.xml.html
NBSP = py.xml.raw("&nbsp;")

class HtmlReport(object): 
    def __init__(self, resultdir): 
        self.resultcache = ResultCache(resultdir)

    def parselatest(self): 
        self.resultcache.parselatest()

    # 
    # rendering 
    # 

    def render_latest_table(self, results): 
        table = html.table(
                    [html.th(x, align='left') 
                        for x in ("failure", "filename", "revision", 
                                  "user", "platform", "elapsed", 
                                  "options", "last error line"
                                  )], 
                )
        r = results[:]
        def f(x, y): 
            xnum = x.isok() and 1 or (x.istimeout() and 2 or 3)
            ynum = y.isok() and 1 or (y.istimeout() and 2 or 3)
            res = -cmp(xnum, ynum)
            if res == 0: 
                return cmp(x['execution-time'], y['execution-time'])
            return res 
        r.sort(f) 
        for result in r: 
            table.append(self.render_result_row(result))
        return table 

    def render_result_row(self, result): 
        dp = py.path.local(result['fspath']) 

        options = " ".join([x for x in result.get('options', []) if x!= 'core'])
        if not options: 
            options = NBSP

        failureratio = 100 * (1.0 - result.ratio_of_passed())
        self.data[result.testname] = failureratio
        return html.tr(
                html.td("%.2f%%" % failureratio, 
                    style = "background-color: %s" % (getresultcolor(result),)), 
                html.td(self.render_test_references(result)),
                html.td(result['pypy-revision']),
                html.td(result['userhost'][:15]), 
                html.td(result['platform']), 
                html.td("%.2fs" % result['execution-time']),
                html.td(options), 
                html.td(result.repr_short_error() or NBSP)
        )

    def getrelpath(self, p): 
        return p.relto(self.indexpath.dirpath())

    def render_test_references(self, result): 
        dest = self.make_single_test_result(result)
        modified = result.ismodifiedtest() and " [mod]" or ""
        return html.div(html.a(result.path.purebasename + modified, 
                      href=self.getrelpath(dest)),
                      style="background-color: transparent")

    def make_single_test_result(self, result): 
        cache = self.indexpath.dirpath('.cache', result['userhost'][:15])
        cache.ensure(dir=1)
        dest = cache.join(result.path.basename).new(ext='.html')
        doc = ViewResult(result)
        doc.writetopath(dest)
        return dest

    def getcorelists(self): 
        def iscore(result): 
            return 'core' in result.get('options', []) 
        coretests = []
        noncoretests = []
        for name in self.resultcache.getnames(): 
            result = self.resultcache.getlatestrelevant(name)
            if iscore(result): 
                coretests.append(result)
            else: 
                noncoretests.append(result) 
        return coretests, noncoretests 
    
    # generate html files 
    #
    def makeindex(self, indexpath, detail="PyPy - latest"): 
        self.indexpath = indexpath
        self.data = {}
        doc = Document(title='pypy test results')
        body = doc.body
        coretests, noncoretests = self.getcorelists()
        body.append(html.h2("%s compliance test results - "
                            "core tests" % detail))

        body.append(self.render_test_summary('core', coretests))
        body.append(self.render_latest_table(coretests))
        body.append(
            html.h2("%s compliance test results - non-core tests" % detail))
        body.append(self.render_test_summary('noncore', noncoretests))
        body.append(self.render_latest_table(noncoretests))
        doc.writetopath(indexpath)
        datapath = indexpath.dirpath().join('data')
        d = datapath.open('w')
        print >>d, "data = ",
        pprint.pprint(self.data, stream=d)
        d.close()
        self.data = None
        
    def render_test_summary(self, tag, tests):
        ok = len([x for x in tests if x.isok()])
        err = len([x for x in tests if x.iserror()])
        to = len([x for x in tests if x.istimeout()])
        numtests = ok + err + to
        assert numtests == len(tests)
        assert numtests

        t = html.table()
        sum100 = numtests / 100.0
        def row(*args):
            return html.tr(*[html.td(arg) for arg in args])

        sum_passed = sum([x.ratio_of_passed() for x in tests])
        compliancy = sum_passed/sum100
        self.data['%s-compliancy' % tag] = compliancy 
        t.append(row(html.b("tests compliancy"), 
                     html.b("%.2f%%" % (compliancy,))))

        passed = ok/sum100
        self.data['%s-passed' % tag] = passed
        t.append(row("testmodules passed completely", "%.2f%%" % passed))
        failed = err/sum100
        self.data['%s-failed' % tag] = failed
        t.append(row("testmodules (partially) failed", "%.2f%%" % failed))
        timedout = to/sum100
        self.data['%s-timedout' % tag] = timedout
        t.append(row("testmodules timeout", "%.2f%%" % timedout))
        return t

class Document(object): 
    def __init__(self, title=None): 
        self.body = html.body()
        self.head = html.head()
        self.doc = html.html(self.head, self.body)
        if title is not None: 
            self.head.append(
                html.meta(name="title", content=title))
        self.head.append(
            html.link(rel="Stylesheet", type="text/css", href="/pypy/default.css"))

    def writetopath(self, p): 
        assert p.ext == '.html'
        self.head.append(
            html.meta(name="Content-Type", content="text/html;charset=UTF-8")
        )
        s = self.doc.unicode().encode('utf-8')
        p.write(s) 
       
def getresultcolor(result): 
    if result.isok(): 
        color = "#00ee00"
    elif result.iserror(): 
        color = "#ee0000" 
    elif result.istimeout: 
        color = "#0000ee"
    else: 
        color = "#444444"
    return color 

class ViewResult(Document): 
    def __init__(self, result): 
        title = "%s testresult" % (result.path.purebasename,)
        super(ViewResult, self).__init__(title=title)
        color = getresultcolor(result)
        self.body.append(html.h2(title, 
                    style="background-color: %s" % color))
        self.body.append(self.render_meta_info(result))

        for name in ('reportdiff', 'stdout', 'stderr'): 
            try: 
                text = result.getnamedtext(name)
            except KeyError: 
                continue
            self.body.append(html.h3(name))
            self.body.append(html.pre(text))

    def render_meta_info(self, result):
        t = html.table()
        items = result.items()
        items.sort()
        for name, value in items: 
            if name.lower() == name:
                t.append(html.tr(
                    html.td(name), html.td(value)))
        return t 
 
class TestOfHtmlReportClass: 
    def setup_class(cls): 
        py.test.skip('needs move to own test file')
        cls.testresultdir = confpath.testresultdir 
        cls.rep = rep = HtmlReport()
        rep.parse_all(cls.testresultdir)

    def test_pickling(self): 
        # test pickling of report 
        tempdir = py.test.ensuretemp('reportpickle')
        picklepath = tempdir.join('report.pickle')
        picklepath.dump(self.rep)
        x = picklepath.load()
        assert len(x.results) == len(self.rep.results)
    
    def test_render_latest(self): 
        t = self.rep.render_latest_table(self.rep.results)
        assert unicode(t)

mydir = py.magic.autopath().dirpath()

def getpicklepath(): 
    return mydir.join('.htmlreport.pickle')
