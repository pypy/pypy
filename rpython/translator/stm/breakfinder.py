from rpython.translator.backendopt import graphanalyze


TRANSACTION_BREAK = set([
    'stm_commit_transaction',
    'stm_begin_inevitable_transaction',
    'stm_perform_transaction',
    'stm_partial_commit_and_resume_other_threads', # new priv_revision
    'jit_assembler_call',
    'jit_stm_transaction_break_point',
    ])


class TransactionBreakAnalyzer(graphanalyze.BoolGraphAnalyzer):

    def analyze_simple_operation(self, op, graphinfo):
        return op.opname in TRANSACTION_BREAK

    def analyze_external_call(self, op, seen=None):
        # if 'funcobj' releases the GIL, then the GIL-releasing
        # functions themselves will call stm_commit_transaction
        # and stm_begin_inevitable_transaction.  This case is
        # covered above.
        return False
