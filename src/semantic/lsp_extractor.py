"""
LSP-inspired symbol extractor for Python source files.

Uses Python's ast module to extract class and function definitions,
converting them into semantic signals for domain/concept detection.
No external LSP server required.
"""
import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class SymbolInfo:
    name: str
    kind: str          # 'class' | 'function' | 'method'
    module: str        # dotted module path
    line: int
    docstring: str | None
    bases: list[str]   # for classes: base class names


def extract_symbols(source_path: Path) -> list[SymbolInfo]:
    """
    Extract class and function symbols from a Python source file.
    Returns empty list if file cannot be parsed.
    """
    try:
        source = source_path.read_text(encoding='utf-8')
        tree = ast.parse(source, filename=str(source_path))
    except (SyntaxError, OSError):
        return []

    module_name = source_path.stem
    symbols = []

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            bases = [_name_of(b) for b in node.bases if _name_of(b)]
            symbols.append(SymbolInfo(
                name=node.name,
                kind='class',
                module=module_name,
                line=node.lineno,
                docstring=ast.get_docstring(node),
                bases=bases,
            ))
            for item in ast.iter_child_nodes(node):
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and not item.name.startswith('_'):
                    symbols.append(SymbolInfo(
                        name=f"{node.name}.{item.name}",
                        kind='method',
                        module=module_name,
                        line=item.lineno,
                        docstring=ast.get_docstring(item),
                        bases=[],
                    ))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith('_'):
                symbols.append(SymbolInfo(
                    name=node.name,
                    kind='function',
                    module=module_name,
                    line=node.lineno,
                    docstring=ast.get_docstring(node),
                    bases=[],
                ))

    return symbols


def symbols_to_signals(symbols: list[SymbolInfo], source_path: Path) -> list[dict[str, Any]]:
    """Convert extracted symbols into semantic signals format"""
    signals = []
    classes = [s for s in symbols if s.kind == 'class']
    functions = [s for s in symbols if s.kind == 'function']

    if classes:
        signals.append({
            'signal_type': 'class_definitions',
            'source': f'lsp:{source_path.name}',
            'evidence': f'{len(classes)} classes: {", ".join(s.name for s in classes[:5])}',
            'confidence': 'high',
            'summary': f'{source_path.name} defines {len(classes)} classes',
        })

    if functions:
        signals.append({
            'signal_type': 'function_definitions',
            'source': f'lsp:{source_path.name}',
            'evidence': f'{len(functions)} functions',
            'confidence': 'medium',
            'summary': f'{source_path.name} defines {len(functions)} top-level functions',
        })

    return signals


def extract_lsp_signals_from_dir(src_dir: Path) -> list[dict[str, Any]]:
    """
    Walk a source directory and extract LSP signals from all .py files.
    Returns a flat list of signals.
    """
    all_signals = []
    for py_file in sorted(src_dir.rglob('*.py')):
        symbols = extract_symbols(py_file)
        if symbols:
            all_signals.extend(symbols_to_signals(symbols, py_file))
    return all_signals


def _name_of(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ''
