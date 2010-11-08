import py
import sys, os
from pypy.tool.udir import udir

dirpath = py.path.local(__file__).dirpath().dirpath()


def run(filename, outputname):
    filepath = dirpath.join(filename)
    tmpdir2 = udir.ensure('testcache-' + filename, dir=True)
    tmpdir = tmpdir2.ensure('ctypes_config_cache', dir=True)
    tmpdir.join('__init__.py').write('\n')
    tmpdir.join('dumpcache.py').write(dirpath.join('dumpcache.py').read())
    path = sys.path[:]
    try:
        sys.path.insert(0, str(tmpdir))
        execfile(str(filepath), {})
    finally:
        sys.path[:] = path
        sys.modules.pop('dumpcache', None)
    #
    outputpath = tmpdir.join(outputname)
    assert outputpath.check(exists=1)
    d = {}
    try:
        sys.path.insert(0, str(tmpdir2))
        execfile(str(outputpath), d)
    finally:
        sys.path[:] = path
        sys.modules.pop('ctypes_config_cache', None)
    return d


def test_syslog():
    d = run('syslog.ctc.py', '_syslog_cache.py')
    assert 'LOG_NOTICE' in d

def test_hashlib():
    d = run('hashlib.ctc.py', '_hashlib_cache.py')
    assert hasattr(d['EVP_MD_CTX'], 'digest')

def test_resource():
    d = run('resource.ctc.py', '_resource_cache.py')
    assert 'RLIM_NLIMITS' in d

def test_pyexpat():
    d = run('pyexpat.ctc.py', '_pyexpat_cache.py')
    assert 'XML_COMBINED_VERSION' in d

def test_locale():
    d = run('locale.ctc.py', '_locale_cache.py')
    assert 'LC_ALL' in d
    assert 'CHAR_MAX' in d
