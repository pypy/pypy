SOURCE = lang/sum.tla.py lang/fact.tla.py lang/fib.tla.py lang/ack.tla.py \
	lang/tak.tla.py lang/gcd.tla.py lang/sum-tail.tla.py lang/fib-tail.tla.py

.PHONY: compile
compile: targettla-c targettla_bench-c

.PHONY: targettla-c
targettla-c: targettla.py tla.py
	rpython -Ojit --make-jobs=12 $<

%.tla: %.tla.py
	./tla_assembler.py $<

.PHONY: assemble
assemble: $(SOURCE)
	for prog in $(SOURCE); do ./tla_assembler.py $$prog; done
