from pypy.conftest import gettestobjspace, option
from py.test import skip

class AppTest_StacklessPickling:

    def setup_class(cls):
        if not option.runappdirect:
            skip('pure appdirect test (run with -A)')
        cls.space = gettestobjspace(usemodules=('_stackless',))

    def test_basic_tasklet_pickling(self):
        import stackless
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

