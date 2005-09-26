

class SimpleTaskEngine:

    def __init__(self):
        self._plan_cache = {}

        self.tasks = tasks = {}

        for name in dir(self):
            if name.startswith('task_'):
                task_name = name[len('task_'):]
                task = getattr(self, name)
                assert callable(task)
                task_deps = getattr(task, 'task_deps', [])

                tasks[task_name] = task, task_deps

    def _plan(self, goals, skip=[]):
        skip = [toskip for toskip in skip if toskip not in goals]

        key = (tuple(goals), tuple(skip))
        try:
            return self._plan_cache[key]
        except KeyError:
            pass
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

        for goal in goals:
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

        self._plan_cache[key] = plan

        return plan

    def _execute(self, goals, *args, **kwds):
        task_skip = kwds.get('task_skip', [])
        for goal in self._plan(goals, skip=task_skip):
            taskcallable, _ = self.tasks[goal]
            self._event('pre', goal, taskcallable)
            try:
                self._do(goal, taskcallable, *args, **kwds)
            except (SystemExit, KeyboardInterrupt):
                raise
            except:
                self._error(goal)
                raise
            self._event('post', goal, taskcallable)
        
    def _do(self, goal, func, *args, **kwds):
        func()

    def _event(self, kind, goal, func):
        pass
    
    def _error(self, goal):
        pass


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

        
        
