"""
this test should probably not run from CPython or py.py.
I'm not entirely sure, how to do that.
"""
from py.test import skip
try:
    import stackless
    stackless_c = True
    if 'coroutine' in dir(stackless):
        stackless_c = False
        raise ImportError("We are running pypy-c")
except ImportError:
    stackless_c = False
    try:
        from pypy.lib import stackless_new as stackless
    except ImportError, e:
        skip('cannot import stackless: %s' % (e,))



class Test_StacklessPickling:

    def test_basic_tasklet_pickling(self):
        try:
            import stackless
        except ImportError:
            skip("can't load stackless and don't know why!!!")
        from stackless import run, schedule, tasklet
        import pickle

        output = []

        import new

        mod = new.module('mod')
        mod.output = output

        exec """from stackless import schedule
        
def aCallable(name):
    output.append(('b', name))
    schedule()
    output.append(('a', name))
""" in mod.__dict__
        import sys
        sys.modules['mod'] = mod
        aCallable = mod.aCallable


        tasks = []
        for name in "ABCDE":
            tasks.append(tasklet(aCallable)(name))

        schedule()

        assert output == [('b', x) for x in "ABCDE"]
        del output[:]
        pickledTasks = pickle.dumps(tasks)

        schedule()
        assert output == [('a', x) for x in "ABCDE"]
        del output[:]
        
        unpickledTasks = pickle.loads(pickledTasks)
        for task in unpickledTasks:
            task.insert()

        schedule()
        assert output == [('a', x) for x in "ABCDE"]

