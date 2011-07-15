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

try:
   import cppyy, random
   cppyy.load_lib('bench02Dict_reflex.so')

   TCanvas  = cppyy.gbl.TCanvas
   TFile    = cppyy.gbl.TFile
   TProfile = cppyy.gbl.TProfile
   TNtuple  = cppyy.gbl.TNtuple
   TH1F     = cppyy.gbl.TH1F
   TH2F     = cppyy.gbl.TH2F
   CH       = cppyy.gbl.CloserHack()
   CH.report()
except ImportError:
   from ROOT import TCanvas, TFile, TProfile, TNtuple, TH1F, TH2F
   import random

#gROOT      = cppyy.gbl.gROOT
#gBenchmark = cppyy.gbl.gBenchmark
#gRandom    = cppyy.gbl.gRandom
#gSystem    = cppyy.gbl.gSystem

#gROOT.Reset()

# Create a new canvas, and customize it.
c1 = TCanvas( 'c1', 'Dynamic Filling Example', 200, 10, 700, 500 )
#c1.SetFillColor( 42 )
#c1.GetFrame().SetFillColor( 21 )
#c1.GetFrame().SetBorderSize( 6 )
#c1.GetFrame().SetBorderMode( -1 )

# Create a new ROOT binary machine independent file.
# Note that this file may contain any kind of ROOT objects, histograms,
# pictures, graphics objects, detector geometries, tracks, events, etc..
# This file is now becoming the current directory.

#hfile = gROOT.FindObject( 'hsimple.root' )
#if hfile:
#   hfile.Close()
hfile = TFile( 'hsimple.root', 'RECREATE', 'Demo ROOT file with histograms' )

# Create some histograms, a profile histogram and an ntuple
hpx    = TH1F( 'hpx', 'This is the px distribution', 100, -4, 4 )
#hpxpy  = TH2F( 'hpxpy', 'py vs px', 40, -4, 4, 40, -4, 4 )
#hprof  = TProfile( 'hprof', 'Profile of pz versus px', 100, -4, 4, 0, 20 )
#ntuple = TNtuple( 'ntuple', 'Demo ntuple', 'px:py:pz:random:i' )

# Set canvas/frame attributes.
#hpx.SetFillColor( 48 )

#gBenchmark.Start( 'hsimple' )

# Initialize random number generator.
#gRandom.SetSeed()
#rannor, rndm = gRandom.Rannor, gRandom.Rndm

# Fill histograms randomly.
#px, py = Double(), Double()
kUPDATE = 1000
for i in xrange( 2500000 ):
 # Generate random values.
   px, py = random.gauss(0, 1), random.gauss(0, 1)
#   pt = (px*px + py*py)**0.5
   pt = (px*px + py*py)
#   random = rndm(1)

 # Fill histograms.
   hpx.Fill( pt )
#   hpxpyFill( px, py )
#   hprofFill( px, pz )
#   ntupleFill( px, py, pz, random, i )

 # Update display every kUPDATE events.
   if i and i%kUPDATE == 0:
      if i == kUPDATE:
         hpx.Draw()

#      c1.Modified()
#      c1.Update()

#      if gSystem.ProcessEvents():            # allow user interrupt
#         break

#gBenchmark.Show( 'hsimple' )

# Save all objects in this file.
#hpx.SetFillColor( 0 )
#hfile.Write()
hfile.Close()
#hpx.SetFillColor( 48 )
#c1.Modified()
c1.Update()
c1.Draw()
#import gc
#gc.collect()
  
# Note that the file is automatically closed when application terminates
# or when the file destructor is called.
