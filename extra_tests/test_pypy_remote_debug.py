import os
import sys
import pytest
import subprocess
import ctypes

try:
    import __pypy__
except ImportError:
    pytest.skip('can only run these tests on pypy')

if not sys.platform.startswith('linux'):
    pytest.skip('only works on linux so far')

import _pypy_remote_debug
import _vmprof

def test_parse_maps():
    maps = _pypy_remote_debug._read_and_parse_maps('self', sys.executable)
    assert os.path.realpath(sys.executable) == maps[0]['file']

def test_elf_find_symbol():
    pid = os.getpid()
    file, base_addr = _pypy_remote_debug._find_file_and_base_addr(pid)
    with open(file, 'rb') as f:
        value = _pypy_remote_debug.elf_find_symbol(f, b'pypysig_counter')
    # compare against output of nm
    out = subprocess.check_output(['nm', file])
    if not out:
        pytest.skip("test can't work on stripped binary")
    for line in out.decode('ascii').splitlines():
        if 'pypysig_counter' in line:
            addr, _, _ = line.split()
            assert int(addr, 16) == value
            break
    else:
        assert False
    assert value

def test_elf_read_first_load_section():
    pid = os.getpid()
    file, base_addr = _pypy_remote_debug._find_file_and_base_addr(pid)
    with open(file, 'rb') as f:
        phdr = _pypy_remote_debug.elf_read_first_load_section(f)

    # compare against output of objdump
    out = subprocess.check_output(['objdump', '-p', file])
    for line in out.decode('ascii').splitlines():
        if 'LOAD' in line:
            outline = line
            break
    content = outline.split()[1:]
    for name, value in zip(content[::2], content[1::2]):
        if name == 'vaddr':
            assert int(value, 16) == phdr.vaddr

def skip_on_oserror(func):
    def wrapper():
        try:
            return func()
        except OSError as e:
            if "Operation not permitted" in str(e):
                pytest.skip('yama ptrace_scope likely forbids read_memory call')
    return wrapper

@skip_on_oserror
def test_read_memory():
    # test using local memory
    ffi = _pypy_remote_debug.ffi
    pid = os.getpid()
    data = b'hello, world!'
    sourcebuffer = ffi.new('char[]', len(data))
    for i in range(len(data)):
        sourcebuffer[i] = data[i:i+1]
    result = _pypy_remote_debug.read_memory(pid, int(ffi.cast('intptr_t', sourcebuffer)), len(data))
    assert result == data

@skip_on_oserror
def test_write_memory():
    # test using local memory
    ffi = _pypy_remote_debug.ffi
    pid = os.getpid()
    data = b'hello, world!'
    targetbuffer = ffi.new('char[]', len(data))
    result = _pypy_remote_debug.write_memory(pid, int(ffi.cast('intptr_t', targetbuffer)), data)
    assert ffi.buffer(targetbuffer)[:] == data

@skip_on_oserror
def test_cookie():
    pid = os.getpid()
    addr = _pypy_remote_debug.compute_remote_addr(pid)
    cookie = _pypy_remote_debug.read_memory(pid, addr + _pypy_remote_debug.COOKIE_OFFSET, 8)
    assert cookie == b'pypysigs'

