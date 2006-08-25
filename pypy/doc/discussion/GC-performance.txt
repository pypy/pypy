StartHeapsize# is the framework GC as of revision 31586 with initial
bytes_malloced_threshold of 2-512 MB

NewHeuristics is the framework GC with a new heuristics for adjusting
the bytes_malloced_threshold

::

 Pystone
 StartHeapsize2:
 This machine benchmarks at 5426.92 pystones/second
 This machine benchmarks at 5193.91 pystones/second
 This machine benchmarks at 5403.46 pystones/second
 StartHeapsize8:
 This machine benchmarks at 6075.33 pystones/second
 This machine benchmarks at 6007.21 pystones/second
 This machine benchmarks at 6122.45 pystones/second
 StartHeapsize32:
 This machine benchmarks at 6643.05 pystones/second
 This machine benchmarks at 6590.51 pystones/second
 This machine benchmarks at 6593.41 pystones/second
 StartHeapsize128:
 This machine benchmarks at 7065.47 pystones/second
 This machine benchmarks at 7102.27 pystones/second
 This machine benchmarks at 7082.15 pystones/second
 StartHeapsize512:
 This machine benchmarks at 7208.07 pystones/second
 This machine benchmarks at 7197.7 pystones/second
 This machine benchmarks at 7246.38 pystones/second
 NewHeuristics:
 This machine benchmarks at 6821.28 pystones/second
 This machine benchmarks at 6858.71 pystones/second
 This machine benchmarks at 6902.9 pystones/second


 Richards
 StartHeapSize2:
 Average time per iteration: 5456.21 ms
 Average time per iteration: 5529.31 ms
 Average time per iteration: 5398.82 ms
 StartHeapsize8:
 Average time per iteration: 4775.43 ms
 Average time per iteration: 4753.25 ms
 Average time per iteration: 4781.37 ms
 StartHeapsize32:
 Average time per iteration: 4554.84 ms
 Average time per iteration: 4501.86 ms
 Average time per iteration: 4531.59 ms
 StartHeapsize128:
 Average time per iteration: 4329.42 ms
 Average time per iteration: 4360.87 ms
 Average time per iteration: 4392.81 ms
 StartHeapsize512:
 Average time per iteration: 4371.72 ms
 Average time per iteration: 4399.70 ms
 Average time per iteration: 4354.66 ms
 NewHeuristics:
 Average time per iteration: 4763.56 ms
 Average time per iteration: 4803.49 ms
 Average time per iteration: 4840.68 ms


 translate rpystone
   time pypy-c translate --text --batch --backendopt --no-compile targetrpystonedalone.py
 StartHeapSize2:
 real    1m38.459s
 user    1m35.582s
 sys     0m0.440s
 StartHeapsize8:
 real    1m35.398s
 user    1m33.878s
 sys     0m0.376s
 StartHeapsize32:
 real    1m5.475s
 user    1m5.108s
 sys     0m0.180s
 StartHeapsize128:
 real    0m52.941s
 user    0m52.395s
 sys     0m0.328s
 StartHeapsize512:
 real    1m3.727s
 user    0m50.031s
 sys     0m1.240s
 NewHeuristics:
 real    0m53.449s
 user    0m52.771s
 sys     0m0.356s


 docutils
   time pypy-c rst2html doc/coding-guide.txt
 StartHeapSize2:
 real    0m36.125s
 user    0m35.562s
 sys     0m0.088s
 StartHeapsize8:
 real    0m32.678s
 user    0m31.106s
 sys     0m0.084s
 StartHeapsize32:
 real    0m22.041s
 user    0m21.085s
 sys     0m0.132s
 StartHeapsize128:
 real    0m19.350s
 user    0m18.653s
 sys     0m0.324s
 StartHeapsize512:
 real    0m19.116s
 user    0m17.517s
 sys     0m0.620s
 NewHeuristics:
 real    0m20.990s
 user    0m20.109s
 sys     0m0.196s


