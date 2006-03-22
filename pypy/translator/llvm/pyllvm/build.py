try:
    from pypy.translator.llvm.pyllvm import pyllvm
except:
    import py
    py.test.skip("pyllvm not found: run 'python setup.py build_ext -i' in translator/llvm/pyllvm")