def test_remote_find_file_and_base_addr():
    code = """
import sys
sys.stdin.readline()
"""
    out = subprocess.Popen([sys.executable, '-c',
         code], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    pid = out.pid
    file, base_addr = _pypy_remote_debug._find_file_and_base_addr(pid)
    assert file == sys.executable or 'libpypy' in file
    out.stdin.write(b'1\n')
    out.stdin.flush()
    out.wait()

def test_integration(tmpdir):
    import __pypy__
    code = """
import time
for i in range(10):
    time.sleep(0.1)
print("done")
"""
    debug_code = rb"""
import sys, os
sys.stdout.write('hello from %s\n' % os.getpid())
sys.stdout.flush()
"""
    debug_script = tmpdir.join('debug.py')
    debug_script.write(debug_code)
    for func in (_pypy_remote_debug.start_debugger, __pypy__.remote_exec):
        out = subprocess.Popen([sys.executable, '-c',
             code], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        pid = out.pid
        func(pid, str(debug_script).encode('utf-8'))
        l = out.stdout.readline()
        assert l == b'Executing remote debugger script %s\n' % str(debug_script).encode('utf-8')
        l = out.stdout.readline()
        assert l == ('hello from %s\n' % pid).encode('ascii')
        exitcode = out.wait()
        assert exitcode == 0

def test_disable_remote_debug(tmpdir):
    import __pypy__
    code = """
import time
for i in range(10):
    time.sleep(0.1)
print("done")
"""
    debug_code = rb"""
import sys, os
sys.stdout.write('hello from %s\n' % os.getpid())
sys.stdout.flush()
"""
    debug_script = tmpdir.join('debug.py')
    debug_script.write(debug_code)
    for func in (_pypy_remote_debug.start_debugger, __pypy__.remote_exec):
        # disable with -X option
        out = subprocess.Popen([sys.executable, '-X', 'disable-remote-debug', '-c',
             code], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        pid = out.pid
        func(pid, str(debug_script).encode('utf-8'))
        l = out.stdout.readline()
        assert l == b'done\n'

        # disable with env var option
        env = os.environ.copy()
        env['PYTHON_DISABLE_REMOTE_DEBUG'] = 'true'
        out = subprocess.Popen([sys.executable, '-c',
             code], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE,
             env=env)
        pid = out.pid
        func(pid, str(debug_script).encode('utf-8'))
        l = out.stdout.readline()
        assert l == b'done\n'

# __________________________________________________________
# symbolification tests


def load_so_or_skip(name):
    try:
        return ctypes.CDLL(name)
    except OSError:
        pytest.skip("couldn't find %s" % name)


def test_proc_map_find_base_map():
    pid = os.getpid()
    so = load_so_or_skip('libexpat.so')
    address_of_function = (ctypes.cast(so.XML_Parse, ctypes.c_void_p)).value
    map = _pypy_remote_debug._proc_map_find_base_map(address_of_function)
    assert 'libexpat.so' in map['file']

def test_proc_map_find_base_map_bug():
    # the entries can be non-consecutive
    s = """\
eb284000-eb285000 rw-p 00000000 00:00 0 
eb285000-eb286000 r-xp 01a80000 103:05 8993453                           /home/user/pypy/bin/libpypy-c.so
eb286000-eb287000 rw-p 00000000 00:00 0 
eb287000-eb288000 r--p 00000000 103:05 8993868                           /home/user/pypy/lib_pypy/_pypy_util_cffi_inner.pypy-73.so
eb288000-eb289000 r-xp 00001000 103:05 8993868                           /home/user/pypy/lib_pypy/_pypy_util_cffi_inner.pypy-73.so
eb289000-eb28a000 r--p 00002000 103:05 8993868                           /home/user/pypy/lib_pypy/_pypy_util_cffi_inner.pypy-73.so
eb28a000-eb28b000 r--p 00002000 103:05 8993868                           /home/user/pypy/lib_pypy/_pypy_util_cffi_inner.pypy-73.so
eb28b000-eb28c000 rw-p 00003000 103:05 8993868                           /home/user/pypy/lib_pypy/_pypy_util_cffi_inner.pypy-73.so
eb28c000-eb28e000 r--p 00570000 103:05 65313846                          /usr/lib/locale/locale-archive
eb28e000-eb8f6000 r--p 00000000 103:05 8993453                           /home/user/pypy/bin/libpypy-c.so
eb8f6000-ecd10000 r-xp 00668000 103:05 8993453                           /home/user/pypy/bin/libpypy-c.so
ecd10000-ed32e000 r--p 01a82000 103:05 8993453                           /home/user/pypy/bin/libpypy-c.so
ed32e000-ed32f000 ---p 020a0000 103:05 8993453                           /home/user/pypy/bin/libpypy-c.so
ed32f000-ed33d000 r--p 020a0000 103:05 8993453                           /home/user/pypy/bin/libpypy-c.so
ed33d000-ede21000 rw-p 020ae000 103:05 8993453                           /home/user/pypy/bin/libpypy-c.so
ede21000-ede3f000 rw-p 00000000 00:00 0 
ede3f000-ede47000 rw-p 02b92000 103:05 8993453                           /home/user/pypy/bin/libpypy-c.so
"""
    maps = _pypy_remote_debug._parse_maps(lineiter=iter(s.splitlines()))
    map = _pypy_remote_debug._proc_map_find_base_map(0xeb28f000, maps=maps)
    assert map['file'] == '/home/user/pypy/bin/libpypy-c.so'
    assert map['from_'] == 0xeb285000

def test_symbolify():
    pid = os.getpid()
    so = load_so_or_skip('libexpat.so')
    address_of_function = (ctypes.cast(so.XML_Parse, ctypes.c_void_p)).value
    name, filename = _pypy_remote_debug._symbolify(address_of_function)
    assert name == b'XML_Parse'
    assert 'libexpat.so' in filename

def test_symbolify_all():
    pid = os.getpid()
    so = load_so_or_skip('libexpat.so')
    names = ['XML_Parse', 'XML_GetBase']
    all = []
    for name in names:
        address_of_function = (ctypes.cast(getattr(so, name), ctypes.c_void_p)).value
        all.append(address_of_function)
    all.append(1)
    res = _pypy_remote_debug._symbolify_all(all)
    for index, name in enumerate(names):
        addr = all[index]
        assert res[addr][0] == name.encode('ascii')
        assert 'libexpat.so' in res[addr][1]

def test_symbolify_pypy_function():
    addr = _pypy_remote_debug.compute_remote_addr()
    name, filename = _pypy_remote_debug._symbolify(addr)
    assert name == b'pypysig_counter'
    addr = _pypy_remote_debug.compute_remote_addr(symbolname=b'pypy_g_DiskFile_read')
    name, filename = _pypy_remote_debug._symbolify(addr)
    assert name == b'pypy_g_DiskFile_read'

def test_symbolify_all_pypy_function():
    names = [b'pypy_g_DiskFile_read', b'pypy_g_DiskFile_seek']
    all = []
    for name in names:
        address_of_function = _pypy_remote_debug.compute_remote_addr('self', name)
        all.append(address_of_function)
    all.append(1)
    res = _pypy_remote_debug._symbolify_all(all)
    for index, name in enumerate(names):
        addr = all[index]
        assert res[addr][0] == name

@pytest.mark.skipif(not hasattr(_vmprof, 'resolve_addr'), reason="not implemented")
def test_symbolify_vmprof():
    import _vmprof, ctypes
    so = load_so_or_skip('libexpat.so')
    address_of_function = (ctypes.cast(so.XML_Parse, ctypes.c_void_p)).value
    name, lineno, filename = _vmprof.resolve_addr(address_of_function)
    assert name == b'XML_Parse'
    assert 'libexpat.so' in filename

    result = _vmprof.resolve_addr(1)
    assert result is None

@pytest.mark.skipif(not hasattr(_vmprof, 'resolve_many_addrs'), reason="not implemented")
def test_symbolify_vmprof_many():
    import _vmprof, ctypes
    names = [b'pypy_g_DiskFile_read', b'pypy_g_DiskFile_seek']
    all = []
    for name in names:
        address_of_function = _pypy_remote_debug.compute_remote_addr('self', name)
        all.append(address_of_function)

    names2 = ['XML_Parse', 'XML_GetBase']
    so = load_so_or_skip('libexpat.so')
    for name in names2:
        address_of_function = (ctypes.cast(getattr(so, name), ctypes.c_void_p)).value
        all.append(address_of_function)
    all.append(1)

    res = _vmprof.resolve_many_addrs(all)
    for index, name in enumerate(names + names2):
        addr = all[index]
        if isinstance(name, str):
            name = name.encode('utf-8')
        assert res[addr][0] == name
