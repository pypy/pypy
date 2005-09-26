



class SimpleTaskEngine:


    def __init__(self):

        self.tasks = tasks = {}

        for name in dir(self):
            if name.startswith('task_'):
                task_name = name[len('task_'):]
                task = getattr(self, name)
                assert callable(task)
                task_deps = getattr(task, 'task_deps', [])

                tasks[task_name] = task, task_deps


    def _plan(self, goal, skip=[]):

        constraints = []

        def subgoals(task_name):
            taskcallable, deps = self.tasks[task_name]
            for dep in deps:
                if dep.startswith('?'):
                    dep = dep[1:]
                    if dep in skip:
                        continue
                yield dep


        seen = {}
                        
        def consider(subgoal):
            if subgoal in seen:
                return
            else:
                seen[subgoal] = True
            constraints.append([subgoal])
            deps = subgoals(subgoal)
            for dep in deps:
                constraints.append([subgoal, dep])
                consider(dep)

        consider(goal)

        #sort

        plan = []

        while True:
            cands = dict.fromkeys([constr[0] for constr in constraints if constr])
            if not cands:
                break

            for cand in cands:
                for constr in constraints:
                    if cand in constr[1:]:
                        break
                else:
                    break
            else:
                raise RuntimeError, "circular dependecy"

            plan.append(cand)
            for constr in constraints:
                if constr and constr[0] == cand:
                    del constr[0]

        plan.reverse()

        return plan
            
            

def test_simple():

    class ABC(SimpleTaskEngine):

        def task_A(self):
            pass

        task_A.task_deps = ['B', '?C']

        def task_B(self):
            pass

        def task_C(self):
            pass

        task_C.task_deps = ['B']

    abc = ABC()

    assert abc._plan('B') == ['B']
    assert abc._plan('C') == ['B', 'C']
    assert abc._plan('A') == ['B', 'C', 'A']
    assert abc._plan('A', skip=['C']) == ['B', 'A']
   

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

        
        
