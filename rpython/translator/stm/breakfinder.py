from rpython.translator.backendopt import graphanalyze
from rpython.translator.stm import funcgen


TRANSACTION_BREAK = set([
    'stm_enter_transactional_zone',
    'stm_leave_transactional_zone',
    'stm_hint_commit_soon',
    'jit_assembler_call',
    'stm_enter_callback_call',
    'stm_leave_callback_call',
    'stm_transaction_break',
    'stm_queue_get',
    'stm_queue_join',
    ])

for tb in TRANSACTION_BREAK:
    assert hasattr(funcgen, tb) or tb == "jit_assembler_call"

# XXX: gilanalysis in backendopt/ does the exact same thing

class TransactionBreakAnalyzer(graphanalyze.BoolGraphAnalyzer):

    def analyze_simple_operation(self, op, graphinfo):
        return op.opname in TRANSACTION_BREAK

    def analyze_external_call(self, op, seen=None):
        # if 'funcobj' releases the GIL, then the GIL-releasing
        # functions themselves will call enter/leave transactional
        # zone. This case is covered above.
        return False
