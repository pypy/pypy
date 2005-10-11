from pypy.translator.goal import richards
from pypy.translator.tool.taskengine import SimpleTaskEngine

entry_point = richards.entry_point


# _____ Define and setup target ___

def target(*args):
    return entry_point, [int]

def get_llinterp_args():
    return [1]

# _____ Run translated _____
def run(c_entry_point):
    print "Translated:"
    richards.main(c_entry_point, iterations=500)
    print "CPython:"
    richards.main(iterations=5)

    
class Tasks(SimpleTaskEngine):

    def task_annotate(self):
        pass
    task_annotate.task_deps = []

    def task


""" sketch of tasks for translation:

annotate:  # includes annotation and annotatation simplifications

rtype: annotate

backendoptimisations: rtype # make little sense otherwise

source_llvm: backendoptimisations, rtype, annotate

source_c: ?backendoptimisations, ?rtype, ?annotate

compile_c : source_c

compile_llvm: source_llvm

run_c: compile_c

run_llvm: compile_llvm

"""
 
