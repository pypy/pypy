import thread, time
from rpython.rlib.rstm import ThreadLocalReference

def test_tlref_untranslated():
    class FooBar(object):
        pass
    t = ThreadLocalReference(FooBar)
    results = []
    def subthread():
        x = FooBar()
        t.set(x)
        time.sleep(0.2)
        results.append(t.get() is x)
    for i in range(5):
        thread.start_new_thread(subthread, ())
    time.sleep(0.5)
    assert results == [True] * 5
