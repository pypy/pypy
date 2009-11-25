#!/usr/local/bin/python -O

""" A Python Benchmark Suite
"""
__copyright__="""\
   Copyright (c), 1997-2001, Marc-Andre Lemburg (mal@lemburg.com)

                   All Rights Reserved.

   Permission to use, copy, modify, and distribute this software and
   its documentation for any purpose and without fee or royalty is
   hereby granted, provided that the above copyright notice appear in
   all copies and that both that copyright notice and this permission
   notice appear in supporting documentation or portions thereof,
   including modifications, that you make.

   THE AUTHOR MARC-ANDRE LEMBURG DISCLAIMS ALL WARRANTIES WITH REGARD
   TO THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF
   MERCHANTABILITY AND FITNESS, IN NO EVENT SHALL THE AUTHOR BE LIABLE
   FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
   WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN
   AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING
   OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS
   SOFTWARE !

"""

__version__ = '1.0'

#
# NOTE: Use xrange for all test loops unless you want to face 
#       a 20MB process !
#
# All tests should have rounds set to values so that a run()
# takes between 20-50 seconds. This is to get fairly good
# clock() values. You can use option -w to speedup the tests
# by a fixed integer factor (the "warp factor").
#
import autopath
from py.xml import html
import sys,time,operator
from CommandLine import *

try:
    import cPickle
    pickle = cPickle
except ImportError:
    import pickle

### Test baseclass

class Test:

    """ All test must have this class as baseclass. It provides
        the necessary interface to the benchmark machinery.

        The tests must set .rounds to a value high enough to let the
        test run between 20-50 seconds. This is needed because
        clock()-timing only gives rather inaccurate values (on Linux,
        for example, it is accurate to a few hundreths of a
        second). If you don't want to wait that long, use a warp
        factor larger than 1.

        It is also important to set the .operations variable to a
        value representing the number of "virtual operations" done per
        call of .run().

        If you change a test in some way, don't forget to increase
        its version number.

    """
    operations = 1      # number of operations done per test()-call
    rounds = 100000     # number of rounds per run
    is_a_test = 1       # identifier
    last_timing = (0,0,0)       # last timing (real,run,calibration)
    warp = 1            # warp factor this test uses
    cruns = 20          # number of calibration runs
    overhead = None     # list of calibration timings

    version = 1.0       # version number of this test
    
    def __init__(self,warp=1):

        if warp > 1:
            self.rounds = self.rounds / warp
            self.warp = warp
        self.times = []
        self.overhead = []
        # We want these to be in the instance dict, so that pickle
        # saves them
        self.version = self.version
        self.operations = self.operations
        self.rounds = self.rounds

    def run(self):

        """ Run the test in two phases: first calibrate, then
            do the actual test. Be careful to keep the calibration
            timing low w/r to the test timing.
        """
        test = self.test
        calibrate = self.calibrate
        clock = time.clock
        cruns = self.cruns
        # first calibrate
        offset = 0.0
        for i in range(cruns):
            t = clock()
            calibrate()
            t = clock() - t
            offset = offset + t
        offset = offset / cruns
        # now the real thing
        t = clock() 
        test()
        t = clock() - t
        self.last_timing = (t-offset,t,offset)
        self.times.append(t-offset)

    def calibrate(self):

        """ Run the test, doing self.rounds loops, but without
            the actual test target in place. 
        """
        return

    def test(self):

        """ Run the test, doing self.rounds loop
        """
        # do some tests
        return
    
    def stat(self):

        """ Returns two value: average time per run and average per
            operation.
        """
        runs = len(self.times)
        if runs == 0:
            return 0,0
        totaltime = reduce(operator.add,self.times,0.0)
        avg = totaltime / float(runs)
        op_avg = totaltime / float(runs * self.rounds * self.operations)
        if self.overhead:
            totaloverhead = reduce(operator.add,self.overhead,0.0)
            ov_avg = totaloverhead / float(runs)
        else:
            # use self.last_timing - not too accurate
            ov_avg = self.last_timing[2]
        return avg,op_avg,ov_avg

### load Setup
import Setup

### Benchmark base class

