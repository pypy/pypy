from __future__ import generators
import sys
import os
import inspect
import traceback 
from time import time as now

from py import test, magic
from py.test import collect, run 
from py.magic import dyncode 

# lazy relative Implementation imports 
from summary import Summary 
from out import getout 

class TextReporter(object):
    Summary = Summary 
    typemap = {
        run.Passed: '.', run.Skipped: 's', run.Failed: 'F',
        collect.Error: 'C', 
    }
    namemap = {
        run.Passed: 'ok', run.Skipped: 'SKIP', run.Failed: 'FAIL',
        collect.Error: 'COLLECT ERROR', 
    }

    def __init__(self, f=None): 
        if f is None:
            f = sys.stdout 
        self.out = getout(f) 
        self._started = {}
        self.summary = self.Summary() 
        self.summary.option = self.option = test.config.option 

    def start(self, conf=None):
        self.summary.starttime = now() 
        if conf is not None and conf.mypath is not None:
            self.out.line("using %s" % conf.mypath) 
        self.out.sep("_")
        self.out.sep("_", " TESTS STARTING ") 
        self.out.sep("_")
        if not self.option.nomagic:
            magic.invoke(assertion=1) 

    def end(self):
        if not self.option.nomagic:
            magic.revoke(assertion=1) 
        self.summary.endtime = now() 
        self.summary.render(self.out) 

    def open(self, collector):
        if self.option.collectonly:
            cols = self.__dict__.setdefault('_opencollectors', [])
            if len(cols):
                print '    ' * len(cols),
            print repr(collector)
            cols.append(collector)
            return cols.pop

        cls = getattr(collector, '__class__', None)
        if cls is None:
            return
        for typ in inspect.getmro(cls):
            meth = getattr(self, 'open_%s' % typ.__name__, None)
            if meth:
                return meth(collector)

    def open_Module(self, collector):
        verbose = self.option.verbose
        if verbose < 1:
            return
        numunits = len(list(collector.iterunits()))
        if numunits > 0:
            #if verbose < 2:
            #    self.out.write('%s[%d]' % (collector.pypath, 
            #                           numunits))
            #else:
            #self.out.line("collector.fspy.modpath) 
            return self.out.line 

    def open_Directory(self, collector):
        if self.option.verbose < 1:
            return
        l = []
        for x in collector:
            l.append(x)
            break
        if l:
            self.out.line('%-13s %s' %('+ directory start ', collector.fspath))
            if self.option.verbose >=1:
                def close_directory():
                    self.out.line('%-13s %s' %('- directory finish', collector.fspath))
                    self.out.line()
                return close_directory

    def startitem(self, item):
        if not self.option.nocapture:
            from py.__impl__.test.tool.outerrcapture import SimpleOutErrCapture 
            item.iocapture = SimpleOutErrCapture()
        if self.out.tty:
            realpath, lineno = item.pypath.getfilelineno()
            location = "running %s:%d %s" % (realpath.basename, lineno, str(item.pypath.modpath))
            self.out.rewrite(location) 
        self._started[item] = now() 

    def enditem(self, result):
        endtime = now()
        item = result.item 
        starttime = self._started[item] 
        del self._started[item]
        elapsed = endtime - starttime
        item.elapsed = elapsed 

        if not self.option.nocapture:
            result.out, result.err = item.iocapture.reset()
       
        restype, c = self.processresult(result)
        writeinfo = None 
        if self.out.tty:
            if not isinstance(result, run.Passed) or self.option.verbose >=1:
                writeinfo = '\n' 
            elif isinstance(result, run.Passed): 
                writeinfo = '' 
        elif self.option.verbose >= 1:
            writeinfo = '\n' 
        else:
            self.out.write(c) 
            
        if writeinfo is not None:
            realpath, lineno = item.pypath.getfilelineno()
            location = "%s:%d" % (realpath.basename, lineno)
            resultstring = self.namemap.get(restype, result.__class__.__name__)
            self.out.rewrite("%.3f %-2s %-20s %s%s" % (
                elapsed, resultstring, location, str(item.pypath.modpath), writeinfo
                ))
        if self.option.usepdb:
            if (issubclass(restype, collect.Error) or
                issubclass(restype, run.Failed)):
                import pdb
                self.out.rewrite(
                    '\n%s: %s\n'
                    % (result.excinfo[1].__class__.__name__,
                       result.excinfo[1]))
                pdb.post_mortem(result.excinfo[2])
        if self.option.exitfirstproblem:
            if (issubclass(restype, collect.Error) or 
                issubclass(restype, run.Failed)):
                raise run.Exit("first problem, exit configured.")

    def report_collect_error(self, error):
        restype, c = self.processresult(error) 
        writeinfo = None 
        if self.out.tty:
            if not isinstance(result, run.Passed) or self.option.verbose >=1:    
                writeinfo = '\n' 
            elif isinstance(result, run.Passed): 
                writeinfo = '' 
        elif self.option.verbose >= 1:
            writeinfo = '\n' 
        else:
            self.out.write(c) 
            
        if writeinfo is not None:
            exc, frame, filename,lineno = self.summary.getexinfo(error)
            self.out.line('CollectError: %s:%d' % (filename, lineno) )

    def processresult(self, testresult):
        for restype, c in self.typemap.items():
            if isinstance(testresult, restype):
                self.summary.append(restype, testresult)
                return restype, c
        else:
            raise TypeError, "not a result instance: %r" % testresult

    #def raiseloc(self, excinfo):
    #    """ return (origin, offendingline) for the given traceback. """
    #    tb = excinfo[2]
    #    origin = misc.getfileloc(tb)
    #    offendingline = misc.getline(tb)
    #    return (origin, offendingline)

