SOURCE = loop.tla.py loopabit.tla.py call.tla.py call_jitfun.tla.py callabit.tla.py callabit_jitfun.tla.py

targettla-c: targettla.py tla.py
	rpython -Ojit --make-jobs=7 $<

targettla-bench-c: targettla_bench.py tla.py
	rpython -Ojit --make-jobs=7 $<

assemble: $(SOURCE)
	for src in $(SOURCE); do ./tla_assembler.py $$src; done
