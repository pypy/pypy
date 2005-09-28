from pypy.translator.tool.taskengine import SimpleTaskEngine

def test_simple():

    class ABC(SimpleTaskEngine):

        def task_A(self):
            pass

        task_A.task_deps = ['B', '?C']

        def task_B(self):
            pass

        def task_C(self):
            pass

        task_C.task_deps = ['B']

    abc = ABC()

    assert abc._plan('B') == ['B']
    assert abc._plan('C') == ['B', 'C']
    assert abc._plan('A') == ['B', 'C', 'A']
    assert abc._plan('A', skip=['C']) == ['B', 'A']
   
def test_execute():

    class ABC(SimpleTaskEngine):

        def __init__(self):
            SimpleTaskEngine.__init__(self)
            self.done = []

        def task_A(self):
            self.done.append('A')

        task_A.task_deps = ['B', '?C']

        def task_B(self):
            self.done.append('B')

        def task_C(self):
            self.done.append('C')

        task_C.task_deps = ['B']

        def _event(self, kind, goal, taskcallable):
            self.done.append((kind, goal))

    def test(goals, task_skip=[]):
        if isinstance(goals, str):
            goals = [goals]
        abc = ABC()
        abc._execute(goals, task_skip=task_skip)
        return abc.done

    def trace(goals):
        t = []
        for goal in goals:
            t.extend([('pre', goal), goal, ('post', goal)])
        return t

    assert test('B') == trace('B')
    assert test('C') == trace(['B', 'C'])
    assert test('A') == trace(['B', 'C', 'A'])
    assert test('A', ['C']) == trace(['B', 'A'])
    assert test(['B', 'C']) == trace(['B', 'C'])
    assert test(['C', 'B']) == trace(['B', 'C'])
    assert test(['B', 'A']) == trace(['B', 'C', 'A'])
    assert test(['B', 'A'], ['C']) == trace(['B', 'A'])
    assert test(['B', 'A', 'C']) == trace(['B', 'C', 'A'])
    assert test(['B', 'A', 'C'], ['C']) == trace(['B', 'C', 'A'])
