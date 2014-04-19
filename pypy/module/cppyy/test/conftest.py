import py

@py.test.mark.tryfirst
def pytest_runtest_setup(item):
    print item
    if py.path.local.sysfind('genreflex') is None:
        #py.test.skip("genreflex is not installed")

        # build the dummy CAPI

        import os
        from rpython.translator.tool.cbuild import ExternalCompilationInfo
        from rpython.translator import platform

        from rpython.rtyper.lltypesystem import rffi

        pkgpath = py.path.local(__file__).dirpath().join(os.pardir)
        srcpath = pkgpath.join('src')
        incpath = pkgpath.join('include')

        eci = ExternalCompilationInfo(
            separate_module_files=[srcpath.join('dummy_backend.cxx')],
            include_dirs=[incpath],
            use_cpp_linker=True,
        )

        soname = platform.platform.compile(
            [], eci,
            outputfilename='libcppyy_backend',
            standalone=False)

        import pypy.module.cppyy.capi.loadable_capi as lcapi
        lcapi.reflection_library = str(soname)
