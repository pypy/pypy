import py
from pypy.lang.smalltalk import wrapper
from pypy.lang.smalltalk import model
from pypy.lang.smalltalk import interpreter
from pypy.lang.smalltalk.error import WrapperException, FatalError
from pypy.lang.smalltalk import objspace

space = objspace.ObjSpace()

def test_simpleread():
    w_o = model.W_PointersObject(None, 2)
    w = wrapper.Wrapper(space, w_o)
    w_o._vars[0] = "hello"
    assert w.read(0) == "hello"
    w.write(1, "b")
    assert w.read(1) == "b"
    py.test.raises(WrapperException, "w.read(2)")
    py.test.raises(WrapperException, "w.write(2, \"test\")")

def test_accessor_generators():
    w_o = model.W_PointersObject(None, 1)
    w = wrapper.LinkWrapper(space, w_o)
    w_o._vars[0] = "hello"
    assert w.next_link() == "hello"
    w.store_next_link("boe")
    assert w.next_link() == "boe"

def link(w_next='foo'):
    w_object = model.W_PointersObject(None, 1)
    wrapper.LinkWrapper(space, w_object).store_next_link(w_next)
    return w_object

def test_linked_list():
    w_object = model.W_PointersObject(None,2)
    w_last = link(space.w_nil)
    w_lb1 = link(w_last)
    w_lb2 = link(w_lb1)
    w_lb3 = link(w_lb2)
    w_lb4 = link(w_lb3)
    w_first = link(w_lb4)
    linkedlist = wrapper.LinkedListWrapper(space, w_object)
    linkedlist.store_first_link(w_first)
    linkedlist.store_last_link(w_last)
    assert w_first is linkedlist.first_link()
    assert w_last is linkedlist.last_link()
    assert linkedlist.remove_first_link_of_list() is w_first
    assert linkedlist.remove_first_link_of_list() is w_lb4
    assert linkedlist.remove_first_link_of_list() is w_lb3
    assert not linkedlist.is_empty_list()
    assert linkedlist.remove_first_link_of_list() is w_lb2
    assert linkedlist.remove_first_link_of_list() is w_lb1
    assert linkedlist.remove_first_link_of_list() is w_last
    assert linkedlist.is_empty_list()
    linkedlist.add_last_link(w_first)
    assert linkedlist.first_link() is w_first
    assert linkedlist.last_link() is w_first
    linkedlist.add_last_link(w_last)
    assert linkedlist.first_link() is w_first
    assert linkedlist.last_link() is w_last
    py.test.raises(WrapperException, linkedlist.remove, space.w_nil)
    linkedlist.remove(w_first)
    assert linkedlist.first_link() is w_last
    linkedlist.store_first_link(w_first)
    wrapper.LinkWrapper(space, w_first).store_next_link(w_last)
    linkedlist.remove(w_last)
    assert linkedlist.last_link() is w_first

def new_process(w_next=space.w_nil,
                w_my_list=space.w_nil,
                w_suspended_context=space.w_nil,
                priority=0):
    w_priority = space.wrap_int(priority)
    w_process = model.W_PointersObject(None, 4)
    process = wrapper.ProcessWrapper(space, w_process)
    process.store_next_link(w_next)
    process.store_my_list(w_my_list)
    process.store_suspended_context(w_suspended_context)
    process.write(2, w_priority)
    return process

def new_processlist(processes_w=[]):
    w_processlist = model.W_PointersObject(None, 2)
    w_first = space.w_nil
    w_last = space.w_nil
    for w_process in processes_w[::-1]:
        w_first = newprocess(w_first, w_processlist).w_self
        if w_last is space.w_nil:
            w_last = w_first
    pl = wrapper.ProcessListWrapper(space, w_processlist)
    pl.store_first_link(w_first)
    pl.store_last_link(w_last)
    return pl

def new_prioritylist(prioritydict=None):
    if prioritydict is not None:
        maxpriority = max(prioritydict.keys())
    else:
        maxpriority = 5
        prioritydict = {}
    w_prioritylist = model.W_PointersObject(None, maxpriority)
    prioritylist = wrapper.Wrapper(space, w_prioritylist)
    for i in range(maxpriority):
        prioritylist.write(i, new_processlist(prioritydict.get(i, [])).w_self)
    
    return prioritylist

def new_scheduler(w_process=space.w_nil, prioritydict=None):
    priority_list = new_prioritylist(prioritydict)
    w_scheduler = model.W_PointersObject(None, 2)
    scheduler = wrapper.SchedulerWrapper(space, w_scheduler)
    scheduler.store_active_process(w_process)
    scheduler.write(0, priority_list.w_self)
    return scheduler

def new_semaphore(excess_signals=0):
    w_semaphore = model.W_PointersObject(None, 3)
    semaphore = wrapper.SemaphoreWrapper(space, w_semaphore)
    semaphore.store_excess_signals(space, excess_signals)
    return semaphore

        
