import py

@py.test.mark.tryfirst
def pytest_runtest_setup(item):
    if py.path.local.sysfind('genreflex') is None:
        import pypy.module.cppyy.capi.loadable_capi as lcapi
        if 'dummy' in lcapi.reflection_library:
            # run only tests that are covered by the dummy backend and tests
            # that do not rely on reflex
            if not item.location[0] in ['test_helper.py', 'test_cppyy.py'] or \
                (item.location[0] == 'test_cppyy.py' and not 'TestCPPYYImplementation' in item.location[2]):
                py.test.skip("genreflex is not installed")

def pytest_configure(config):
    if py.path.local.sysfind('genreflex') is None:
        import pypy.module.cppyy.capi.loadable_capi as lcapi
        try:
            import ctypes
            ctypes.CDLL(lcapi.reflection_library)
        except Exception, e:
            # build dummy backend (which has reflex info and calls hard-wired)
            import os
            from rpython.translator.tool.cbuild import ExternalCompilationInfo
            from rpython.translator.platform import platform

            from rpython.rtyper.lltypesystem import rffi

            pkgpath = py.path.local(__file__).dirpath().join(os.pardir)
            srcpath = pkgpath.join('src')
            incpath = pkgpath.join('include')

            eci = ExternalCompilationInfo(
                separate_module_files=[srcpath.join('dummy_backend.cxx')],
                include_dirs=[incpath],
                use_cpp_linker=True,
            )

            soname = platform.compile(
                [], eci,
                outputfilename='libcppyy_dummy_backend',
                standalone=False)

            lcapi.reflection_library = str(soname)