class Benchmark:

    name = '?'                  # Name of the benchmark
    rounds = 1                  # Number of rounds to run
    warp = 1                    # Warp factor
    roundtime = 0               # Average round time
    version = None              # Benchmark version number (see __init__)

    def __init__(self):

        self.tests = {}
        self.version = 0.31

    def load_tests(self,setupmod,warp=1):

        self.warp = warp
        tests = self.tests
        print 'Searching for tests...'
        setupmod.__dict__.values()
        for c in setupmod.__dict__.values():
            if hasattr(c,'is_a_test') and c.__name__ != 'Test':
                tests[c.__name__] = c(warp)
        l = tests.keys()
        l.sort()
        for t in l:
            print '  ',t
        print

    def run(self):

        tests = self.tests.items()
        tests.sort()
        clock = time.clock
        print 'Running %i round(s) of the suite: ' % self.rounds
        print
        roundtime = clock()
        for i in range(self.rounds):
            print ' Round %-25i  real   abs    overhead' % (i+1)
            for j in range(len(tests)):
                name,t = tests[j]
                print '%30s:' % name,
                t.run()
                print '  %.3fr %.3fa %.3fo' % t.last_timing
            print '                                 ----------------------'
            print '            Average round time:      %.3f seconds' % \
                  ((clock() - roundtime)/(i+1))
            print
        self.roundtime = (clock() - roundtime) / self.rounds
        print
    
    def print_stat(self, compare_to=None, hidenoise=0):

        if not compare_to:
            print '%-30s      per run    per oper.   overhead' % 'Tests:'
            print '-'*72
            tests = self.tests.items()
            tests.sort()
            for name,t in tests:
                avg,op_avg,ov_avg = t.stat()
                print '%30s: %10.2f ms %7.2f us %7.2f ms' % \
                      (name,avg*1000.0,op_avg*1000000.0,ov_avg*1000.0)
            print '-'*72
            print '%30s: %10.2f ms' % \
                  ('Average round time',self.roundtime * 1000.0)

        else:
            print '%-30s      per run    per oper.    diff *)' % \
                  'Tests:'
            print '-'*72
            tests = self.tests.items()
            tests.sort()
            compatible = 1
            for name,t in tests:
                avg,op_avg,ov_avg = t.stat()
                try:
                    other = compare_to.tests[name]
                except KeyError:
                    other = None
                if other and other.version == t.version and \
                   other.operations == t.operations:
                    avg1,op_avg1,ov_avg1 = other.stat()
                    qop_avg = (op_avg/op_avg1-1.0)*100.0
                    if hidenoise and abs(qop_avg) < 10:
                        qop_avg = ''
                    else:
                        qop_avg = '%+7.2f%%' % qop_avg
                else:
                    qavg,qop_avg = 'n/a', 'n/a'
                    compatible = 0
                print '%30s: %10.2f ms %7.2f us  %8s' % \
                      (name,avg*1000.0,op_avg*1000000.0,qop_avg)
            print '-'*72
            if compatible and compare_to.roundtime > 0 and \
               compare_to.version == self.version:
                print '%30s: %10.2f ms             %+7.2f%%' % \
                      ('Average round time',self.roundtime * 1000.0,
                       ((self.roundtime*self.warp)/
                        (compare_to.roundtime*compare_to.warp)-1.0)*100.0)
            else:
                print '%30s: %10.2f ms                  n/a' % \
                      ('Average round time',self.roundtime * 1000.0)
            print
            print '*) measured against: %s (rounds=%i, warp=%i)' % \
                  (compare_to.name,compare_to.rounds,compare_to.warp)
        print

    def html_stat(self, compare_to=None, hidenoise=0):


        if not compare_to:
            table = html.table(
                        html.thead(
                            html.tr(
                                [ html.th(x, **{'mochi:format': y, 'align':'left'})
                            for (x,y) in [('Tests','str'), ('per run','float'),
                                  ('per oper.', 'float'), ('overhead', 'float')]])
                                    ),id = "sortable_table")
                               
            tests = self.tests.items()
            tests.sort()
            tbody = html.tbody()
            for name,t in tests:
                avg,op_avg,ov_avg = t.stat()
                tbody.append(html.tr( html.td(name),
                                      html.td(avg*1000.0),
                                      html.td(op_avg*1000000.0),
                                      html.td(ov_avg*1000.0)
                                    ))
            table.append(tbody)
            table.append(html.tr(
                                    'Average round time %s' % (self.roundtime * 1000.0))
                                            )
            return table
        elif isinstance(compare_to, Benchmark):
            table = html.table(html.thead(
                      html.tr([ html.th(x, **{'mochi:format': y, 'align':'left'})
                          for (x,y) in [('Tests','str'), ('per run','float'),
                             ('per oper.', 'float'), ('diff', 'float')]])),
                             id = "sortable_table", class_="datagrid")
            tests = self.tests.items()
            tests.sort()
            compatible = 1
            tbody = html.tbody()
            for name,t in tests:
                avg,op_avg,ov_avg = t.stat()
                try:
                    other = compare_to.tests[name]
                except KeyError:
                    other = None
                if other and other.version == t.version and \
                   other.operations == t.operations:
                    avg1,op_avg1,ov_avg1 = other.stat()
                    qop_avg = (op_avg/op_avg1-1.0)*100.0
                    if hidenoise and abs(qop_avg) < 10:
                        qop_avg = ''
                    else:
                        qop_avg = '%+7.2f%%' % qop_avg
                else:
                    qavg,qop_avg = 'n/a', 'n/a'
                    compatible = 0
                tbody.append(html.tr( html.td(name),
                                      html.td(avg*1000.0),
                                      html.td(op_avg*1000000.0),
                                      html.td(qop_avg)
                                    ))
            if compatible and compare_to.roundtime > 0 and \
               compare_to.version == self.version:
                tbody.append(html.tr(
                                 html.td('Average round time'),
                                 html.td(self.roundtime * 1000.0),
                                 html.td(''),
                                 html.td('%+7.2f%%'% (((self.roundtime*self.warp)/ 
                                        (compare_to.roundtime*compare_to.warp)-1.0)*100.0)
                                        )))
                                    
            else:
                tbody.append(html.tr(
                                    html.td('Average round time'),
                                    html.td(self.roundtime * 1000.0)))
            table.append(tbody)
            return table
        else:
            table = html.table(html.thead(
                      html.tr([ html.th(x, **{'mochi:format': y, 'align':'left'})
                          for (x,y) in [('Tests','str')]+[('pypy ver','float') for z in compare_to]
                             ])),
                             id = "sortable_table")
            tests = self.tests.items()
            tests.sort()
            compatible = 1
            for name,t in tests:
                avg,op_avg,ov_avg = t.stat()
                percent = []
                for comp_to in compare_to:
                    try:
                        other = comp_to.tests[name]
                    except KeyError:
                        other = None
                    if other and other.version == t.version and \
                            other.operations == t.operations:
                        avg1,op_avg1,ov_avg1 = other.stat()
                        qop_avg = (op_avg/op_avg1-1.0)*100.0
                        if hidenoise and abs(qop_avg) < 10:
                            qop_avg = ''
                        else:
                            qop_avg = '%+7.2f%%' % qop_avg
                    else:
                        qavg,qop_avg = 'n/a', 'n/a'
                        compatible = 0
                    percent.append(qop_avg)
                table.append(html.tr( html.td(name),
                                      [html.td(qop_avg) for qop_avg in percent]
                                    ))
            if compatible and compare_to.roundtime > 0 and \
               compare_to.version == self.version:
                table.append(html.tr(
                                 html.td('Average round time'),
                                 html.td(self.roundtime * 1000.0),
                                 html.td(''),
                                 html.td('%+7.2f%%'% (((self.roundtime*self.warp)/ 
                                        (compare_to.roundtime*compare_to.warp)-1.0)*100.0)
                                        )))
                                    
            else:
                table.append(html.tr(
                                    html.td('Average round time'),
                                    html.td(self.roundtime * 1000.0)))
            return table

