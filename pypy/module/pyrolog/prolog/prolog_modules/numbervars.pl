:- module(numbervars, [numbervars/3]).

numbervars(Term, Start, R) :-
	term_variables(Term, List),
	numvars(List, Start, R).

numvars([], N, N).
numvars([H|T], N, R) :-
	H = '$VAR'(N),
	N1 is N + 1,
	numvars(T, N1, R).
