:- module(unifiable, [unifiable/3, unifiable/4]).

unifiable(A, B, List) :-
	unifiable(A, B, [], List).

unifiable(A, B, Acc, List) :-
    var(A),
    unifiable_first_var(A, B, Acc, List).

unifiable(A, B, Acc, List) :-
    nonvar(A),
    unifiable_first_nonvar(A, B, Acc, List).

unifiable_first_var(A, B, Acc, Ret) :-
    var(B),
    unifiable_both_var(A, B, Acc, Ret).

unifiable_first_var(A, B, Acc, [A-B|Acc]) :-
	nonvar(B).

unifiable_first_nonvar(A, B, Acc, [B-A|Acc]) :-
	var(B).

unifiable_both_var(A, B, Acc, [A-B|Acc]) :-
    A \== B.

unifiable_both_var(A, B, Acc, Acc) :-
    A == B.

unifiable_first_nonvar(A, B, Acc, List) :-
	nonvar(A),
	nonvar(B),
	functor(A, Functor, Arity),
	functor(B, Functor, Arity),
	A =.. [_|ArgsA],
	B =.. [_|ArgsB],
	unifiable_list(ArgsA, ArgsB, Acc, List).

unifiable_list([], [], Acc, Acc).
unifiable_list([A|RestA], [B|RestB], Acc, List) :-
	unifiable(A, B, Acc, NewAcc),
	unifiable_list(RestA, RestB, NewAcc, List).
