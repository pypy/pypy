#*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
#*-*
#*-*  This program creates :
#*-*    - a one dimensional histogram
#*-*    - a two dimensional histogram
#*-*    - a profile histogram
#*-*    - a memory-resident ntuple
#*-*
#*-*  These objects are filled with some random numbers and saved on a file.
#*-*
#*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*

_reflex = True     # to keep things equal, set to False for full macro

try:
    import cppyy, random

    if not hasattr(cppyy.gbl, 'gROOT'):
        cppyy.load_reflection_info('bench02Dict_reflex.so')
        _reflex = True

    TCanvas  = cppyy.gbl.TCanvas
    TFile    = cppyy.gbl.TFile
    TProfile = cppyy.gbl.TProfile
    TNtuple  = cppyy.gbl.TNtuple
    TH1F     = cppyy.gbl.TH1F
    TH2F     = cppyy.gbl.TH2F
    TRandom3 = cppyy.gbl.TRandom3

    gROOT      = cppyy.gbl.gROOT
    gBenchmark = cppyy.gbl.TBenchmark()
    gSystem    = cppyy.gbl.gSystem

except ImportError:
    from ROOT import TCanvas, TFile, TProfile, TNtuple, TH1F, TH2F, TRandom3
    from ROOT import gROOT, gBenchmark, gSystem
    import random

if _reflex:
    gROOT.SetBatch(True)

# Create a new ROOT binary machine independent file.
# Note that this file may contain any kind of ROOT objects, histograms,
# pictures, graphics objects, detector geometries, tracks, events, etc..
# This file is now becoming the current directory.

if not _reflex:
    hfile = gROOT.FindObject('hsimple.root')
    if hfile:
        hfile.Close()
    hfile = TFile('hsimple.root', 'RECREATE', 'Demo ROOT file with histograms' )

# Create some histograms, a profile histogram and an ntuple
hpx    = TH1F('hpx', 'This is the px distribution', 100, -4, 4)
hpx.SetFillColor(48)
hpxpy  = TH2F('hpxpy', 'py vs px', 40, -4, 4, 40, -4, 4)
hprof  = TProfile('hprof', 'Profile of pz versus px', 100, -4, 4, 0, 20)
if not _reflex:
    ntuple = TNtuple('ntuple', 'Demo ntuple', 'px:py:pz:random:i')

gBenchmark.Start('hsimple')

# Create a new canvas, and customize it.
c1 = TCanvas('c1', 'Dynamic Filling Example', 200, 10, 700, 500)
c1.SetFillColor(42)
c1.GetFrame().SetFillColor(21)
c1.GetFrame().SetBorderSize(6)
c1.GetFrame().SetBorderMode(-1)

# Fill histograms randomly.
random = TRandom3()
kUPDATE = 1000
for i in xrange(50000):
    # Generate random numbers
#    px, py = random.gauss(0, 1), random.gauss(0, 1)
    px, py = random.Gaus(0, 1), random.Gaus(0, 1)
    pz = px*px + py*py
#    rnd = random.random()
    rnd = random.Rndm(1)

    # Fill histograms
    hpx.Fill(px)
    hpxpy.Fill(px, py)
    hprof.Fill(px, pz)
    if not _reflex:
        ntuple.Fill(px, py, pz, rnd, i)

    # Update display every kUPDATE events
    if i and i%kUPDATE == 0:
        if i == kUPDATE:
            hpx.Draw()

        c1.Modified(True)
        c1.Update()

        if gSystem.ProcessEvents():          # allow user interrupt
            break

gBenchmark.Show( 'hsimple' )

# Save all objects in this file
hpx.SetFillColor(0)
if not _reflex:
    hfile.Write()
hpx.SetFillColor(48)
c1.Modified(True)
c1.Update()

# Note that the file is automatically closed when application terminates
# or when the file destructor is called.
