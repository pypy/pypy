# it had to happen: a customized version of pdb for pypy; Py Py
# DeBugger, if you please.

# i only plan to support post morterm debugging!  my head hurts if my
# thoughts even go near any alternative!

import pdb, sys

class PPdb(pdb.Pdb):
    def do_bta(self, line):
        self.operr.print_application_traceback(self.space, sys.stdout)

def post_mortem(space, t, operr):
    # need app-level tb too?
    p = PPdb()
    p.reset()
    p.space = space
    p.operr = operr
    while t.tb_next is not None:
        t = t.tb_next
    p.interaction(t.tb_frame, t)

