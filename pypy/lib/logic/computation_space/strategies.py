import computationspace as csp

class StrategyDistributionMismatch(Exception):
    pass

def dfs_one(problem):
    """depth-first single-solution search
       assumes the space default distributor is
       dichotomic"""

    def do_dfs(space):
        print "do_dfs"
        status = space.ask()
        if status == csp.Failed:
            return None
        elif status == csp.Succeeded:
            return space
        elif status == csp.Alternatives(2):
            new_space = space.clone()
            space.commit(1)
            outcome = do_dfs(space)
            if outcome is None:
                new_space.commit(2)
                return do_dfs(new_space)
            else:
                return outcome
        else:
            raise StrategyDistributionMismatch()
                                               
    space = csp.ComputationSpace(problem)
    solved_space = do_dfs(space)
    if solved_space == None: return None
    return solved_space.merge()



#-- solve_all

def solve_all(problem):

    solutions = []
    sp_stack = []

    sp_stack.append(csp.ComputationSpace(problem))

    while len(sp_stack):
        space = sp_stack.pop()
        print ' '*len(sp_stack), "ask ..."
        status = space.ask()
        if status == csp.Succeeded:
            print ' '*len(sp_stack), "solution !"
            solutions.append(space)
        elif status == csp.Alternatives(2):
            print ' '*len(sp_stack), "branches ..."
            sp1 = space.clone()
            sp1.commit(1)
            sp_stack.append(sp1)
            sp2 = space.clone()
            sp2.commit(2)
            sp_stack.append(sp2)

    return [sp.merge() for sp in solutions]
    
## declare

## % This version of SolveAll will do a depth-first or breadth-first 
## % traversal of the search space depending on the WhichFirst parameter.
## fun {SolveAll WhichFirst Script} 
##    {TouchAll {Solve WhichFirst Script}} 
## end

## fun {TouchAll L}
##    case L of
##       nil then skip
##    [] _ | Rest then {TouchAll Rest _}
##    end
##    L
## end

## % Returns a lazy list of solutions for Script.
## % The list is ordered depth-first or breadth-first
## % depending on the WhichFirst parameter.
## % The allowable values are depth and breadth.
## fun {Solve WhichFirst Script}

## % All the subsidiary function are declared within Solve so
## % that we won't have to pass WhichFirst around.
## % The body of Solve is at the bottom.

##    % Each of the elements in Ss is either a Space or a 
##    % commitTo(<Space> <Int>) record. A commitTo(<Space> <Int>) 
##    % record identifies a Space that is ready to commit to
##    % the Ith choice at a choice point.
##    % Returns all solutions using either depth-first or
##    % breadth-first depending on the value of WhichFirst.
##    fun lazy {SolveSpaces Ss}
##       case Ss of
##          nil then nil
##       [] S | SRest then
##          % S is either a Space or a commitTo(<Space> <Int>) record.
##          case S of
## 	     commitTo(S I) then
## 	     Clone = {Space.clone S} 
##          in
## 	     % Start the Ith branch in the clone of S.
## 	     {Space.commit Clone I}
## 	     {SolveSpaces Clone|SRest}
##          else % S is a Space.
##              {SolveSpace {Space.ask S} S SRest}
##          end
##       end
##    end

##    % Deal with Space S, which is in state SpaceState
##    fun {SolveSpace SpaceState S SRest}
##       case SpaceState of
##          failed then {SolveSpaces SRest}  
##       [] succeeded then {Space.merge S}|{SolveSpaces SRest}  
##       [] alternatives(N) then
##          {SolveSpaces {NewSpaceList {Choices S N} SRest}}
##       end
##    end

##    % The choices are commitTo(<Space> <Int>) records. They
##    % keep track of the branch to which to commit.
##    fun {Choices S N}
##       {List.mapInd
##        {List.make N} % Generates N elements for Map to use.
##        % Keep track of which branch to commit to.
##        fun {$ I _} commitTo(S I) end}
##    end

##    % Put the Choices at the front or back of the existing list
##    % of pending Spaces depending on WhichFirst.  For efficiency 
##    % the lists could be replaced with difference lists.
##    fun {NewSpaceList Choices Ss}
##       % This is the only place where WhichFirst matters.
##       % In depth-first search, the list of pending spaces is a stack.
##       if WhichFirst == depth then {Append Choices Ss}
##       % In breadth-first search, the list of pending spaces is a queue.
##       elseif WhichFirst == breadth then {Append Ss Choices}
##       else {Raise traversalSpecificationError(WhichFirst)} nil
##       end
##    end

## in
## % The body of Solve
##    {SolveSpaces [{Space.new Script}]} 
## end

## % ==============================================================
## % Example to illustrate depth-first vs. breadth-first
## fun {ABC} choice a [] b [] c end end

## % The "problem" looks at all lists of length =< 3.
## % The "Show" documents the order in which the lists
## % are generated.
## fun {Problem List}
##    if {Length List} > 3 then fail end
##    {Show List}
##    {Problem {Append List [{ABC}]}}
## end