def print_machine():

    import platform
    print 'Machine Details:'
    print '   Platform ID:  %s' % platform.platform()
    # There's a bug in Python 2.2b1+...
    if 1 or sys.version[:6] != '2.2b1+':
        print '   Python:       %s' % platform.python_version()
        print '   Compiler:     %s' % platform.python_compiler()
        buildno, buildate = platform.python_build()
        print '   Build:        %s (#%i)' % (buildate, buildno)

class Document(object): 
    
    def __init__(self, title=None): 

        self.body = html.body()
        self.head = html.head()
        self.doc = html.html(self.head, self.body)
        if title is not None: 
            self.head.append(
                html.meta(name="title", content=title))
        self.head.append(
            html.link(rel="Stylesheet", type="text/css", href="MochiKit-1.1/examples/sortable_tables/sortable_tables.css"))
        self.head.append(
                    html.script(rel="JavaScript", type="text/javascript", src="MochiKit-1.1/lib/MochiKit/MochiKit.js"))
        self.head.append(
            html.script(rel="JavaScript", type="text/javascript", src="MochiKit-1.1/examples/sortable_tables/sortable_tables.js"))

    def writetopath(self, p): 
        assert p.ext == '.html'
        self.head.append(
            html.meta(name="Content-Type", content="text/html;charset=UTF-8")
        )
        s = self.doc.unicode().encode('utf-8')
        p.write(s) 

