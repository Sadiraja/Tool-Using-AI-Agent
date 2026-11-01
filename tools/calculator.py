"""
Calculator tool for safe mathematical evaluation.
"""

import ast
import math
import operator
from typing import Any, Dict
from pydantic import BaseModel, Field
from tools.base import BaseTool


class CalculatorInput(BaseModel):
    expression: str = Field(
        ...,
        description="The mathematical expression to evaluate, e.g., '125000 * 0.15 * 1.22' or 'sqrt(144) + 25 * 4'."
    )
    precision: int = Field(
        default=4,
        ge=0,
        le=10,
        description="Number of decimal places for rounding the result (0 to 10)."
    )


class CalculatorTool(BaseTool):
    name = "calculator"
    description = (
        "Safely evaluates mathematical expressions including addition, subtraction, "
        "multiplication, division, exponentiation, modulo, and functions like sqrt, log, abs, round, min, max."
    )
    args_schema = CalculatorInput

    # Allowed operators
    _OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    # Allowed math functions and constants
    _FUNCTIONS: Dict[str, Any] = {
        "sqrt": math.sqrt,
        "log": math.log,
        "log10": math.log10,
        "exp": math.exp,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "sum": sum,
        "ceil": math.ceil,
        "floor": math.floor,
        "pi": math.pi,
        "e": math.e,
    }

    def _eval_node(self, node: ast.AST) -> Any:
        if isinstance(node, ast.Expression):
            return self._eval_node(node.body)
        elif isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError(f"Unsupported constant type: {type(node.value).__name__}")
        elif isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type in self._OPERATORS:
                return self._OPERATORS[op_type](self._eval_node(node.operand))
            raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
        elif isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type in self._OPERATORS:
                left = self._eval_node(node.left)
                right = self._eval_node(node.right)
                # Check division by zero
                if op_type in (ast.Div, ast.FloorDiv, ast.Mod) and right == 0:
                    raise ZeroDivisionError("Division by zero in mathematical expression.")
                return self._OPERATORS[op_type](left, right)
            raise ValueError(f"Unsupported binary operator: {op_type.__name__}")
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
                if func_name in self._FUNCTIONS:
                    args = [self._eval_node(arg) for arg in node.args]
                    return self._FUNCTIONS[func_name](*args)
                raise ValueError(f"Disallowed or unknown function '{func_name}'.")
            raise ValueError("Only simple function calls are allowed.")
        elif isinstance(node, ast.Name):
            if node.id in self._FUNCTIONS and isinstance(self._FUNCTIONS[node.id], (int, float)):
                return self._FUNCTIONS[node.id]
            raise ValueError(f"Variable or identifier '{node.id}' is not recognized.")
        elif isinstance(node, ast.List):
            return [self._eval_node(elem) for elem in node.elts]
        else:
            raise ValueError(f"Unsupported AST syntax: {type(node).__name__}")

    def _execute(self, expression: str, precision: int = 4) -> Dict[str, Any]:
        cleaned_expr = expression.strip()
        if not cleaned_expr:
            raise ValueError("Empty mathematical expression provided.")

        try:
            parsed = ast.parse(cleaned_expr, mode="eval")
        except SyntaxError as e:
            raise ValueError(f"Invalid syntax in mathematical expression '{cleaned_expr}': {e.msg}")

        raw_result = self._eval_node(parsed)
        if isinstance(raw_result, float):
            result = round(raw_result, precision)
        else:
            result = raw_result

        return {
            "expression": cleaned_expr,
            "result": result,
            "raw_result": raw_result
        }
