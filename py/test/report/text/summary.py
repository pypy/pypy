from __future__ import generators
import sys
import os
import traceback 

from py.test import collect, run 
from py.magic import dyncode 
from py.__impl__.magic import exprinfo, assertion

class Summary(object):
    def __init__(self): 
        pass 

    def append(self, restype, testresult):
        self.getlist(restype).append(testresult)

    def getlist(self, restype):
        name = restype.__name__.lower()
        return self.__dict__.setdefault(name, [])

    def repr_collect_error(self, error): 
        exc, frame, filename,lineno = self.getexinfo(error)
        self.out.line()
        self.out.sep("_") 
        self.out.sep("_", "Collect Error")
        self.out.line()
        self.repr_traceback_raw(filename, error.excinfo[2])
        #self.repr_failure_result(res)
        #self.out.line()
        #if isinstance(res.excinfo[1], AssertionError):
        #     from std.utest.tool import hackexpr
        #     res.msg = "failed: " + hackexpr.getmsg(res.excinfo)
        for line in traceback.format_exception_only(*error.excinfo[:2]):
            self.out.line(line.rstrip())

        #if self.option.showlocals:
        #    self.out.sep('- ', 'locals')
        #    for name, value in frame.f_locals.items():
        #        self.out.line("%-10s = %r" %(name, value))
    def summary_collect_errors(self):
        for error in self.getlist(collect.Error): 
            self.repr_collect_error(error) 

    def render(self, out):
        self.out = out 
        self.out.write('\n')
        self.skippedreasons()
        self.failures()
        self.summary_collect_errors() 
        outlist = []
        sum = 0
        for typ in run.Passed, run.Failed, run.Skipped:
            l = self.getlist(typ)
            outlist.append('%d %s' % (len(l), typ.__name__.lower()))
            sum += len(l)
        self.out.sep('=', '%d TESTS FINISHED' % sum)
        self.out.write('%4.2f seconds' % (self.endtime-self.starttime))
        self.out.line(" (%s)" % ", ".join(outlist))

    def getexinfo(self, res):
        _,exc,tb = res.excinfo
        tbindex = getattr(res, 'tbindex', -1)
        filename, lineno = dyncode.tbinfo(tb, tbindex)
        frame = dyncode.listtb(tb)[tbindex].tb_frame 
        return exc, frame, filename, lineno

    def skippedreasons(self):
        d = {}
        for res in self.getlist(run.Skipped):
            raisingtb = dyncode.listtb(res.excinfo[2])[-1]
            fn = raisingtb.tb_frame.f_code.co_filename 
            lineno = raisingtb.tb_lineno
            d[(fn,lineno)] = res
        if d:
            self.out.line()
            self.out.sep('_', 'reasons for skipped tests')
            for (fn,lineno), res in d.items():
                self.out.line('Skipped in %s:%d %s' %(fn,lineno,getattr(res, 'msg')))
            self.out.line()
            
    def failures(self):
        for res in self.getlist(run.Failed):
            self.repr_failure(res)

    def repr_failure(self, res):
        exc, frame, filename,lineno = self.getexinfo(res)
        self.out.line()
        self.out.sep("_") 
        self.out.line()
        #self.out.sep("_", "Test Failure") #  %s" % res.unit.pypath)
        #self.out.sep("_") 
        #self.out.line()
        self.repr_traceback(res.item, res.excinfo[2], 
                            getattr(res, 'tbindex', -1))
        #self.out.line()
        self.repr_failure_result(res)
        try:
            out, err = res.out, res.err
        except AttributeError:
            pass
        else:
            if out.strip():
                self.out.sep("- ", "recorded stdout")
                self.out.line(out.strip())
            if err.strip():
                self.out.sep("- ", "recorded stderr")
                self.out.line(err.strip())
        #self.out.line()

    def repr_failure_result(self, res):
        cls = res.excinfo[0]
        if issubclass(cls, run.ExceptionFailure):
            if not res.innerexcinfo:
                self.out.line("%s <<<  DID NOT RAISE" % (res.expr,))
                self.out.line("expected: %r" % (res.expected,))
            else:
                self.out.write("%r raised wrong Exception, " % (res.expr,))
                self.out.line("expected: %r" % (res.expected.__name__,))
                #self.out.line("got     : %r" % res.innerexcinfo[0])
                #self.out.line()
                self.out.sep("- ", "traceback of unexpected exception")
                #self.out.line("reality:") 
                self.repr_traceback(res.item, res.innerexcinfo[2])
                for line in traceback.format_exception_only(*res.innerexcinfo[:2]):
                    self.out.line(line)
        elif issubclass(cls, assertion.AssertionError): 
            res.msg = str(res.excinfo[1])
            self.out.line(res)
            return
        else:
            if not self.option.nomagic:
	    	showex = False
                try:
                    res.msg = exprinfo.getmsg(res.excinfo)
                except KeyboardInterrupt:
                    raise
                except:
                    if self.option.verbose > 1:
                        self.out.line("reinterpretation traceback")
                        traceback.print_exc()
                    else:
                        self.out.line("(reinterpretation failed, you may increase "
                                        "verbosity to see details)")
                        showex = True
                else:
                    self.out.line(res) 
            else:
                showex = True 
            if showex:
                for line in traceback.format_exception_only(*res.excinfo[:2]):
                    self.out.line(line)

    def repr_source(self, frame, lineno):
        # represent the source code
        self.out.line()
        try:
            lines, firstlineno = dyncode.findsource(frame) # .f_code)
        except IOError:
            self.out.line("failure to retrieve sourcelines from %r" % frame) 
            #self.out.line("(co_filename = %r)" % (frame.f_code.co_filename))
            #self.out.line("(f_lineno = %r)" % (frame.f_lineno)) 
            return

        for line in lines[firstlineno:lineno-1]:
            self.out.line(line.rstrip())
        line = lines[lineno-1]
        if line.startswith(" "):
            line = line[1:]  # to avoid the indentation caused by ">"
        self.out.line(">" + line)
        return

    #def tracelines(self, filename, lineno):
    #    prelines = 3
    #    if prelines:
    #        for i in range(lineno-prelines-1, lineno):
    #            line = dyncode.getline(filename, i)
    #            self.out.line("  %s" % line.rstrip())
    #    line = dyncode.getline(filename, lineno)
    #    self.out.line("> %s" % line.rstrip())

    def forward_traceback_to_test(self, tb, filename):
        old = tb
        while tb:
            codefn = tb.tb_frame.f_code.co_filename
            if filename == codefn or filename.endswith(codefn) or codefn.endswith(filename): 
                return tb 
            tb = tb.tb_next
        return old

    def repr_traceback(self, item, tb, tbindex=-1):
        t_file, t_lineno = item.pypath.getfilelineno() 
        self.out.line("%s, line %d" % (item.pypath, t_lineno) )
        fspath = item.pypath.fspath 
        self.out.sep('_')
        self.repr_traceback_raw(fspath, tb, tbindex)
        #t_file, t_lineno = unit.pypath.getfilelineno() 
        #if t_file != filename or lineno != t_lineno:
        #self.out.line("%s, line %d" % (unit.pypath, t_lineno) )
        self.out.sep('-')

    def repr_traceback_raw(self, fspath, tb, tbindex=-1):
        if fspath and not self.option.fulltrace:
            tb = self.forward_traceback_to_test(tb, str(fspath))
        else:
            tbindex = -1
        tbentries = dyncode.listtb(tb) 
        if tbindex < -1 and not self.option.fulltrace:
            tbentries = tbentries[:tbindex+1]

        recursioncache = {}
        first = True 
        for tb in tbentries:
            if first:
                first = False 
            else:
                self.out.sep('-')
            filename = tb.tb_frame.f_code.co_filename 
            lineno = tb.tb_lineno
            name = tb.tb_frame.f_code.co_name
            showfn = filename 
            #showfn = filename.split(os.sep)
            #if len(showfn) > 5:
            #    showfn = os.sep.join(['...'] + showfn[-5:])
            self.repr_source(tb.tb_frame, lineno)
            self.out.line("> %s, line %d" %(showfn, lineno)) # , name))
            if self.option.showlocals:
                self.out.sep('- ', 'locals')
                for name, value in tb.tb_frame.f_locals.items():
                    self.out.line("%-10s = %r" %(name, value))
            key = (filename, lineno)
            if key not in recursioncache:
                recursioncache.setdefault(key, []).append(tb.tb_frame.f_locals)
            else:
                loc = tb.tb_frame.f_locals 
                for x in recursioncache[key]:
                    if x==loc:
                        self.out.line("Recursion detected (same locals & position)")
                        break
                else:
                    #self.out.sep('-')
                    continue
                break

