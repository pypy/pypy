from __future__ import generators

import sys, inspect
from py import test

class Driver:
    option = test.config.option

    def __init__(self, reporter):
        self.reporter = reporter 
        self._setupstack = []
        self._instance = None 

    def run(self, obj):
        """ run (possibly many) testitems and/or collectors. """
        collect = test.collect 
        if isinstance(obj, Item):
            if not self.option.collectonly:
                #if self.option.args:
                #    if str(obj.path).find(self.option.args[0]) == -1:
                #        return
                self.runitem(obj)
        elif isinstance(obj, collect.Collector):
            self.runcollector(obj)
        elif isinstance(obj, collect.Error):
            try:
                self.reporter.report_collect_error(obj)
            except (KeyboardInterrupt, SystemExit):
                raise 
            except: 
                print "*" * 80
                print "Reporter Error"
                print "*" * 80
                import traceback
                traceback.print_exc()
                raise SystemExit, 1
            if self.option.exitfirstproblem:
                raise SystemExit, 2
        else:
            raise TypeError("%r is not a Item or Collector instance" % obj)

    def runcollector(self, collector):
        close = self.reporter.open(collector)
        try:
            for obj in collector:
                self.run(obj)
        finally:
            if close:
                close()

    def runitem(self, item):
        self.reporter.startitem(item)
        try:
            res = item.execute(self) or Passed()
        except Outcome, res:
            res.excinfo = sys.exc_info()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            res = Failed(excinfo=sys.exc_info())
        res.item = item
        self.reporter.enditem(res)

    def setup_path(self, pypath):
        """ setup objects along the path to the test-method 
            (pointed to by pypath). Tear down any previously 
            setup objects which are not directly needed. 
        """ 
        # setupstack contains (pypath, obj)'s of already setup objects 
        # strict ordering is maintained, i.e. each pypath in
        # the stack is "relto" the previous pypath. 
        stack = self._setupstack 
        while stack and not pypath.relto(stack[-1][0]): 
            self._teardownone(stack.pop()[1])
        rest = pypath.parts()[len(stack):-1]
        for x in rest: 
            stack.append((x, self._setupone(x)))

    def setup(self):
        """ setup any neccessary resources. """ 

    def teardown(self):
        """ teardown any resources the runner knows about. """ 
        while self._setupstack: 
            self._teardownone(self._setupstack.pop()[1]) 
                
    def _setupone(self, pypath):
        obj = pypath.resolve() 
        if inspect.ismodule(obj): 
            if hasattr(obj, 'setup_module'):
                obj.setup_module(obj) 
        elif inspect.isclass(obj):
            if hasattr(obj, 'setup_class'):
                obj.setup_class.im_func(obj) 
        return obj 

    def _teardownone(self, obj):
        if inspect.ismodule(obj): 
            if hasattr(obj, 'teardown_module'):
                obj.teardown_module(obj) 
        elif inspect.isclass(obj):
            if hasattr(obj, 'teardown_class'):
                obj.teardown_class.im_func(obj) 

    def setup_method(self, pypath): 
        """ return a tuple of (bound method or callable, teardown method). """
        method = pypath.resolve()
        if not hasattr(method, 'im_class'):
            return method, None
        if self._instance.__class__ != method.im_class: 
            self._instance = method.im_class() 
        method = method.__get__(self._instance, method.im_class) 
        if hasattr(self._instance, 'setup_method'):
            self._instance.setup_method(method) 
        return (method, getattr(self._instance, 'teardown_method', None))

# ----------------------------------------------
# Basic Test Unit Executor 
# ----------------------------------------------
class Item(object):
    _setupcache = []
    _lastinstance = None

    def __init__(self, pypath, *args): 
        self.pypath = pypath
        self.name = pypath.basename 
        self.args = args

    def execute(self, runner):
        runner.setup_path(self.pypath) 
        target, teardown = runner.setup_method(self.pypath) 
        try:
            target(*self.args)
        finally: 
            if teardown: 
                teardown(target) 
            
class Outcome: 
    def __init__(self, **kwargs):
        assert 'msg' not in kwargs or isinstance(kwargs['msg'], str), (
            "given 'msg' argument is not a string" ) 
        self.__dict__.update(kwargs)
    def __repr__(self):
        return getattr(self, 'msg', object.__repr__(self)) 
class Passed(Outcome): pass
class Failed(Outcome): pass
class ExceptionFailure(Failed): pass
class Skipped(Outcome): pass 

class Exit(Exception):
    """ for immediate program exits without tracebacks. """

