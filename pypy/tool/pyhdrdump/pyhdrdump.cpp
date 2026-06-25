// pyhdrdump -- dump the Py-prefixed API surface of a Python.h-style header
// in a normalized form, so that CPython's and PyPy's headers can be diffed.
//
// This is a reconstruction of the clang-based tool described by nulano in
// https://github.com/pypy/pypy/issues/3397#issuecomment-1872091878
// (the original source was never published).  It uses libclang so that it sees
// both the preprocessor (every #define) and the real type system (function
// declarations with typedefs resolved), which a preprocessed-source parser such
// as pycparser cannot do.
//
// Output rules (matching the original tool's README):
//   * Only names with a `Py` prefix (but not `PyPy`) are reported.
//   * Functions print as  RETTYPE NAME(ARGTYPE, ...)  with no parameter names.
//   * All typedef'd primitives are replaced by their underlying base type
//     (Py_ssize_t -> long / long long, etc.).
//   * A pointer to a struct/union/void/pointer/function is replaced by `void *`;
//     a pointer to a primitive keeps the pointer (e.g. `const char *`,
//     `long long *`).  The pointee's const qualifier is preserved.
//   * A macro that is a plain alias of -- or a pure argument-forwarder to -- a
//     function is reported as that function, using the macro's name, with the
//     real name in a trailing comment.
//   * A macro that aliases another macro is reported with the fully expanded
//     value and the real macro name in a comment.
//   * Every other macro is printed verbatim as `#define ...`.
//
// Build:  see build.sh
// Usage:  ./pyhdrdump <header.h> [extra clang args, e.g. -I/usr/include/python3.12]

#include <clang-c/Index.h>

#include <algorithm>
#include <cstring>
#include <fstream>
#include <iostream>
#include <map>
#include <sstream>
#include <string>
#include <vector>

