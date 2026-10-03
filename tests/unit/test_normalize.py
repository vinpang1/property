import pytest

from src.etl.normalize import strip_whitespace, unify_floor_format


class TestNormalize:
    def test_strip_whitespace(self):
        assert strip_whitespace("  青山灣  ") == "青山灣"

    def test_unify_floor_format_slash(self):
        assert unify_floor_format("12/F") == "12/F"

    def test_unify_floor_format_chinese(self):
        assert unify_floor_format("3樓") == "3/F"

    def test_unify_floor_format_number(self):
        assert unify_floor_format("8") == "8/F"
