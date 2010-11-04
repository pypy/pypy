" Language   : PyPy JIT traces
" Maintainer : Armin Rigo

if exists("b:current_syntax")
 finish
endif

syn case ignore

syn match pypyNumber      '\<[0-9.]\+\>'
syn match pypyConstPtr    '\<ptr\d\+\>'
syn region pypyDescr      start=/descr=</ end=/>/ contains=pypyDescrField
syn match pypyDescrField  '[.]\w\+ ' contained
syn match pypyOpNameStart '^' nextgroup=pypyOpName
syn match pypyOpNameEqual ' = ' nextgroup=pypyOpName
syn match pypyOpName      '\l\l\w\+' contained
syn match pypyFailArgs    '[[].*[]]'
syn match pypyLoopArgs    '^[[].*'
syn match pypyLoopStart   '^#.*'
syn match pypyDebugMergePoint  '^debug_merge_point(.\+)'

hi def link pypyLoopStart   Structure
"hi def link pypyLoopArgs    PreProc
hi def link pypyFailArgs    String
"hi def link pypyOpName      Statement
hi def link pypyDebugMergePoint  Comment
hi def link pypyConstPtr    Constant
hi def link pypyNumber      Number
hi def link pypyDescr       String
hi def link pypyDescrField  Label
