SOURCE = loop.tla.py loopabit.tla.py call.tla.py call_jitfun.tla.py callabit.tla.py callabit_baseline_tracing.tla.py callabit_baseline_only.tla.py

.PHONY: compile
compile: targettla-c targettla_bench-c

.PHONY: targettla-c
targettla-c: targettla.py tla.py
	rpython -Ojit --make-jobs=12 $<

.PHONY: targettla_bench-c
targettla_bench-c: targettla_bench.py tla.py
	rpython -Ojit --make-jobs=12 $<

%.tla: %.tla.py
	./tla_assembler.py $<

.PHONY: assemble
assemble: $(SOURCE)
	for prog in $(SOURCE); do ./tla_assembler.py $$prog; done
