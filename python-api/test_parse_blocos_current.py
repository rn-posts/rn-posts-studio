import ast
from pathlib import Path

source = Path(__file__).with_name("main.py").read_text(encoding="utf-8")
tree = ast.parse(source)
node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_parse_blocos")
ns = {}
exec(compile(ast.Module(body=[node], type_ignores=[]), "main.py", "exec"), ns)

result = ns["_parse_blocos"]("Uma vida sem -desordem fim")
expected = [
    {"texto": "Uma vida sem", "estilo": "normal"},
    {"texto": "desordem", "estilo": "fundo"},
    {"texto": "fim", "estilo": "normal"},
]
assert result == expected, result
print(result)
print("parser inline: OK")
