from rpython.translator.backendopt import graphanalyze
from rpython.translator.stm import funcgen
from rpython.translator.backendopt.gilanalysis import GilAnalyzer

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

# XXX: gilanalysis in backendopt/ does the exact same thing:

TransactionBreakAnalyzer = GilAnalyzer
