:- module(list, [append/3, is_list/1]).

append([], L, L).
append([H|T], L, [H|R]) :- append(T, L, R).

is_list([]).
is_list([_|T]) :- is_list(T).
