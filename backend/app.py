#!/usr/bin/env python3
"""Simple Flask API exposing a stub equation solver."""

from __future__ import annotations
# from sympy import symbols, solve as sym_solve, sympify, Eq
import sympy as sp

from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
    convert_xor,
)
import re
import os
from flask import Flask, jsonify, request


def create_app() -> Flask:
    app = Flask(__name__)

    @app.after_request
    def add_cors_headers(response):  # type: ignore[override]
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return response
    
    def preprocess_equation(equation: str) -> str:
        equation = equation.lower() 
        
        equation = re.sub(r'(\d)([a-zA-Z])', r'\1*\2', equation)
        equation = re.sub(r'(\d)\(', r'\1*(', equation)
        equation = re.sub(r'\)(\d)', r')*\1', equation)
        equation = re.sub(r'\)([a-zA-Z])', r')*\1', equation)
        equation = re.sub(r'([a-zA-Z])\(', r'\1*(', equation)
        equation = equation.replace('^', '**')
        return equation

    @app.get("/solve")
    def solve():
        equation = (request.args.get("equation") or "").strip()

        if not equation:
            return jsonify({"error": "Missing 'equation' query parameter"}), 400
        try:
            equation_str = preprocess_equation(equation.lower())

            # transformations for parsing
            transformations = (standard_transformations + (implicit_multiplication_application,) + (convert_xor,))

            # Spliting multiple equations into individual equation strings
            equations = [ eq.strip() for eq in equation.split(',') if eq.strip()]

            sympy_equations = []
            all_symbols = set()

            # Parse and collect all equations and variables
            for eq_str in equations:

                # Preprocess each equation string
                equation_str = preprocess_equation(eq_str)

                # Split by '=' to create an Eq object
                if "=" in equation_str:
                    lhs_str, rhs_str = equation_str.split("=", 1)
                    lhs = parse_expr(lhs_str, transformations=transformations)
                    rhs = parse_expr(rhs_str, transformations=transformations)
                    expr = sp.Eq(lhs, rhs)
                else:
                    # Treat the raw equation as being equal to zero, for single equation
                    expr = parse_expr(equation_str, transformations=transformations)

                sympy_equations.append(expr)

                # Collect all symbols (variables) found in this expression
                for sym in expr.free_symbols:
                    all_symbols.add(sym)
            
            # Convert set of symbols to a list for sp.solve()
            symbols_list = sorted(list(all_symbols), key=str)

            # Solve the system of equationsSolving
            solution = sp.solve(sympy_equations, symbols_list)

            final_results = []
            # Determining the solution structure returned by sp.solve()
            is_system_solution = isinstance(solution, dict) or (isinstance(solution, list) and solution and isinstance(solution[0], dict))
            
            if is_system_solution:
                # systems of equations - dicts or list of dicts

                if isinstance(solution, dict):
                    solution_sets = [solution]
                elif isinstance(solution, list) and all(isinstance(s, dict) for s in solution):
                    solution_sets = solution
                else:
                    # Handle edge case where SymPy might return something unexpected for a system
                    raise ValueError(f"Unexpected solution structure for system: {type(solution)}")
                
                # Formatting each solution set into a string-based dictionary
                for sol_set in solution_sets:
                    formatted_set = {}
                    for symbol, value in sol_set.items():
                        formatted_set[str(symbol)] = str(value)
                    final_results.append(str(formatted_set))
            else:
                # single equation - list of values
                # Formatting each solution into a string
                final_results = [str(s) for s in solution]

            return jsonify({ "result": final_results})

        except Exception as err:
            return jsonify({"error": f"Failed to solve equation: {err}"}), 400
        
        return jsonify({"result": f"not implemented: solving '{equation}'"})

    @app.route("/", methods=["GET"])
    def root():
        return jsonify({"message": "Equation API. Try /solve?equation=1+1"})

    return app


def run() -> None:
    port = int(os.environ.get("PORT", 8000))
    app = create_app()
    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    run()