class PyBenchCmdline(Application):

    header = ("PYBENCH - a benchmark test suite for Python "
              "interpreters/compilers.")

    version = __version__

    options = [ArgumentOption('-n','number of rounds',Setup.Number_of_rounds),
               ArgumentOption('-f','save benchmark to file arg',''),
               ArgumentOption('-c','compare benchmark with the one in file arg',''),
               ArgumentOption('-l','compare benchmark with the ones in the files arg',''),
               ArgumentOption('-s','show benchmark in file arg, then exit',''),
               ArgumentOption('-w','set warp factor to arg',Setup.Warp_factor),
               SwitchOption('-d','hide noise in compares', 0),
               SwitchOption('--no-gc','disable garbage collection', 0),
               SwitchOption('-x','write html table', 0),
               ]

    about = """\
The normal operation is to run the suite and display the
results. Use -f to save them for later reuse or comparisms.

Examples:

python1.5 pybench.py -w 100 -f p15
python1.4 pybench.py -w 100 -f p14
python pybench.py -s p15 -c p14
"""
    copyright = __copyright__

    def main(self):

        rounds = self.values['-n']
        reportfile = self.values['-f']
        show_bench = self.values['-s']
        compare_to = self.values['-c']
        compare_to_many = self.values['-l']
        hidenoise = self.values['-d']
        warp = self.values['-w']
        nogc = self.values['--no-gc']
        html = self.values['-x']

        # Switch off GC
        if nogc:
            try:
                import gc
            except ImportError:
                nogc = 0
            else:
                if self.values['--no-gc']:
                    gc.disable()

        print 'PYBENCH',__version__
        print

        if not compare_to:
            #print_machine()
            print

        if compare_to:
            try:
                f = open(compare_to,'rb')
                bench = pickle.load(f)
                bench.name = compare_to
                f.close()
                compare_to = bench
            except IOError:
                print '* Error opening/reading file',compare_to
                compare_to = None    

        if show_bench:
            try:
                f = open(show_bench,'rb')
                bench = pickle.load(f)
                bench.name = show_bench
                f.close()
                print 'Benchmark: %s (rounds=%i, warp=%i)' % \
                      (bench.name,bench.rounds,bench.warp)
                print
                print "*******************************************"
                if html:
                    print "Generating HTML"
                    import py.path
                    index = py.path.local('index.html')
                    table = bench.html_stat(compare_to, hidenoise)
                    doc = Document()
                    doc.body.append(table)
                    doc.writetopath(index)
                else:
                    bench.print_stat(compare_to, hidenoise)
            except IOError:
                print '* Error opening/reading file',show_bench
                print
            return

        if reportfile:
            if nogc:
                print 'Benchmark: %s (rounds=%i, warp=%i, no GC)' % \
                      (reportfile,rounds,warp)
            else:
                print 'Benchmark: %s (rounds=%i, warp=%i)' % \
                      (reportfile,rounds,warp)
            print

        # Create benchmark object
        bench = Benchmark()
        bench.rounds = rounds
        bench.load_tests(Setup,warp)
        try:
            bench.run()
        except KeyboardInterrupt:
            print
            print '*** KeyboardInterrupt -- Aborting'
            print
            return
        bench.print_stat(compare_to)
        if html:
            print "Generating HTML"
            import py.path
            index = py.path.local('index.html')
            table = bench.html_stat(compare_to, hidenoise)
            doc = Document()
            doc.body.append(table)
            doc.writetopath(index)
        # ring bell
        sys.stderr.write('\007')

        if reportfile:
            try:
                f = open(reportfile,'wb')
                bench.name = reportfile
                pickle.dump(bench,f)
                f.close()
            except IOError:
                print '* Error opening/writing reportfile'

if __name__ == '__main__':
    PyBenchCmdline()
