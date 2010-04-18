"""Tests for functions and classes concerning unevaluated expressions. """

from sympy import Rational, Add, Mul, Pow, sin, raises

from sympy.core.holdtools import hold, unhold, unhold_first
from sympy.core.holdclasses import HoldAdd, HoldMul, HoldPow

from sympy.abc import x, y, z

def test_HoldAdd():
    assert HoldAdd() == 0
    assert HoldAdd(2) == 2
    assert HoldAdd(2, 2) != Add(2, 2)
    assert HoldAdd(2, 2).unhold() == Add(2, 2)

def test_HoldMul():
    assert HoldMul() == 1
    assert HoldMul(2) == 2
    assert HoldMul(2, 2) != Mul(2, 2)
    assert HoldMul(2, 2).unhold() == Mul(2, 2)

def test_HoldPow():
    assert HoldPow(2, 2) != Pow(2, 2)
    assert HoldPow(2, 2).unhold() == Pow(2, 2)

def test_hold_unhold():
    expr = HoldAdd(1, 1, HoldMul(1, sin(HoldAdd(x, x))), HoldMul(1, 2, 3))

    try:
        assert hold('1 + 1 + 1*sin(x + x) + 1*2*3') == expr
        assert hold('sqrt(2)') == HoldPow(2, Rational(1, 2))
        assert hold('x*y/z') == HoldMul(x, y, HoldPow(z, -1))
    except RuntimeError:
        pass

    assert expr.unhold() == 8 + sin(2*x)

    assert expr.unhold(Add) == 2 + HoldMul(1, sin(2*x)) + HoldMul(1, 2, 3)
    assert expr.unhold('Add') == 2 + HoldMul(1, sin(2*x)) + HoldMul(1, 2, 3)

    assert expr.unhold(Mul) == HoldAdd(1, 1, sin(HoldAdd(x, x)), 6)
    assert expr.unhold('Mul') == HoldAdd(1, 1, sin(HoldAdd(x, x)), 6)

    assert expr.unhold(Add).unhold(Mul) == 8 + sin(2*x)
    assert expr.unhold(Mul).unhold(Add) == 8 + sin(2*x)

    assert expr.unhold_first() == 2 + HoldMul(1, sin(HoldAdd(x, x))) + HoldMul(1, 2, 3)

    raises(TypeError, "hold(1)")

