import py; py.test.skip("doesn't run with py.test")
from stackless_ import scheduler

class task_mock(object):
    number = 0
    @classmethod
    def new_id(cls):
        cls.number += 1
        return cls.number

    def __init__(self):
        self.thread_id = task_mock.new_id()
        self.next = self.prev = None

main_task = task_mock()
main_task.next = main_task.prev = main_task

def setmain():
    scheduler.current = main_task

def check_chain(chain):
    assert chain.next is not None
    assert chain.prev is not None
    visited = set()
    nextcount = prevcount = 0
    if chain.next == chain.prev == chain:
        return True
    next = chain.next
    while next is not chain:
        if next in visited:
            return False
        nextcount += 1
        visited.add(next)
        next = next.next
    visited = set()
    prev = chain.prev
    while prev is not chain:
        if prev in visited:
            return False
        prevcount += 1
        visited.add(prev)
        prev = prev.prev

    return nextcount == prevcount


class TestStackless(object):

    def setup_method(self, name):
        scheduler.reset()
        main_task.next = main_task.prev = main_task
        task_mock.number = 1
        setmain()

    def test_insert(self):
        t1 = task_mock()
        t2 = task_mock()
        scheduler.current_insert(t1)
        assert check_chain(scheduler.chain)
        setmain()
        scheduler.current_insert(t2)
        assert check_chain(scheduler.chain)
        assert main_task.next is t1
        assert main_task.prev is t2

    def test_insert_after(self):
        t1 = task_mock()
        t2 = task_mock()
        scheduler.current_insert_after(t1)
        assert check_chain(scheduler.chain)
        setmain()
        scheduler.current_insert_after(t2)
        assert check_chain(scheduler.chain)
        assert main_task.prev is t1
        assert main_task.next is t2

    def test_current_remove(self):
        t1 = task_mock()
        t2 = task_mock()
        scheduler.current_insert(t1)
        setmain()
        scheduler.current_insert(t2)
        scheduler.current = t1
        assert len(scheduler) == 3
        scheduler.current_remove()
        assert len(scheduler) == 2 and t1 not in scheduler._content()
