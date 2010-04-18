"""Tools for manipulating expressions in unevaluated form. """

from sympify import sympify, SympifyError

import ast_parser

class HoldMixin(object):
    """Mixin class adding support for unevaluated expressions. """

    _unhold_cls = None

    def _eval_unhold(self, what):
        if self.is_Atom:
            return self

        args = [ arg._eval_unhold(what) for arg in self.args ]

        if self.is_Hold and not what or self._unhold_cls in what:
            return self._unhold_cls(*args)
        else:
            return self.new(*args)

    def unhold(self, what=None):
        """Transform an object recursively into an evaluated form. """
        what = sympify(what)

        if what is None:
            what = []
        elif not hasattr(what, '__iter__'):
            what = [what]

        return self._eval_unhold(what)

    def unhold_first(self):
        """Transform the topmost object into an evaluated form. """
        if self.is_Hold:
            return self._unhold_cls(*self.args)
        else:
            return self

if ast_parser.ast_enabled:
    import ast

    fix = ast.fix_missing_locations

    class HoldTransform(ast_parser.Transform):

        def visit_Call(self, node):
            node = self.generic_visit(node)

            if isinstance(node.func, ast.Name) and node.func.id == 'sqrt':
                return fix(ast.Call(ast.Name('hold_sqrt', ast.Load()),
                    node.args, node.keywords, node.starargs, node.kwargs))
            else:
                return node

        def visit_BinOp(self, node):
            node = self.generic_visit(node)

            if isinstance(node.op, ast.Add):
                cls, left, right = 'HoldAdd', node.left, node.right
            elif isinstance(node.op, ast.Sub):
                cls, left, right = 'HoldAdd', node.left, self.visit(ast.UnaryOp(ast.USub(), node.right))
            elif isinstance(node.op, ast.Mult):
                cls, left, right = 'HoldMul', node.left, node.right
            elif isinstance(node.op, ast.Div):
                cls, left, right = 'HoldMul', node.left, self.visit(ast.BinOp(node.right, ast.Pow(), ast.Num(-1)))
            elif isinstance(node.op, ast.Pow):
                cls, left, right = 'HoldPow', node.left, node.right
            else:
                return node

            return fix(ast.Call(ast.Name(cls, ast.Load()), [left, right], [], None, None))

def hold(form, local_dict=None):
    """Transform a ``form`` to an expression but do not evaluate. """
    if not isinstance(form, str):
        raise TypeError("a form to hold() must be a string")

    if not ast_parser.ast_enabled:
        raise RuntimeError("hold() needs 'ast' module (>= Python 2.6)")

    global_dict = {}

    exec 'from sympy import *' in global_dict

    try:
        parsed = ast.parse(form.strip(), mode="eval")
    except SyntaxError:
        raise SympifyError("can't parse '%s' form" % form)

    transform = HoldTransform(local_dict or {}, global_dict)

    return eval(compile(transform.visit(parsed),
        "<string>", "eval"), local_dict or {}, global_dict)

def unhold(expr, what=None):
    """Transform an object recursively into an evaluated form. """
    return sympify(expr).unhold(what)

def unhold_first(self):
    """Transform the topmost object into an evaluated form. """
    return sympify(expr).unhold_first()

