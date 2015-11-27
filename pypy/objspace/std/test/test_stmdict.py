import py
from pypy.objspace.std.stmdict import StmDictStrategy
from pypy.objspace.std.test.test_dictmultiobject import (
    BaseTestRDictImplementation)


class TestStmDictImplementation(BaseTestRDictImplementation):
    StrategyClass = StmDictStrategy
    GenericDictStrategy = StmDictStrategy
