"""Make wheel installers accept CPython abi3 wheels on PyPy.

PyPy >= 3.12 can load CPython abi3 wheels whose Py_LIMITED_API floor is
3.12 or newer: cpyext's PyObject header matches CPython's, the limited-API
symbols are exported under their bare CPython names, and from 3.12 on the
limited API turns Py_INCREF/Py_DECREF into calls to _Py_IncRef/_Py_DecRef.
Wheels with an older floor (cp37-abi3 ... cp311-abi3) still inline the
ob_refcnt arithmetic and must not be accepted, so the floor here is a hard
3.12, independent of the running version.

Which wheel tags an interpreter supports is decided by the `packaging`
library, of which several copies exist (standalone, vendored in pip,
setuptools, ...), and none of them know that a non-CPython interpreter can
support abi3.  Rather than patch each copy, install a sys.meta_path finder
that wraps the loader of any `packaging.tags` module (`packaging.tags`,
`pip._vendor.packaging.tags`, ...) and, once the module has executed,
replaces its `compatible_tags` with one that first yields
cp3XY-abi3-<platform> for 3.12 <= XY <= the running version.  That slot is
after the native pp3XY tags (a PyPy wheel still wins) and before the
py3-none-* tags (an abi3 binary wheel beats a pure-Python one, as on
CPython), and it is reached by both `sys_tags()` and pip's own
`get_supported()`, which bypasses `sys_tags()`.
"""
import sys

_ABI3_FLOOR_MINOR = 12
_TAGS_MODULE = 'packaging.tags'
_PATCHED_ATTR = '_pypy_abi3_patched'


def _is_tags_module(fullname):
    return (fullname == _TAGS_MODULE or
            fullname.endswith('.' + _TAGS_MODULE))


def _abi3_interpreters():
    version = sys.version_info[:2]
    return ('pp%d' % version[0], 'pp%d%d' % version)


def _abi3_versions():
    major, minor = sys.version_info[:2]
    return ['cp%d%d' % (major, m)
            for m in range(minor, _ABI3_FLOOR_MINOR - 1, -1)]


def patch_tags_module(tags):
    if getattr(tags, _PATCHED_ATTR, False):
        return
    orig_compatible_tags = tags.compatible_tags
    Tag = tags.Tag
    interpreters = _abi3_interpreters()
    versions = _abi3_versions()

    def compatible_tags(python_version=None, interpreter=None,
                        platforms=None):
        platforms = list(platforms or tags.platform_tags())
        if interpreter in interpreters:
            for version in versions:
                for platform_ in platforms:
                    yield Tag(version, 'abi3', platform_)
        yield from orig_compatible_tags(python_version, interpreter,
                                        platforms)

    compatible_tags.__wrapped__ = orig_compatible_tags
    compatible_tags.__doc__ = orig_compatible_tags.__doc__
    tags.compatible_tags = compatible_tags
    setattr(tags, _PATCHED_ATTR, True)


class _PatchingLoader:
    def __init__(self, loader):
        self._loader = loader

    def create_module(self, spec):
        return self._loader.create_module(spec)

    def exec_module(self, module):
        self._loader.exec_module(module)
        patch_tags_module(module)

    def __getattr__(self, name):
        return getattr(self._loader, name)


class _Abi3TagsFinder:
    def find_spec(self, fullname, path=None, target=None):
        if not _is_tags_module(fullname):
            return None
        meta_path = sys.meta_path
        try:
            start = meta_path.index(self) + 1
        except ValueError:
            start = 0
        for finder in meta_path[start:]:
            find_spec = getattr(finder, 'find_spec', None)
            if find_spec is None:
                continue
            spec = find_spec(fullname, path, target)
            if spec is not None:
                break
        else:
            return None
        loader = spec.loader
        if loader is None or not hasattr(loader, 'exec_module'):
            return None
        spec.loader = _PatchingLoader(loader)
        return spec


def install():
    if sys.platform == 'win32':
        # abi3 wheels ship a bare '.pyd' there, which _imp.extension_suffixes()
        # does not (yet) include
        return
    if not any(isinstance(finder, _Abi3TagsFinder) for finder in sys.meta_path):
        sys.meta_path.insert(0, _Abi3TagsFinder())
    for name, module in list(sys.modules.items()):
        if _is_tags_module(name) and module is not None:
            patch_tags_module(module)


install()
