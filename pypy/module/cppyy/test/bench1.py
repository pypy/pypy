import commands, os, sys, time

NNN = 10000000


def run_bench(bench):
    global t_loop_offset

    t1 = time.time()
    bench()
    t2 = time.time()

    t_bench = (t2-t1)-t_loop_offset
    return bench.scale*t_bench

def print_bench(name, t_bench):
    global t_cppref
    print ':::: %s cost: %#6.3fs (%#4.1fx)' % (name, t_bench, float(t_bench)/t_cppref)

def python_loop_offset():
    for i in range(NNN):
        i
    return i

class PyCintexBench1(object):
    scale = 10
    def __init__(self):
        import PyCintex
        self.lib = PyCintex.gbl.gSystem.Load("./example01Dict.so")

        self.cls   = PyCintex.gbl.example01
        self.inst  = self.cls(0)

    def __call__(self):
        # note that PyCintex calls don't actually scale linearly, but worse
        # than linear (leak or wrong filling of a cache??)
        instance = self.inst
        niter = NNN/self.scale
        for i in range(niter):
            instance.addDataToInt(i)
        return i

class PyROOTBench1(PyCintexBench1):
    def __init__(self):
        import ROOT
        self.lib = ROOT.gSystem.Load("./example01Dict_cint.so")

        self.cls   = ROOT.example01
        self.inst  = self.cls(0)

class CppyyInterpBench1(object):
    scale = 1
    def __init__(self):
        import cppyy
        self.lib = cppyy.load_lib("./example01Dict.so")

        self.cls  = cppyy._type_byname("example01")
        self.inst = self.cls.get_overload(self.cls.type_name).call(None, cppyy.CPPInstance, 0)

    def __call__(self):
        addDataToInt = self.cls.get_overload("addDataToInt")
        instance = self.inst
        for i in range(NNN):
            addDataToInt.call(instance, None, i)
        return i

class CppyyPythonBench1(object):
    scale = 1
    def __init__(self):
        import cppyy
        self.lib = cppyy.load_lib("./example01Dict.so")

        self.cls = cppyy.gbl.example01
        self.inst = self.cls(0)

    def __call__(self):
        instance = self.inst
        for i in range(NNN):
            instance.addDataToInt(i)
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

    # special case for PyCintex (run under python, not pypy-c)
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

    # warm-up
    print "warming up ... "
    interp_bench1 = CppyyInterpBench1()
    python_bench1 = CppyyPythonBench1()
    interp_bench1(); python_bench1()

    # to allow some consistency checking
    print "C++ reference uses %.3fs" % t_cppref

    # test runs ...
    print_bench("cppyy interp", run_bench(interp_bench1))
    print_bench("cppyy python", run_bench(python_bench1))
    stat, t_cintex = commands.getstatusoutput("python bench1.py --pycintex")
    print_bench("pycintex    ", float(t_cintex))
    #stat, t_pyroot = commands.getstatusoutput("python bench1.py --pyroot")
    #print_bench("pyroot      ", float(t_pyroot))
