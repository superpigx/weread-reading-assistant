# -*- coding: utf-8 -*-
"""核心纯函数单元测试（不需要浏览器）。运行: python tests/test_core.py"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from common import extract_books, pick, _safe_json_parse, BOOK_RE


class TestExtractBooks:
    def test_basic(self):
        txt = "世界级畅销书《秘密》的灵感源泉，《秘密》背后的终极秘密，《思考致富》和《圣经》"
        result = extract_books(txt)
        assert "秘密" in result
        assert "思考致富" in result
        assert "圣经" in result
        # 去重：应由调用方处理
        assert result.count("秘密") == 2

    def test_exclude_self(self):
        txt = "《失落的致富经典》与《思考致富》并称三大财富著作"
        result = extract_books(txt, self_title="失落的致富经典")
        assert "失落的致富经典" not in result
        assert "思考致富" in result

    def test_nested_handled(self):
        # 《《秘密》》 — 外层因含嵌套《被拒绝，内层《秘密》正常提取
        txt = "《《秘密》》"
        result = extract_books(txt)
        assert "秘密" in result  # 内层被正确提取
        assert len(result) == 1

    def test_short_reject(self):
        txt = "《一》本书"
        result = extract_books(txt)
        assert len(result) == 0  # <2 字丢弃

    def test_cross_page_reject(self):
        txt = "《世界上最伟..》"
        result = extract_books(txt)
        assert len(result) == 0  # 跨页截断丢弃


class TestSafeJsonParse:
    def test_valid_json(self):
        assert _safe_json_parse('{"a":1}') == {"a": 1}
        assert _safe_json_parse('[1,2,3]', []) == [1, 2, 3]

    def test_invalid_json(self):
        assert _safe_json_parse('not json', []) == []
        assert _safe_json_parse('', {}) == {}

    def test_non_string(self):
        assert _safe_json_parse([1, 2]) == [1, 2]
        assert _safe_json_parse({"k": "v"}) == {"k": "v"}
        assert _safe_json_parse(None, []) == []


class TestPick:
    def test_exact_match(self):
        cands = [
            {"t": "失落的致富经典 作者", "rec": 85.0},
            {"t": "失落的致富经典（珍藏版） 作者2", "rec": 92.0},
        ]
        result = pick(cands, "失落的致富经典")
        assert result is not None
        assert result["rec"] == 92.0  # 推荐值最高

    def test_empty(self):
        assert pick([], "anything") is None

    def test_partial_match(self):
        cands = [{"t": "完全无关", "rec": 90.0}]
        result = pick(cands, "失落的")
        assert result is None  # 无匹配


class TestBookRe:
    def test_simple(self):
        matches = BOOK_RE.findall("《失落的致富经典》")
        assert matches == ["失落的致富经典"]

    def test_multiple(self):
        matches = BOOK_RE.findall("《秘密》《思考致富》《圣经》")
        assert matches == ["秘密", "思考致富", "圣经"]

    def test_no_match(self):
        matches = BOOK_RE.findall("没有书名号")
        assert matches == []


if __name__ == "__main__":
    # 无需 pytest 也可直接跑
    import traceback
    passed = failed = 0
    for cls_name in [TestExtractBooks, TestSafeJsonParse, TestPick, TestBookRe]:
        cls = cls_name()
        for name in dir(cls):
            if name.startswith("test_"):
                try:
                    getattr(cls, name)()
                    print("  PASS %s.%s" % (cls_name.__name__, name))
                    passed += 1
                except Exception:
                    print("  FAIL %s.%s" % (cls_name.__name__, name))
                    traceback.print_exc()
                    failed += 1
    print("\n%d passed, %d failed" % (passed, failed))
    sys.exit(1 if failed else 0)
