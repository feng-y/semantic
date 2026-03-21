"""Tests for normalize module."""

import pytest

from src.normalize import normalize_text


class TestNormalizeText:
    """Tests for normalize_text function."""

    def test_empty_string(self):
        """Test empty string returns empty."""
        assert normalize_text("") == ""

    def test_whitespace_normalization(self):
        """Test multiple whitespace collapsed to single space."""
        assert normalize_text("hello   world") == "hello world"
        assert normalize_text("hello\tworld") == "hello world"
        assert normalize_text("hello\n\nworld") == "hello world"

    def test_leading_trailing_whitespace(self):
        """Test leading/trailing whitespace stripped."""
        assert normalize_text("  hello world  ") == "hello world"

    def test_ascii_lowercasing(self):
        """Test ASCII letters lowercased."""
        assert normalize_text("HELLO WORLD") == "hello world"
        assert normalize_text("Hello World") == "hello world"

    def test_unicode_preserved(self):
        """Test non-ASCII characters preserved in case."""
        assert normalize_text("你好 World") == "你好 world"

    def test_punctuation_normalization(self):
        """Test Chinese punctuation normalized to ASCII."""
        assert normalize_text("hello，world") == "hello,world"
        assert normalize_text("test。end") == "test.end"
        assert normalize_text("key：value") == "key:value"
        assert normalize_text("a；b") == "a;b"
        assert normalize_text("（test）") == "(test)"

    def test_synonym_normalization(self):
        """Test Chinese synonyms normalized."""
        assert normalize_text("修正bug") == "修复bug"
        assert normalize_text("调整性能") == "优化性能"
        assert normalize_text("接入新功能") == "新增新功能"
        assert normalize_text("引入模块") == "新增模块"

    def test_synonym_disabled(self):
        """Test synonym normalization can be disabled."""
        assert normalize_text("修正bug", synonym_normalize=False) == "修正bug"

    def test_number_placeholder(self):
        """Test numbers replaced with <NUM> placeholder."""
        assert normalize_text("fix 123 issues", normalize_numbers=True) == "fix <NUM> issues"
        assert normalize_text("version 1.2.3", normalize_numbers=True) == "version <NUM>.<NUM>"

    def test_decimal_numbers(self):
        """Test decimal numbers handled correctly."""
        assert normalize_text("value 3.14", normalize_numbers=True) == "value <NUM>"

    def test_number_placeholder_disabled_by_default(self):
        """Test numbers preserved by default."""
        assert normalize_text("fix 123 issues") == "fix 123 issues"

    def test_lowercasing_disabled(self):
        """Test lowercasing can be disabled."""
        assert normalize_text("HELLO", lowercase_ascii=False) == "HELLO"

    def test_combined_normalization(self):
        """Test all normalization options together."""
        result = normalize_text(
            "  修正  BUG，在  123  个文件中  ",
            normalize_numbers=True
        )
        assert result == "修复 bug,在 <NUM> 个文件中"

    def test_nfkc_normalization(self):
        """Test NFKC Unicode normalization applied."""
        # Fullwidth characters should be normalized
        assert normalize_text("ｈｅｌｌｏ") == "hello"


class TestNormalizeTextEdgeCases:
    """Edge case tests for normalize_text."""

    def test_only_whitespace(self):
        """Test string with only whitespace."""
        assert normalize_text("   ") == ""
        assert normalize_text("\t\n") == ""

    def test_only_punctuation(self):
        """Test string with only punctuation."""
        assert normalize_text("。") == "."
        assert normalize_text("，") == ","

    def test_mixed_unicode(self):
        """Test mixed Chinese and English."""
        result = normalize_text("修复BUG，优化CODE质量")
        assert result == "修复bug,优化code质量"
