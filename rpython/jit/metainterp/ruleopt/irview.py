"""Graphviz rendering for the IR's debugging helpers.

Edges describe tree fields, not control flow. Dashed edges connect bindings
and references to shared Value objects.
"""
from rpython.jit.metainterp.ruleopt import ir
from rpython.jit.metainterp.ruleopt.emit import PythonEmitter


def quote(text):
    return '"%s"' % (text.replace('\\', '\\\\').replace('"', '\\"')
                    .replace('\n', '\\n').replace('\r', '\\r'))


def fields(node):
    if isinstance(node, ir.Bind):
        return [('value', node.value), ('expr', node.expr)]
    if isinstance(node, ir.If):
        return [('condition', node.condition),
                ('then_block', node.then_block), ('else_block', node.else_block)]
    if isinstance(node, ir.Call):
        return ([('function', node.function), ('args', node.args)] +
                [('keyword ' + name, expr) for name, expr in node.keywords])
    return sorted(vars(node).items())


def as_dot(root):
    names = PythonEmitter()
    names.reserve_symbols(root)
    nodes = {}
    lines = ['digraph ruleopt_ir {',
             '  graph [ordering="out"];',
             '  node [shape="box", style="rounded,filled", fontname="monospace"];',
             '  edge [fontname="monospace", fontsize="10"];']

    def visit(node):
        if node in nodes:
            return nodes[node]
        ident = 'n%d' % len(nodes)
        nodes[node] = ident
        label = [type(node).__name__]
        children = []

        def field(name, value):
            if isinstance(value, ir.Node):
                children.append((name, value))
            elif isinstance(value, list) and value:
                for index, item in enumerate(value):
                    field('%s[%d]' % (name, index), item)
            else:
                text = value if name == 'comment' else repr(value)
                label.append('%s = %s' % (name, text))

        if isinstance(node, ir.Value):
            label.append(names.name_for(node))
            color = '#fff2cc'
        else:
            for name, value in fields(node):
                field(name, value)
            if isinstance(node, ir.Block):
                color = '#dae8fc'
            elif isinstance(node, ir.If):
                color = '#e1d5e7'
            elif isinstance(node, (ir.Return, ir.FinishRule)):
                color = '#d5e8d4'
            elif isinstance(node, ir.Stmt):
                color = '#eeeeee'
            else:
                color = '#ffffff'
        lines.append('  %s [label=%s, fillcolor=%s];' % (
            ident, quote('\n'.join(label)), quote(color)))
        for name, child in children:
            child_id = visit(child)
            style = 'dashed' if isinstance(child, ir.Value) else 'solid'
            lines.append('  %s -> %s [label=%s, style=%s];' % (
                ident, child_id, quote(name), quote(style)))
        return ident

    visit(root)
    lines.append('}')
    return '\n'.join(lines)
