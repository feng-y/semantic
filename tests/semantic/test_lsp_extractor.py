"""
Tests for LSP-inspired symbol extractor
"""
import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from semantic.lsp_extractor import (
    SymbolInfo,
    extract_symbols,
    symbols_to_signals,
    extract_lsp_signals_from_dir,
)


def test_extract_symbols_class(tmp_path):
    src = tmp_path / "mymodule.py"
    src.write_text("class Foo(Base):\n    pass\n")
    symbols = extract_symbols(src)
    classes = [s for s in symbols if s.kind == 'class']
    assert len(classes) == 1
    assert classes[0].name == 'Foo'
    assert classes[0].kind == 'class'
    assert classes[0].bases == ['Base']
    assert classes[0].module == 'mymodule'


def test_extract_symbols_function(tmp_path):
    src = tmp_path / "mod.py"
    src.write_text("def do_thing():\n    pass\n")
    symbols = extract_symbols(src)
    funcs = [s for s in symbols if s.kind == 'function']
    assert len(funcs) == 1
    assert funcs[0].name == 'do_thing'
    assert funcs[0].kind == 'function'


def test_extract_symbols_method(tmp_path):
    src = tmp_path / "mod.py"
    src.write_text("class MyClass:\n    def run(self):\n        pass\n")
    symbols = extract_symbols(src)
    methods = [s for s in symbols if s.kind == 'method']
    assert len(methods) == 1
    assert methods[0].name == 'MyClass.run'
    assert methods[0].kind == 'method'


def test_extract_symbols_private_skipped(tmp_path):
    src = tmp_path / "mod.py"
    src.write_text(
        "def _private():\n    pass\n\nclass Foo:\n    def _hidden(self):\n        pass\n"
    )
    symbols = extract_symbols(src)
    names = [s.name for s in symbols]
    assert '_private' not in names
    assert 'Foo._hidden' not in names


def test_extract_symbols_syntax_error(tmp_path):
    src = tmp_path / "bad.py"
    src.write_text("def broken(\n")
    symbols = extract_symbols(src)
    assert symbols == []


def test_symbols_to_signals_classes(tmp_path):
    src = tmp_path / "mod.py"
    symbols = [
        SymbolInfo(name='Alpha', kind='class', module='mod', line=1, docstring=None, bases=[]),
        SymbolInfo(name='Beta', kind='class', module='mod', line=5, docstring=None, bases=[]),
    ]
    signals = symbols_to_signals(symbols, src)
    class_signals = [s for s in signals if s['signal_type'] == 'class_definitions']
    assert len(class_signals) == 1
    assert class_signals[0]['confidence'] == 'high'
    assert 'Alpha' in class_signals[0]['evidence']


def test_symbols_to_signals_functions(tmp_path):
    src = tmp_path / "mod.py"
    symbols = [
        SymbolInfo(name='run', kind='function', module='mod', line=1, docstring=None, bases=[]),
    ]
    signals = symbols_to_signals(symbols, src)
    func_signals = [s for s in signals if s['signal_type'] == 'function_definitions']
    assert len(func_signals) == 1
    assert func_signals[0]['confidence'] == 'medium'


def test_extract_lsp_signals_from_dir(tmp_path):
    (tmp_path / "a.py").write_text("class Foo:\n    pass\n")
    (tmp_path / "b.py").write_text("def bar():\n    pass\n")
    signals = extract_lsp_signals_from_dir(tmp_path)
    assert len(signals) >= 2
    types = {s['signal_type'] for s in signals}
    assert 'class_definitions' in types
    assert 'function_definitions' in types


def test_docstring_captured(tmp_path):
    src = tmp_path / "mod.py"
    src.write_text('class Documented:\n    """This is a docstring."""\n    pass\n')
    symbols = extract_symbols(src)
    classes = [s for s in symbols if s.kind == 'class']
    assert len(classes) == 1
    assert classes[0].docstring == 'This is a docstring.'