namespace {

std::string cxstr(CXString s) {
    const char *c = clang_getCString(s);
    std::string r = c ? c : "";
    clang_disposeString(s);
    return r;
}

bool startsWith(const std::string &s, const char *p) {
    return s.compare(0, std::strlen(p), p) == 0;
}

// A name we are willing to emit: Py-prefixed, but not PyPy-prefixed.
bool isReportable(const std::string &name) {
    return startsWith(name, "Py") && !startsWith(name, "PyPy");
}

bool isArithmeticKind(enum CXTypeKind k) {
    switch (k) {
    case CXType_Bool:
    case CXType_Char_U:  case CXType_UChar:  case CXType_Char16:
    case CXType_Char32:  case CXType_UShort: case CXType_UInt:
    case CXType_ULong:   case CXType_ULongLong: case CXType_UInt128:
    case CXType_Char_S:  case CXType_SChar:  case CXType_WChar:
    case CXType_Short:   case CXType_Int:    case CXType_Long:
    case CXType_LongLong:case CXType_Int128: case CXType_Float:
    case CXType_Double:  case CXType_LongDouble: case CXType_Float128:
    case CXType_Half:
        return true;
    default:
        return false;
    }
}

// Strip a leading "const "/"volatile " from a type spelling.
std::string stripQuals(std::string s) {
    for (;;) {
        if (startsWith(s, "const ")) s = s.substr(6);
        else if (startsWith(s, "volatile ")) s = s.substr(9);
        else break;
    }
    return s;
}

// Format a type per the normalization rules above.
std::string formatType(CXType t) {
    CXType c = clang_getCanonicalType(t);
    if (c.kind == CXType_Pointer) {
        CXType pointee = clang_getCanonicalType(clang_getPointeeType(c));
        std::string prefix = clang_isConstQualifiedType(pointee) ? "const " : "";
        if (isArithmeticKind(pointee.kind)) {
            std::string sp = stripQuals(cxstr(clang_getTypeSpelling(pointee)));
            return prefix + sp + " *";
        }
        return prefix + "void *";
    }
    return cxstr(clang_getTypeSpelling(c));
}

// Render a function declaration's signature with a chosen display name.
std::string functionSignature(CXCursor fn, const std::string &displayName) {
    CXType ft = clang_getCursorType(fn);
    std::string ret = formatType(clang_getResultType(ft));
    int n = clang_getNumArgTypes(ft);
    std::string args;
    if (n <= 0) {
        args = "void";
    } else {
        for (int i = 0; i < n; ++i) {
            if (i) args += ", ";
            args += formatType(clang_getArgType(ft, i));
        }
    }
    return ret + " " + displayName + "(" + args + ")";
}

struct Token {
    std::string spelling;
    CXTokenKind kind;
};

std::vector<Token> tokenize(CXTranslationUnit tu, CXCursor cur) {
    std::vector<Token> out;
    CXSourceRange range = clang_getCursorExtent(cur);
    CXToken *toks = nullptr;
    unsigned n = 0;
    clang_tokenize(tu, range, &toks, &n);
    for (unsigned i = 0; i < n; ++i) {
        out.push_back({cxstr(clang_getTokenSpelling(tu, toks[i])),
                       clang_getTokenKind(toks[i])});
    }
    if (toks) clang_disposeTokens(tu, toks, n);
    return out;
}

// Cache of source-file contents, for verbatim macro extraction.
std::map<std::string, std::string> g_fileCache;

const std::string &fileContents(const std::string &path) {
    auto it = g_fileCache.find(path);
    if (it != g_fileCache.end()) return it->second;
    std::ifstream f(path, std::ios::binary);
    std::ostringstream ss;
    ss << f.rdbuf();
    return g_fileCache.emplace(path, ss.str()).first->second;
}

// The original source text covered by a cursor's extent, with internal newlines
// (and their line-continuation backslashes) collapsed to single spaces.
std::string verbatimSource(CXCursor cur) {
    CXSourceRange range = clang_getCursorExtent(cur);
    CXFile file;
    unsigned line, col, startOff, endOff;
    clang_getFileLocation(clang_getRangeStart(range), &file, &line, &col, &startOff);
    clang_getFileLocation(clang_getRangeEnd(range), nullptr, &line, &col, &endOff);
    if (!file || endOff <= startOff) return "";
    std::string path = cxstr(clang_getFileName(file));
    const std::string &buf = fileContents(path);
    if (endOff > buf.size()) return "";
    std::string raw = buf.substr(startOff, endOff - startOff);
    std::string out;
    out.reserve(raw.size());
    bool prevSpace = false;
    for (size_t i = 0; i < raw.size(); ++i) {
        char ch = raw[i];
        if (ch == '\\' && i + 1 < raw.size() &&
            (raw[i + 1] == '\n' || raw[i + 1] == '\r')) {
            continue;  // drop line-continuation backslash
        }
        if (ch == '\n' || ch == '\r' || ch == '\t' || ch == ' ') {
            if (!prevSpace && !out.empty()) out += ' ';
            prevSpace = true;
        } else {
            out += ch;
            prevSpace = false;
        }
    }
    while (!out.empty() && out.back() == ' ') out.pop_back();
    return out;
}

struct MacroInfo {
    CXCursor cursor;
    bool functionLike = false;
    std::vector<std::string> params;  // for function-like macros
    std::vector<Token> body;          // replacement tokens
};

std::map<std::string, CXCursor> g_functions;   // name -> declaration
std::map<std::string, MacroInfo> g_macros;     // name -> macro info

CXChildVisitResult collect(CXCursor cur, CXCursor, CXClientData data) {
    auto *tu = static_cast<CXTranslationUnit *>(data);
    CXCursorKind kind = clang_getCursorKind(cur);
    std::string name = cxstr(clang_getCursorSpelling(cur));

    if (kind == CXCursor_FunctionDecl) {
        // Keep every function (even non-Py ones such as memcpy); a Py-prefixed
        // forwarding macro may name one of them as its "real name".
        g_functions.emplace(name, cur);
    } else if (kind == CXCursor_MacroDefinition) {
        if (clang_Cursor_isMacroBuiltin(cur)) return CXChildVisit_Continue;
        MacroInfo mi;
        mi.cursor = cur;
        mi.functionLike = clang_Cursor_isMacroFunctionLike(cur);
        std::vector<Token> toks = tokenize(*tu, cur);
        size_t bodyStart = 1;  // token 0 is the macro name
        if (mi.functionLike) {
            // toks: NAME ( p1 , p2 , ... ) body...
            size_t i = 1;
            if (i < toks.size() && toks[i].spelling == "(") {
                ++i;
                while (i < toks.size() && toks[i].spelling != ")") {
                    if (toks[i].kind == CXToken_Identifier)
                        mi.params.push_back(toks[i].spelling);
                    ++i;
                }
                if (i < toks.size()) ++i;  // skip ')'
            }
            bodyStart = i;
        }
        for (size_t i = bodyStart; i < toks.size(); ++i)
            mi.body.push_back(toks[i]);
        g_macros[name] = std::move(mi);
    }
    return CXChildVisit_Continue;
}

// Follow a chain of single-identifier macro aliases to its terminal body text.
std::string resolveMacroValue(const std::string &name, int depth = 0) {
    auto it = g_macros.find(name);
    if (it == g_macros.end() || depth > 32) return name;
    const std::vector<Token> &body = it->second.body;
    if (body.size() == 1 && body[0].kind == CXToken_Identifier &&
        g_macros.count(body[0].spelling)) {
        return resolveMacroValue(body[0].spelling, depth + 1);
    }
    std::string out;
    for (size_t i = 0; i < body.size(); ++i) {
        if (i) out += ' ';
        out += body[i].spelling;
    }
    return out;
}

// If a function-like macro purely forwards all of its parameters, in order, to a
// single function call -- e.g. #define Py_IS_NAN(X) _isnan(X) -- return that
// function's name, else "".
std::string pureForwardTarget(const MacroInfo &mi) {
    const std::vector<Token> &b = mi.body;
    if (b.size() < 3) return "";
    if (b[0].kind != CXToken_Identifier) return "";
    if (b[1].spelling != "(") return "";
    if (b.back().spelling != ")") return "";
    std::vector<std::string> args;
    for (size_t i = 2; i + 1 < b.size(); ++i) {
        if (b[i].spelling == ",") continue;
        if (b[i].kind != CXToken_Identifier) return "";  // not a bare arg
        args.push_back(b[i].spelling);
    }
    if (args != mi.params) return "";
    return b[0].spelling;
}

std::string macroVerbatim(const std::string &name, const MacroInfo &mi) {
    std::string text = verbatimSource(mi.cursor);
    if (!text.empty()) return "#define " + text;
    // Fallback: rebuild from tokens if the extent gave us nothing.
    std::string line = "#define " + name;
    if (mi.functionLike) {
        line += "(";
        for (size_t i = 0; i < mi.params.size(); ++i) {
            if (i) line += ", ";
            line += mi.params[i];
        }
        line += ")";
    }
    for (const Token &t : mi.body) line += " " + t.spelling;
    return line;
}

}  // namespace

