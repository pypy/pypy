from pypy.objspace.flow.test import test_model
from pypy.objspace.flow.model import checkgraph

import pickle


import py; py.test.skip("pickling graphs not really used")


def test_pickle_block():
    # does not raise
    s = pickle.dumps(test_model.graph.startblock)
    # does not raise
    block = pickle.loads(s)
   
def test_pickle_graph():
    # does not raise
    s = pickle.dumps(test_model.graph)
    # does not raise
    newgraph = pickle.loads(s)
    checkgraph(newgraph)
