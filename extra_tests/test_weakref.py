import os
import sys
import textwrap
import subprocess
import gc
import weakref

import pytest


@pytest.mark.pypy_only
@pytest.mark.parametrize('container_type', [
    weakref.WeakSet, weakref.WeakKeyDictionary, weakref.WeakValueDictionary,
])
def test_len_during_finalization(container_type):
    container = container_type()
    observations = []

    class Item:
        def __del__(self):
            # PyPy clears weakrefs before __del__, but their callbacks may
            # not have removed the dead entries from the container yet.
            observations.append((len(container), list(container)))

    item = Item()
    if container_type is weakref.WeakSet:
        container.add(item)
    elif container_type is weakref.WeakKeyDictionary:
        container[item] = 42
    else:
        container['key'] = item
    del item
    gc.collect()
    # Check outside __del__, where assertion failures would be unraisable.
    assert observations == [(0, [])]


def test_WeakValueDictionary_len(tmpdir):
    src = textwrap.dedent("""
        from weakref import WeakValueDictionary
        class Foo:
            pass
        N = 1000
        D = WeakValueDictionary()
        for i in range(N):
            D[i] = Foo()

        for i in range(10):
            x = len(D)
        print('OK')
    """)
    testfile = tmpdir.join('testfile.py')
    testfile.write(src)
    #
    # by setting a very small PYPY_GC_NURSERY value, we force running a minor
    # collection inside WeakValueDictionary.__len__. We just check that the
    # snippet above completes correctly, instead of raising "dictionary
    # changed size during iteration"
    env = {'PYPY_GC_NURSERY': '1k'}
    env['PATH'] = os.environ.get("PATH")
    subprocess.run([sys.executable, str(testfile)], env=env, check=True)


def test_WeakKeyDictionary_len(tmpdir):
    src = textwrap.dedent("""
        from weakref import WeakKeyDictionary
        class Foo:
            pass
        N = 1000
        D = WeakKeyDictionary()
        for i in range(N):
            D[Foo()] = i

        for i in range(10):
            x = len(D)
        print('OK')
    """)
    testfile = tmpdir.join('testfile.py')
    testfile.write(src)
    #
    # by setting a very small PYPY_GC_NURSERY value, we force running a minor
    # collection inside WeakValueDictionary.__len__. We just check that the
    # snippet above completes correctly, instead of raising "dictionary
    # changed size during iteration"
    env = {'PYPY_GC_NURSERY': '1k'}
    env['PATH'] = os.environ.get("PATH")
    subprocess.run([sys.executable, str(testfile)], env=env, check=True)
