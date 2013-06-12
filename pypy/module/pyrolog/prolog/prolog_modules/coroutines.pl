:- module(coroutines, [freeze/2, when/2, frozen/2, block/1, dif/2]).
:- meta_predicate freeze('?', :), when('?', :), block(:).

% *****************************************************
% *                  F R E E Z E                      *
% *****************************************************

freeze(X, Goal) :-
    nonvar(X), !,
    call(Goal).

freeze(X, Goal) :-
    var(X), !,
    put_freeze_attribute(X, Goal).

put_freeze_attribute(X, Freeze_Goal) :-
    (get_attr(X, freeze, Current_Goals)
    ->
        put_attr(X, freeze, (Current_Goals, Freeze_Goal))
    ;
        put_attr(X, freeze, Freeze_Goal)
    ).

% * FROZEN *

frozen(X, true) :-
    nonvar(X).

frozen(X, true) :-
    var(X),
    \+ get_attr(X, freeze, _).

frozen(X, R) :-
    var(X),
    get_attr(X, freeze, R).

% *****************************************************
% *                    W H E N                        *
% *****************************************************

put_when_attributes([], _).
put_when_attributes([X|Rest], When_Goal) :-
    (get_attr(X, when, Current_Goals)
    ->
        put_attr(X, when, (Current_Goals, When_Goal))
    ;
        put_attr(X, when, When_Goal)
    ),
    coroutines:put_when_attributes(Rest, When_Goal).

when_impl(nonvar(X), Goal) :- !,
    (var(X)
    ->
        coroutines:put_when_attributes([X], Goal)
    ;
        Goal
    ).

when_impl(ground(X), Goal) :- !,
    term_variables(X, Varlist),
    (Varlist = []
    ->
        Goal
    ;
        [Var|_] = Varlist,
        coroutines:put_when_attributes([Var], coroutines:when_impl(ground(Varlist), Goal))
    ).

when_impl((A, B), Goal) :- !,
    coroutines:when_impl(A, coroutines:when_impl(B, Goal)).

call_when_disjoint(Var, Goal) :-
    (var(Var) ->
        Var = a,
        Goal
    ;
        true).

when_impl((A; B), Goal) :- !,
    coroutines:when_impl(A, coroutines:call_when_disjoint(Z, Goal)),
    coroutines:when_impl(B, coroutines:call_when_disjoint(Z, Goal)).

when_impl(?=(A, B), Goal) :- !,
    coroutines:when_decidable(A, B, Goal).

when_impl(X, _) :-
    throw(error(domain_error(when_condition, X))).

when_decidable(A, B, Goal) :-
    (unifiable(A, B, Unifiers)
    ->
        (Unifiers == []
        ->
            Goal
        ;
            when_decidable_list(Unifiers, coroutines:call_when_disjoint(_Guard, coroutines:when_decidable_helper(Unifiers, Goal)))
        )
    ;
        Goal
    ).

when_decidable_helper(Unifiers, Goal) :-
    (unifiable_list(Unifiers, NewUnifiers)
    ->
        (NewUnifiers == []
        ->
            Goal
        ;
            when_decidable_list(NewUnifiers, coroutines:call_when_disjoint(_Guard, coroutines:when_decidable_helper(NewUnifiers, Goal)))
        )
    ;
        Goal
    ).

when_decidable_list([], _).
when_decidable_list([A-B|Rest], Goal) :-
    (var(B)
    ->
        (var(A)
        ->
            put_when_attributes([A, B], Goal)
        ;
            put_when_attributes([B], Goal)
        )
    ;
        (var(A)
        ->
            put_when_attributes([A], Goal)
        ;
            true
        )
    ),
    when_decidable_list(Rest, Goal).

unifiable_list(Unifiers, NewUnifiers) :-
    unifiable_list(Unifiers, [], NewUnifiers).
unifiable_list([], A, A).
unifiable_list([X-Y|Rest], Acc, Ret) :-
    unifiable(X, Y, Acc, Temp),
    unifiable_list(Rest, Temp, Ret).

when(Cond, Goal) :-
    var(Cond), !,
    throw(error(instantiation_error)).

when(Cond, Goal) :-
    coroutines:when_impl(Cond, Goal).

% *****************************************************
% *					     D I F                        *
% *****************************************************

dif(X, Y) :-
    coroutines:when_decidable(X, Y, X \== Y).

% *****************************************************
% *					   B L O C K                      *
% *****************************************************

block(Module:Term) :-
    coroutines:process_block_list(Term, Module).

process_block_list(Term, Module) :-
    Term \= (A, B),
    coroutines:process_block(Term, Module).
process_block_list((Head, Rest), Module) :-
    coroutines:process_block(Head, Module),
    coroutines:process_block_list(Rest, Module).

process_block(Block, Module) :-
    Block =.. [Functor|Args],
    coroutines:make_constraints(Args, Vars, Var_Constraints, When_Constraints),
    Header =.. [Functor|Vars],
    Rule = (Header :- (Var_Constraints, !, when(When_Constraints, Header))),
    assert(Module:Rule).

make_constraints([], [], true, nonvar(_)).
make_constraints([Head|Rest], [X|Vars], (var(X), Var_Constraints), ';'(nonvar(X), When_Constraints)) :-
    nonvar(Head),
    Head = '-', !,
    coroutines:make_constraints(Rest, Vars, Var_Constraints, When_Constraints).
make_constraints([X|Rest], [Var|Vars], Var_Constraints, When_Constraints) :-
    nonvar(X),
    \+ X = '-', !,
    coroutines:make_constraints(Rest, Vars, Var_Constraints, When_Constraints).
make_constraints([X|_], _, _, _) :-
    var(X), !,
    throw(error(domain_error(nonvar, X))).
