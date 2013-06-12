call_when_disjoint(Var, Goal) :-
	var(Var),
	Var = a,
	Goal.

call_when_disjoint(Var, _) :-
	nonvar(Var).

% calling bug causes the interpreter to crash
bug :-
	call(call_when_disjoint(_Z, nl)), fail.
