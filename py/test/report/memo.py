from __future__ import generators
import sys
import os
from py import test 

run = test.run 

class MemoReporter:
    typemap = {
        run.Passed: '.', run.Skipped: 's', run.Failed: 'F',
    }

    def append(self, restype, testresult):
        self.getlist(restype).append(testresult)

    def getlist(self, restype):
        name = restype.__name__.lower()
        return self.__dict__.setdefault(name, [])

    def processresult(self, testresult):
        for restype, c in self.typemap.items():
            if isinstance(testresult, restype):
                self.append(restype, testresult)
                return restype, c
        else:
            raise TypeError, "not a result instance: %r" % testresult

    ##########################
    # API for the runner
    ##########################

    def open(self, collector):
        pass

    def report_outcome(self, testresult):
        restype, c = self.processresult(testresult)
            
    def summary(self):
        pass

