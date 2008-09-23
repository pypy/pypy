import py; py.test.skip("clonable coroutines not really maintained any more")

from pypy.rlib.rcoroutine import AbstractThunk
from pypy.module._stackless.rclonable import InterpClonableCoroutine as ClonableCoroutine

class ChoicePointHolder(object):
    def __init__(self):
        self.choicepoints = []
        self.clone_me = False
        self.answer = 0
        self.solutions_count = 0

    def next_choice(self):
        return self.choicepoints.pop()

    def add(self, choice, answer=0):
        self.choicepoints.append((choice, answer))

    def more_choices(self):
        return bool(self.choicepoints)

    def choice(self):
        #os.write(1, "choice\n")
        self.clone_me = True
        self.g_main.switch()
        #os.write(1, "answer: %d\n" % (self.answer,))
        return self.answer

    def fail(self):
        self.g_main.switch()
        assert False

choicepoints = ChoicePointHolder()

# ____________________________________________________________

class SearchTask(AbstractThunk):
    def call(self):
        path = []
        for i in range(10):
            res = choicepoints.choice()
            assert len(path) == i
            path.append(res)
            #os.write(1, "{%x} trying: %s\n" % (id(path), path))
            if i == 3:
                import gc; gc.collect()
        #os.write(1, "{%x} found a solution: %s\n" % (id(path), path))
        choicepoints.solutions_count += 1

# ____________________________________________________________


class SearchAllTask(AbstractThunk):
    def call(self):
        search_coro = ClonableCoroutine()
        search_coro.bind(SearchTask())
        choicepoints.add(search_coro)

        #os.write(1, "starting\n")
        while choicepoints.more_choices():
            searcher, nextvalue = choicepoints.next_choice()
            choicepoints.clone_me = False
            choicepoints.answer = nextvalue
            #os.write(1, '<<< {%x} %d\n' % (id(searcher), nextvalue))
            searcher.switch()
            #os.write(1, '>>> %d\n' % (choicepoints.clone_me,))
            if choicepoints.clone_me:
                searcher2 = searcher.clone()
                #os.write(1, 'searcher = {%x}, searcher2 = {%x}\n' % (
                #    id(searcher), id(searcher2)))
                choicepoints.add(searcher, 5)
                choicepoints.add(searcher2, 4)

def entry_point():
    choicepoints.g_main = ClonableCoroutine()
    choicepoints.g_main.bind(SearchAllTask())
    choicepoints.g_main.switch()
    return choicepoints.solutions_count

def test_choicepoint():
    from pypy.translator.c.test import test_newgc
    tester = test_newgc.TestUsingStacklessFramework()
    fn = tester.getcompiled(entry_point)
    res = fn()
    assert res == 2 ** 10
