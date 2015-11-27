from rpython.translator.backendopt import graphanalyze
from rpython.translator.stm import funcgen
from rpython.translator.backendopt.gilanalysis import (
    GilAnalyzer, TRANSACTION_BREAK)

# simple check if all operations exist in funcgen
for tb in TRANSACTION_BREAK:
    assert hasattr(funcgen, tb) or tb == "jit_assembler_call"


class TransactionBreakAnalyzer(GilAnalyzer):
    """adds a cache to GilAnalyzer"""

    def __init__(self, *args, **kwargs):
        super(TransactionBreakAnalyzer, self).__init__(*args, **kwargs)
        self._cache = {}

    def analyze(self, op, *args, **kwargs):
        if op in self._cache:
            return self._cache[op]
        res = super(TransactionBreakAnalyzer, self).analyze(op, *args, **kwargs)
        self._cache[op] = res
        return res
