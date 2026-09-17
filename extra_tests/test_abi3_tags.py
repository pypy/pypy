"""Tests for lib_pypy/_pypy_abi3_tags.py: PyPy advertising cp3XY-abi3 wheel
tags to every copy of `packaging.tags` that gets imported."""
import sys
import textwrap

import pytest

abi3_tags = pytest.importorskip('_pypy_abi3_tags')

FAKE_TAGS_PY = textwrap.dedent('''
    from collections import namedtuple
    Tag = namedtuple('Tag', 'interpreter abi platform')

    def platform_tags():
        return ['fakeplat']

    def compatible_tags(python_version=None, interpreter=None, platforms=None):
        platforms = list(platforms or platform_tags())
        for p in platforms:
            yield Tag('py3', 'none', p)
        if interpreter:
            yield Tag(interpreter, 'none', 'any')

    def sys_tags():
        yield Tag('pp312', 'pypy312_pp80', 'fakeplat')
        yield from compatible_tags(interpreter='pp3')
''')

VERSION = 'cp%d%d' % sys.version_info[:2]


@pytest.fixture
def fake_packaging(tmp_path, monkeypatch):
    """A `<unique>.packaging.tags` module on sys.path, mimicking the shape of
    the real one (vendored copies live at e.g. `pip._vendor.packaging.tags`)."""
    vendor = 'fakevendor_%d' % id(tmp_path)
    pkg = tmp_path / vendor / 'packaging'
    pkg.mkdir(parents=True)
    (tmp_path / vendor / '__init__.py').write_text('')
    (pkg / '__init__.py').write_text('')
    (pkg / 'tags.py').write_text(FAKE_TAGS_PY)
    monkeypatch.syspath_prepend(str(tmp_path))
    for name in list(sys.modules):
        if name.startswith(vendor):
            monkeypatch.delitem(sys.modules, name)
    return vendor + '.packaging.tags'


def _import(name):
    __import__(name)
    return sys.modules[name]


def test_finder_installed():
    assert any(isinstance(f, abi3_tags._Abi3TagsFinder)
               for f in sys.meta_path)


def test_patched_on_import(fake_packaging):
    tags = _import(fake_packaging)
    assert getattr(tags, abi3_tags._PATCHED_ATTR)
    assert tags.compatible_tags.__wrapped__ is not tags.compatible_tags


def test_abi3_tags_for_running_interpreter(fake_packaging):
    tags = _import(fake_packaging)
    result = list(tags.compatible_tags(interpreter='pp%d%d' % sys.version_info[:2],
                                       platforms=['p1', 'p2']))
    abi3 = [t for t in result if t.abi == 'abi3']
    assert abi3 == [tags.Tag(VERSION, 'abi3', 'p1'),
                    tags.Tag(VERSION, 'abi3', 'p2')]
    assert result[:2] == abi3
    assert result[2:] == [tags.Tag('py3', 'none', 'p1'),
                          tags.Tag('py3', 'none', 'p2'),
                          tags.Tag('pp%d%d' % sys.version_info[:2], 'none', 'any')]


def test_floor_is_312(fake_packaging):
    tags = _import(fake_packaging)
    result = list(tags.compatible_tags(interpreter='pp3', platforms=['p']))
    versions = {t.interpreter for t in result if t.abi == 'abi3'}
    assert VERSION in versions
    assert 'cp311' not in versions
    assert 'cp310' not in versions
    assert all(int(v[3:]) >= 12 for v in versions)


def test_no_abi3_for_other_targets(fake_packaging):
    tags = _import(fake_packaging)
    for interpreter in ['pp311', 'pp310', 'cp312', 'cp3', None]:
        result = list(tags.compatible_tags(interpreter=interpreter,
                                           platforms=['p']))
        assert not [t for t in result if t.abi == 'abi3'], interpreter


def test_sys_tags_goes_through_patch(fake_packaging):
    tags = _import(fake_packaging)
    result = [str(t) for t in tags.sys_tags()]
    assert '%s-abi3-fakeplat' % VERSION in [
        '-'.join(t) for t in tags.sys_tags()]
    assert result.index(str(tags.Tag('pp312', 'pypy312_pp80', 'fakeplat'))) == 0


def test_patch_is_idempotent(fake_packaging):
    tags = _import(fake_packaging)
    patched = tags.compatible_tags
    abi3_tags.patch_tags_module(tags)
    assert tags.compatible_tags is patched


def test_from_import_sees_patched_function(fake_packaging):
    tags = _import(fake_packaging)
    ns = {}
    exec('from %s import compatible_tags' % fake_packaging, ns)
    assert ns['compatible_tags'] is tags.compatible_tags


@pytest.mark.skipif(sys.platform == 'win32', reason='no abi3 suffix on win32')
def test_extension_suffix():
    import importlib.machinery
    assert '.abi3.so' in importlib.machinery.EXTENSION_SUFFIXES
    assert '.so' not in importlib.machinery.EXTENSION_SUFFIXES
