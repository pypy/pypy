"""App-level tests for support.py"""
import sys
import py

from pypy.module.micronumpy.test.test_base import BaseNumpyAppTest
from pypy.conftest import option

class AppTestPicklingNumpy(BaseNumpyAppTest):
    spaceconfig = dict(usemodules=["micronumpy", "struct", "binascii"])

    def setup_class(cls):
        if option.runappdirect and '__pypy__' not in sys.builtin_module_names:
            py.test.skip("pypy only test")
        BaseNumpyAppTest.setup_class.im_func(cls)

    def test_pickle_module(self):
        import pickle
        import numpy as np

        pkl_str = pickle.dumps(np.array([1,2,3], dtype=np.int8))

        # print repr(pkl_str)

        assert '_numpypy' not in pkl_str
        assert 'numpy.core.multiarray' in pkl_str

        # with open('ndarray-pypy-compat-cpython.pkl', 'w') as f:
        #     pickle.dump(np.array([1,2,3], dtype=np.int8), f)

    def test_cPickle_module(self):
        import cPickle as pickle
        import numpy as np

        pkl_str = pickle.dumps(np.array([1,2,3], dtype=np.int8))

        # print repr(pkl_str)

        assert '_numpypy' not in pkl_str
        assert 'numpy.core.multiarray' in pkl_str

        # with open('ndarray-pypy-compat-cpython.pkl', 'w') as f:
        #     pickle.dump(np.array([1,2,3], dtype=np.int8), f)