class TestScheduler(object):
    def setup_method(self, meth):
        self.old_scheduler = wrapper.scheduler
        wrapper.scheduler = lambda space: scheduler
        scheduler = new_scheduler()

    def teardown_method(self, meth):
        wrapper.scheduler = self.old_scheduler

    def test_put_to_sleep(self):
        process = new_process(priority=2)
        process.put_to_sleep()
        process_list = wrapper.scheduler(space).get_process_list(2)
        assert process_list.first_link() is process_list.last_link()
        assert process_list.first_link() is process.w_self

    def test_suspend_asleep(self):
        interp, process, old_process = self.make_processes(4, 2, space.w_false, space.w_true)
        process.suspend(interp)
        process_list = wrapper.scheduler(space).get_process_list(process.priority())
        assert process_list.first_link() is process_list.last_link()
        assert process_list.first_link() is space.w_nil
        assert process.my_list() is space.w_nil

    def test_suspend_active(self):
        interp, process, old_process = self.make_processes(4, 2, space.w_false, space.w_true)
        old_process.suspend(interp)
        process_list = wrapper.scheduler(space).get_process_list(old_process.priority())
        assert process_list.first_link() is process_list.last_link()
        assert process_list.first_link() is space.w_nil
        assert old_process.my_list() is space.w_nil
        assert wrapper.scheduler(space).active_process() is process.w_self

    def new_process_consistency(self, process, old_process, interp,
                                    old_active_context, new_active_context):
        scheduler = wrapper.scheduler(space)
        assert interp.w_active_context() is new_active_context
        assert scheduler.active_process() is process.w_self
        priority_list = wrapper.scheduler(space).get_process_list(process.priority())
        assert priority_list.first_link() is priority_list.last_link()
        # activate does not remove the process from the process_list.
        # The caller of activate is responsible
        assert priority_list.first_link() is process.w_self

    def old_process_consistency(self, old_process, old_process_context):
        assert old_process.suspended_context() is old_process_context
        priority_list = wrapper.scheduler(space).get_process_list(old_process.priority())
        assert priority_list.first_link() is old_process.w_self

    def make_processes(self, sleepingpriority, runningpriority,
                             sleepingcontext, runningcontext):
        interp = interpreter.Interpreter(space)
        scheduler = wrapper.scheduler(space)
        sleeping = new_process(priority=sleepingpriority,
                               w_suspended_context=sleepingcontext)
        sleeping.put_to_sleep()
        running = new_process(priority=runningpriority)
        scheduler.store_active_process(running.w_self)
        interp.store_w_active_context(runningcontext)

        return interp, sleeping, running


    def test_activate(self):
        interp, process, old_process = self.make_processes(4, 2, space.w_false, space.w_true)
        process.activate(interp)
        self.new_process_consistency(process, old_process, interp,
                                         space.w_true, space.w_false)
       
    def test_resume(self):
        interp, process, old_process = self.make_processes(4, 2, space.w_false, space.w_true)
        process.resume(interp)
        self.new_process_consistency(process, old_process, interp,
                                         space.w_true, space.w_false)
        self.old_process_consistency(old_process, space.w_true)

        # Does not reactivate old_process because lower priority
        old_process.resume(interp)
        self.new_process_consistency(process, old_process, interp,
                                         space.w_true, space.w_false)
        self.old_process_consistency(old_process, space.w_true)

    def test_semaphore_excess_signal(self):
        semaphore = new_semaphore()
        self.space = space
        semaphore.signal(self)
        assert semaphore.excess_signals(space) == 1

    def test_highest_priority(self):
        py.test.raises(FatalError, wrapper.scheduler(space).highest_priority_process)
        interp, process, old_process = self.make_processes(4, 2, space.w_false, space.w_true)
        process.put_to_sleep()
        old_process.put_to_sleep()
        highest = wrapper.scheduler(space).highest_priority_process()
        assert highest is process.w_self
        highest = wrapper.scheduler(space).highest_priority_process()
        assert highest is old_process.w_self
        py.test.raises(FatalError, wrapper.scheduler(space).highest_priority_process)

    def test_semaphore_wait(self):
        semaphore = new_semaphore()
        interp, process, old_process = self.make_processes(4, 2, space.w_false, space.w_true)
        semaphore.wait(interp)
        assert semaphore.first_link() is old_process.w_self
        assert wrapper.scheduler(space).active_process() is process.w_self

    def test_semaphore_signal_wait(self):
        semaphore = new_semaphore()
        self.space = space
        semaphore.signal(self)
        interp, process, old_process = self.make_processes(4, 2, space.w_false, space.w_true)
        semaphore.wait(interp)
        assert semaphore.is_empty_list()
        assert wrapper.scheduler(space).active_process() is old_process.w_self
        semaphore.wait(interp)
        assert semaphore.first_link() is old_process.w_self
        assert wrapper.scheduler(space).active_process() is process.w_self

        py.test.raises(FatalError, semaphore.wait, interp)

    def test_semaphore_wait_signal(self):
        semaphore = new_semaphore()
        interp, process, old_process = self.make_processes(4, 2, space.w_false, space.w_true)

        semaphore.wait(interp)
        assert wrapper.scheduler(space).active_process() is process.w_self
        semaphore.signal(interp)
        assert wrapper.scheduler(space).active_process() is process.w_self
        process_list = wrapper.scheduler(space).get_process_list(old_process.priority())
        assert process_list.remove_first_link_of_list() is old_process.w_self

        process.write(2, space.wrap_int(1))        
        old_process.resume(interp)
        assert wrapper.scheduler(space).active_process() is old_process.w_self        
        semaphore.wait(interp)
        assert wrapper.scheduler(space).active_process() is process.w_self
        semaphore.signal(interp)
        assert wrapper.scheduler(space).active_process() is old_process.w_self        

        process_list = wrapper.scheduler(space).get_process_list(process.priority())
        assert process_list.first_link() is process.w_self
