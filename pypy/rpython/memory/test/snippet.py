import os, py
from pypy.tool.udir import udir
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.lltypesystem.lloperation import llop

class SemiSpaceGCTests:
    large_tests_ok = False

    def run_ok(self, f):
        res = self.run(f)
        assert res == 'ok'

    def test_finalizer_order(self):
        import random
        from pypy.tool.algo import graphlib

        examples = []
        if self.large_tests_ok:
            letters = 'abcdefghijklmnopqrstuvwxyz'
            COUNT = 20
        else:
            letters = 'abcdefghijklm'
            COUNT = 2
        for i in range(COUNT):
            input = []
            edges = {}
            for c in letters:
                edges[c] = []
            # make up a random graph
            for c in letters:
                for j in range(random.randrange(0, 4)):
                    d = random.choice(letters)
                    edges[c].append(graphlib.Edge(c, d))
                    input.append((c, d))
            # find the expected order in which destructors should be called
            components = list(graphlib.strong_components(edges, edges))
            head = {}
            for component in components:
                c = component.keys()[0]
                for d in component:
                    assert d not in head
                    head[d] = c
            assert len(head) == len(letters)
            strict = []
            for c, d in input:
                if head[c] != head[d]:
                    strict.append((c, d))
            examples.append((input, components, strict))

        class State:
            pass
        state = State()
        class A:
            def __init__(self, key):
                self.key = key
                self.refs = []
            def __del__(self):
                assert state.age[self.key] == -1
                state.age[self.key] = state.time
                state.progress = True

        def build_example(input):
            state.time = 0
            state.age = {}
            vertices = {}
            for c in letters:
                vertices[c] = A(c)
                state.age[c] = -1
            for c, d in input:
                vertices[c].refs.append(vertices[d])

        def f():
            i = 0
            while i < len(examples):
                input, components, strict = examples[i]
                build_example(input)
                while state.time < len(letters):
                    state.progress = False
                    llop.gc__collect(lltype.Void)
                    if not state.progress:
                        break
                    state.time += 1
                # summarize the finalization order
                lst = []
                for c in letters:
                    lst.append('%s:%d' % (c, state.age[c]))
                summary = ', '.join(lst)

                # check that all instances have been finalized
                if -1 in state.age.values():
                    return error(i, summary, "not all instances finalized")
                # check that if a -> b and a and b are not in the same
                # strong component, then a is finalized strictly before b
                for c, d in strict:
                    if state.age[c] >= state.age[d]:
                        return error(i, summary,
                                     "%s should be finalized before %s"
                                     % (c, d))
                # check that two instances in the same strong component
                # are never finalized during the same collection
                for component in components:
                    seen = {}
                    for c in component:
                        age = state.age[c]
                        if age in seen:
                            d = seen[age]
                            return error(i, summary,
                                         "%s and %s should not be finalized"
                                         " at the same time" % (c, d))
                        seen[age] = c
                i += 1
            return "ok"

        def error(i, summary, msg):
            return '%d\n%s\n%s' % (i, summary, msg)

        res = self.run(f)
        if res != "ok":
            i, summary, msg = res.split('\n')
            i = int(i)
            import pprint
            print 'Example:'
            pprint.pprint(examples[i])
            print 'Finalization ages:'
            print summary
            print msg
            py.test.fail(msg)
