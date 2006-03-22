try:
    from pypy.translator.llvm.pyllvm import pyllvm
except:
    try:
        import sys
        sys.argv = "setup.py build_ext -i".split()
        from pypy.translator.llvm.pyllvm import setup
    except:
        import py
        py.test.skip("pyllvm failed to build")
    from pypy.translator.llvm.pyllvm import pyllvm
