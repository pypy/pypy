import commands, os, sys, time

NNN = 10000000


def run_bench(bench):
    global t_loop_offset, NNN

    t1 = time.time()
    bench(NNN)
    t2 = time.time()

    t_bench = (t2-t1)
    return bench.scale*t_bench-t_loop_offset

def print_bench(name, t_bench):
    global t_cppref
    print ':::: %s cost: %#6.3fs (%#4.1fx)' % (name, t_bench, float(t_bench)/t_cppref)

def python_loop_offset():
    for i in range(NNN):
        i
    return i

class PyCintexBench1(object):
    scale = 5
    def __init__(self):
        import PyCintex
        self.lib = PyCintex.gbl.gSystem.Load("./example01Dict.so")

        self.cls   = PyCintex.gbl.example01
        self.inst  = self.cls(0)

    def __call__(self, repeat):
        # note that PyCintex calls don't actually scale linearly, but worse
        # than linear (leak or wrong filling of a cache??)
        instance = self.inst
        niter = repeat/self.scale
        for i in range(niter):
            instance.addDataToInt(i)
        return i

class PyROOTBench1(PyCintexBench1):
    def __init__(self):
        import ROOT
        self.lib = ROOT.gSystem.Load("./example01Dict.so")

        self.cls   = ROOT.example01
        self.inst  = self.cls(0)

class CppyyInterpBench1(object):
    title = "cppyy interp"
    scale = 1
    def __init__(self):
        import cppyy
        self.lib = cppyy.load_reflection_info("./example01Dict.so")

        self.cls  = cppyy._scope_byname("example01")
        self.inst = self.cls.get_overload(self.cls.type_name).call(None, 0)

    def __call__(self, repeat):
        addDataToInt = self.cls.get_overload("addDataToInt")
        instance = self.inst
        for i in range(repeat):
            addDataToInt.call(instance, i)
        return i

class CppyyInterpBench2(CppyyInterpBench1):
    title = "... overload"
    def __call__(self, repeat):
        addDataToInt = self.cls.get_overload("overloadedAddDataToInt")
        instance = self.inst
        for i in range(repeat):
            addDataToInt.call(instance, i)
        return i

class CppyyInterpBench3(CppyyInterpBench1):
    title = "... constref"
    def __call__(self, repeat):
        addDataToInt = self.cls.get_overload("addDataToIntConstRef")
        instance = self.inst
        for i in range(repeat):
            addDataToInt.call(instance, i)
        return i

class CppyyPythonBench1(object):
    title = "cppyy python"
    scale = 1
    def __init__(self):
        import cppyy
        self.lib = cppyy.load_reflection_info("./example01Dict.so")

        self.cls = cppyy.gbl.example01
        self.inst = self.cls(0)

    def __call__(self, repeat):
        instance = self.inst
        for i in range(repeat):
            instance.addDataToInt(i)
        return i

class CppyyPythonBench2(CppyyPythonBench1):
    title = "... objbyval"
    def __call__(self, repeat):
        import cppyy
        pl = cppyy.gbl.payload(3.14)

        instance = self.inst
        for i in range(repeat):
            instance.copyCyclePayload(pl)
        return i

class CppyyPythonBench3(CppyyPythonBench1):
    title = "... objbyptr"
    def __call__(self, repeat):
        import cppyy
        pl = cppyy.gbl.payload(3.14)

        instance = self.inst
        for i in range(repeat):
            instance.cyclePayload(pl)
        return i


if __name__ == '__main__':
    python_loop_offset();

    # time python loop offset
    t1 = time.time()
    python_loop_offset()
    t2 = time.time()
    t_loop_offset = t2-t1

    # special case for PyCintex (run under python, not pypy-c)
    if '--pycintex' in sys.argv:
        cintex_bench1 = PyCintexBench1()
        print run_bench(cintex_bench1)
        sys.exit(0)

    # special case for PyROOT (run under python, not pypy-c)
    if '--pyroot' in sys.argv:
        pyroot_bench1 = PyROOTBench1()
        print run_bench(pyroot_bench1)
        sys.exit(0)

    # get C++ reference point
    if not os.path.exists("bench1.exe") or\
            os.stat("bench1.exe").st_mtime < os.stat("bench1.cxx").st_mtime:
        print "rebuilding bench1.exe ... "
        os.system( "g++ -O2 bench1.cxx example01.cxx -o bench1.exe" )
    stat, cppref = commands.getstatusoutput("./bench1.exe")
    t_cppref = float(cppref)

    # created object
    benches = [
        CppyyInterpBench1(), CppyyInterpBench2(), CppyyInterpBench3(),
        CppyyPythonBench1(), CppyyPythonBench2(), CppyyPythonBench3() ]

    # warm-up
    print "warming up ... "
    for bench in benches:
        bench(2000)

    # to allow some consistency checking
    print "C++ reference uses %.3fs" % t_cppref

    # test runs ...
    for bench in benches:
        print_bench(bench.title, run_bench(bench))
    stat, t_cintex = commands.getstatusoutput("python bench1.py --pycintex")
    print_bench("pycintex    ", float(t_cintex))
    #stat, t_pyroot = commands.getstatusoutput("python bench1.py --pyroot")
    #print_bench("pyroot      ", float(t_pyroot))
