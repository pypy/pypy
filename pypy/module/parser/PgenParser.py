#! /usr/bin/env python
# ______________________________________________________________________
"""Module PgenParser

Implements a recursive descent parser for the Python pgen parser generator
input language.

$Id: PgenParser.py,v 1.2 2003/10/02 17:37:17 jriehl Exp $
"""
# ______________________________________________________________________

import token

# ______________________________________________________________________
# XXX I am unsure I want these here.  Conversely, pgen really doesn't change
# at all, so what is the harm in duplicating these?

MSTART = 256
RULE = 257
RHS = 258
ALT = 259
ITEM = 260
ATOM = 261

# ______________________________________________________________________

__DEBUG__ = 0

if __DEBUG__:
    import pprint

# ______________________________________________________________________

def expect (val, tok):
    type, name, lineno = tok
    if val != type:
        if name == None:
            gotStr = token.tok_name[type]
        else:
            gotStr = `name`
        errStr = ("Line %d, expecting %s, got %s." %
                  (lineno, token.tok_name[val], gotStr))
        raise SyntaxError, errStr

# ______________________________________________________________________

def handleStart (tokenizer):
    """handleStart()
    MSTART := ( RULE | NEWLINE )* ENDMARKER
    """
    children = []
    crntToken = tokenizer()
    while token.ENDMARKER != crntToken[0]:
        if token.NEWLINE == crntToken[0]:
            children.append((crntToken, []))
            crntToken = None
        else:
            ruleResult, crntToken = handleRule(tokenizer, crntToken)
            children.append(ruleResult)
        if None == crntToken:
            crntToken = tokenizer()
    children.append((crntToken, []))
    return (MSTART, children)

# ______________________________________________________________________

def handleRule (tokenizer, crntToken = None):
    """handleRule()
    RULE := NAME COLON RHS NEWLINE
    """
    children = []
    if None == crntToken:
        crntToken = tokenzier()
    expect(token.NAME, crntToken)
    children.append((crntToken, []))
    crntToken = tokenizer()
    expect(token.COLON, crntToken)
    children.append((crntToken, []))
    rhsResult, crntToken = handleRhs(tokenizer)
    children.append(rhsResult)
    if None == crntToken:
        crntToken = tokenizer()
    expect(token.NEWLINE, crntToken)
    children.append((crntToken, []))
    result = (RULE, children)
    if __DEBUG__:
        pprint.pprint(result)
    return result, None

# ______________________________________________________________________

def handleRhs (tokenizer, crntToken = None):
    """handleRhs()
    RHS := ALT ( VBAR ALT )*
    """
    children = []
    altResult, crntToken = handleAlt(tokenizer, crntToken)
    children.append(altResult)
    if None == crntToken:
        crntToken = tokenizer()
    while crntToken[0] == token.VBAR:
        children.append((crntToken, []))
        altResult, crntToken = handleAlt(tokenizer)
        children.append(altResult)
        if None == crntToken:
            crntToken = tokenizer()
    result = (RHS, children)
    if __DEBUG__:
        pprint.pprint(result)
    return result, crntToken

# ______________________________________________________________________

def handleAlt (tokenizer, crntToken = None):
    """handleAlt()
    ALT := ITEM+
    """
    children = []
    itemResult, crntToken = handleItem(tokenizer, crntToken)
    children.append(itemResult)
    if None == crntToken:
        crntToken = tokenizer()
    while crntToken[0] in (token.LSQB, token.LPAR, token.NAME, token.STRING):
        itemResult, crntToken = handleItem(tokenizer, crntToken)
        children.append(itemResult)
        if None == crntToken:
            crntToken = tokenizer()
    return (ALT, children), crntToken

# ______________________________________________________________________

def handleItem (tokenizer, crntToken = None):
    """handleItem()
    ITEM := LSQB RHS RSQB
         | ATOM ( STAR | PLUS )?
    """
    children = []
    if None == crntToken:
        crntToken = tokenizer()
    if crntToken[0] == token.LSQB:
        children.append((crntToken, []))
        rhsResult, crntToken = handleRhs(tokenizer)
        children.append(rhsResult)
        if None == crntToken:
            crntToken = tokenizer()
        expect(token.RSQB, crntToken)
        children.append((crntToken, []))
        crntToken = None
    else:
        atomResult, crntToken = handleAtom(tokenizer,crntToken)
        children.append(atomResult)
        if None == crntToken:
            crntToken = tokenizer()
        if crntToken[0] in (token.STAR, token.PLUS):
            children.append((crntToken, []))
            crntToken = None
    return (ITEM, children), crntToken

# ______________________________________________________________________

def handleAtom (tokenizer, crntToken = None):
    """handleAtom()
    ATOM := LPAR RHS RPAR
          | NAME
          | STRING
    """
    children = []
    if None == crntToken:
        crntToken = tokenizer()
    tokType = crntToken[0]
    if tokType == token.LPAR:
        children.append((crntToken, []))
        rhsResult, crntToken = handleRhs(tokenizer)
        children.append(rhsResult)
        if None == crntToken:
            crntToken = tokenizer()
        expect(token.RPAR, crntToken)
        children.append((crntToken, []))
        #crntToken = None
    elif tokType == token.STRING:
        children.append((crntToken, []))
        #crntToken = None
    else:
        expect(token.NAME, crntToken)
        children.append((crntToken, []))
        # crntToken = None
    return (ATOM, children), None

# ______________________________________________________________________

def parseString (inString, tokenizer = None):
    if tokenizer == None:
        import StdTokenizer
        tokenizer = StdTokenizer.StdTokenizer()
        tokenizer.tokenizeString(inString)
    return handleStart(tokenizer)

# ______________________________________________________________________

def parseFile (filename, tokenizer = None):
    if tokenizer == None:
        import StdTokenizer
        tokenizer = StdTokenizer.StdTokenizer()
        tokenizer.tokenizeFile(filename)
    return handleStart(tokenizer)

# ______________________________________________________________________

def main ():
    import sys
    if len(sys.argv) > 1:
        parseTree = parseFile(sys.argv[1])
    else:
        parseTree = parseString(sys.stdin.read())
    from basil.visuals.TreeBox import showTree
    showTree(parseTree).mainloop()

# ______________________________________________________________________

if __name__ == "__main__":
    main()

# ______________________________________________________________________
# End of PgenParser.py
