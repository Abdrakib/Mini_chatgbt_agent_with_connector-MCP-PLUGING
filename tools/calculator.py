import ast
import operator
import re
from typing import Optional

_FAILURE = "Sorry I could not calculate that"

# Match a math expression: numbers and + - * / ** % (no parentheses)
_EXPR_PATTERN = re.compile(
    r"-?\d+(?:\.\d+)?(?:\s*(?:\*\*|[+\-*/%])\s*-?\d+(?:\.\d+)?)+"
)


def _normalize_text(message: str) -> str:
    s = message.lower().strip()
    # Longer phrases first so "multiplied by" wins over "by"
    replacements = (
        ("divided by", "/"),
        ("multiplied by", "*"),
        ("times", "*"),
        ("plus", "+"),
        ("minus", "-"),
        ("modulo", "%"),
        (" to the power of ", "**"),
    )
    for a, b in replacements:
        s = s.replace(a, b)
    s = re.sub(r"\bmod\b", "%", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _strip_leading_phrases(s: str) -> str:
    return re.sub(
        r"^(?:what\s+is|calculate|compute|find|eval|evaluate)\s+",
        "",
        s,
        flags=re.IGNORECASE,
    ).strip()


def _extract_expression(message: str) -> Optional[str]:
    normalized = _normalize_text(message)
    trimmed = _strip_leading_phrases(normalized)
    m = _EXPR_PATTERN.search(trimmed)
    if not m:
        m = _EXPR_PATTERN.search(normalized)
    if not m:
        return None
    expr = m.group(0).strip()
    if not expr:
        return None
    return expr


_ALLOWED_BINOPS = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod)
_ALLOWED_UNARY = (ast.UAdd, ast.USub)

_BINOP_FUNC = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
}


def _safe_eval_node(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _safe_eval_node(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return float(node.value)
        raise ValueError
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, _ALLOWED_UNARY):
        v = _safe_eval_node(node.operand)
        if isinstance(node.op, ast.USub):
            return -v
        return +v
    if isinstance(node, ast.BinOp) and isinstance(node.op, _ALLOWED_BINOPS):
        left = _safe_eval_node(node.left)
        right = _safe_eval_node(node.right)
        return _BINOP_FUNC[type(node.op)](left, right)
    raise ValueError


def _safe_eval_expression(expr: str) -> float:
    tree = ast.parse(expr, mode="eval")
    return _safe_eval_node(tree)


def _format_number(n: float) -> str:
    if isinstance(n, float) and n.is_integer():
        return str(int(n))
    # Trim trailing zeros for readability
    s = f"{n:.12g}"
    return s


def run_calculator(message: str) -> str:
    try:
        expr = _extract_expression(message)
        if not expr:
            return _FAILURE
        result = _safe_eval_expression(expr)
        if not isinstance(result, (int, float)) or result != result:  # NaN
            return _FAILURE
        return f"The answer is {_format_number(float(result))}"
    except (ValueError, SyntaxError, ZeroDivisionError, TypeError, OverflowError):
        return _FAILURE


if __name__ == "__main__":
    for sample in (
        "what is 25 times 4",
        "calculate 100 divided by 5",
        "15 + 27",
    ):
        print(sample, "->", run_calculator(sample))