int main(int argc, char **argv) {
    const char *prog = argv[0];
    bool wantHelp = argc < 2;
    if (argc >= 2 && (std::strcmp(argv[1], "--help") == 0 ||
                      std::strcmp(argv[1], "-h") == 0)) {
        wantHelp = true;
    }
    if (wantHelp) {
        std::ostream &o = (argc < 2) ? std::cerr : std::cout;
        o << "usage: " << prog << " <header.h> [clang args...]\n\n"
          << "Dump the Py-prefixed API surface of a Python.h-style header in a\n"
          << "normalized form, so CPython's and PyPy's headers can be diffed.\n\n"
          << "Arguments after the header are passed straight to clang; you will\n"
          << "almost always need a -I for the header's own directory, because\n"
          << "Python.h pulls in <pyconfig.h> via an angled include.\n\n"
          << "examples:\n"
          << "  " << prog
          << " /usr/include/python3.12/Python.h -I/usr/include/python3.12\n"
          << "  " << prog
          << " include/pypy3.12/Python.h -Iinclude/pypy3.12\n\n"
          << "useful clang args:\n"
          << "  -I<dir>             add <dir> to the include search path\n"
          << "  --target=<triple>   dump for another ABI, e.g.\n"
          << "                      x86_64-pc-windows-msvc, i386-pc-linux-gnu\n"
          << "  -D<name>[=<val>]    predefine a macro\n\n"
          << "See compare.sh in this directory to diff two dumps.\n";
        return (argc < 2) ? 2 : 0;
    }

    std::vector<const char *> args;
    for (int i = 2; i < argc; ++i) args.push_back(argv[i]);

    CXIndex index = clang_createIndex(0, 0);
    CXTranslationUnit tu = nullptr;
    unsigned options = CXTranslationUnit_DetailedPreprocessingRecord |
                       CXTranslationUnit_SkipFunctionBodies;
    CXErrorCode err = clang_parseTranslationUnit2(
        index, argv[1], args.data(), (int)args.size(), nullptr, 0, options, &tu);
    if (err != CXError_Success || !tu) {
        std::cerr << "error: failed to parse " << argv[1] << " (code " << err
                  << ")\n";
        return 1;
    }

    // Surface fatal include problems, but keep going on ordinary diagnostics.
    unsigned nDiag = clang_getNumDiagnostics(tu);
    for (unsigned i = 0; i < nDiag; ++i) {
        CXDiagnostic d = clang_getDiagnostic(tu, i);
        if (clang_getDiagnosticSeverity(d) >= CXDiagnostic_Error) {
            std::cerr << "diag: "
                      << cxstr(clang_formatDiagnostic(
                             d, clang_defaultDiagnosticDisplayOptions()))
                      << "\n";
        }
        clang_disposeDiagnostic(d);
    }

    clang_visitChildren(clang_getTranslationUnitCursor(tu), collect, &tu);

    // Build the merged, name-sorted output.  Macros take precedence over a
    // function of the same name (the macro is what a caller actually sees).
    std::map<std::string, std::string> lines;

    for (auto &kv : g_macros) {
        const std::string &name = kv.first;
        if (!isReportable(name)) continue;
        const MacroInfo &mi = kv.second;

        if (mi.functionLike) {
            std::string target = pureForwardTarget(mi);
            auto fit = g_functions.find(target);
            if (!target.empty() && fit != g_functions.end()) {
                lines[name] = functionSignature(fit->second, name) +
                              " /* macro, real name " + target + " */";
                continue;
            }
        } else if (mi.body.size() == 1 &&
                   mi.body[0].kind == CXToken_Identifier) {
            const std::string &id = mi.body[0].spelling;
            auto fit = g_functions.find(id);
            if (fit != g_functions.end()) {
                lines[name] = functionSignature(fit->second, name) +
                              " /* macro, real name " + id + " */";
                continue;
            }
            if (g_macros.count(id)) {
                lines[name] = "#define " + name + " " + resolveMacroValue(id) +
                              " /* macro, real name " + id + " */";
                continue;
            }
        }
        lines[name] = macroVerbatim(name, mi);
    }

    for (auto &kv : g_functions) {
        const std::string &name = kv.first;
        if (!isReportable(name)) continue;
        if (lines.count(name)) continue;  // shadowed by a macro
        lines[name] = functionSignature(kv.second, name);
    }

    for (auto &kv : lines) std::cout << kv.second << "\n";

    clang_disposeTranslationUnit(tu);
    clang_disposeIndex(index);
    return 0;
}
