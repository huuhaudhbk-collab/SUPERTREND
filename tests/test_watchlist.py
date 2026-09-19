"""Danh mục nhập tay: parse chuẩn hoá chuỗi người dùng gõ; load đọc env WATCHLIST → bản chụp → rỗng."""
import json

import pytest

from job import watchlist


def test_parse_chuan_hoa():
    assert watchlist.parse("hpg, VNM\nssi;  mwg HPG") == ["HPG", "MWG", "SSI", "VNM"]


def test_parse_bo_token_sai_dang():
    # quá dài, có dấu, quá ngắn, rỗng → bỏ; không ném lỗi
    assert watchlist.parse("HPG, abcdefgh, VN-INDEX, AB, , ,") == ["HPG"]
    assert watchlist.parse("") == []
    assert watchlist.parse(None) == []


@pytest.fixture
def cache(tmp_path, monkeypatch):
    p = tmp_path / "watchlist.json"
    monkeypatch.setattr(watchlist, "CACHE", p)
    return p


def test_load_tu_env_va_ghi_ban_chup(cache, monkeypatch):
    monkeypatch.setattr(watchlist.config, "WATCHLIST", " vnm, hpg ")
    items, src = watchlist.load()
    assert src == "variable"
    assert [it["symbol"] for it in items] == ["HPG", "VNM"]
    snap = json.loads(cache.read_text(encoding="utf-8"))
    assert snap["source"] == "variable" and [it["symbol"] for it in snap["items"]] == ["HPG", "VNM"]


def test_load_env_trong_thi_dung_ban_chup(cache, monkeypatch):
    monkeypatch.setattr(watchlist.config, "WATCHLIST", "")
    cache.write_text(json.dumps({"items": [{"symbol": "SSI", "company_name": ""}]}), encoding="utf-8")
    assert watchlist.load() == ([{"symbol": "SSI", "company_name": ""}], "cache")


def test_load_env_chi_co_rac_thi_dung_ban_chup(cache, monkeypatch):
    monkeypatch.setattr(watchlist.config, "WATCHLIST", "??, -")
    cache.write_text(json.dumps({"items": [{"symbol": "SSI"}]}), encoding="utf-8")
    assert watchlist.load()[1] == "cache"


def test_load_khong_co_gi(cache, monkeypatch):
    monkeypatch.setattr(watchlist.config, "WATCHLIST", "")
    assert watchlist.load() == ([], "none")
    cache.write_text(json.dumps({"items": []}), encoding="utf-8")
    assert watchlist.load() == ([], "none")
