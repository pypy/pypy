import py
from rpython.translator.cli.test.runtest import compile_function
from rpython.translator.oosupport.test_template.backendopt import BaseTestOptimizedSwitch

class TestOptimizedSwitch(BaseTestOptimizedSwitch):
    def getcompiled(self, fn, annotation):
        return compile_function(fn, annotation, backendopt=True)
