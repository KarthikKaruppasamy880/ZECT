from unittest.mock import patch

import pytest

from app.services.mentrix.sheets import (
    generate_workbook,
    normalize_workbook,
    resolve_workbook_path,
    workbook_from_xlsx,
    workbook_to_xlsx,
)


def test_normalize_rejects_bad_addresses():
    wb = normalize_workbook({"sheets": [{"name": "A", "cells": {"1A": {"v": "x"}, "AAAA1": {"v": "x"}, "A1": {"v": "ok"}}}]})
    assert "A1" in wb["sheets"][0]["cells"]
    assert "1A" not in wb["sheets"][0]["cells"]
    assert "AAAA1" not in wb["sheets"][0]["cells"]


def test_xlsx_roundtrip_two_by_three():
    wb = {
        "sheets": [
            {
                "name": "Grid",
                "cells": {
                    "A1": {"v": "Name", "f": ""},
                    "B1": {"v": "Qty", "f": ""},
                    "C1": {"v": "Note", "f": ""},
                    "A2": {"v": "Alpha", "f": ""},
                    "B2": {"v": "2", "f": ""},
                    "C2": {"v": "", "f": "=B2"},
                },
            }
        ]
    }
    data = workbook_to_xlsx(wb)
    back = workbook_from_xlsx(data)
    assert back["sheets"][0]["cells"]["A1"]["v"] == "Name"
    assert back["sheets"][0]["cells"]["C2"]["f"] == "=B2"


def test_path_escape_rejected():
    with pytest.raises(ValueError, match="path_escape"):
        resolve_workbook_path("../secret.json")


def test_generate_mocked_grid():
    class _Msg:
        content = '{"sheets":[{"name":"Sheet1","cells":{"A1":{"v":"a"},"B1":{"v":"b"},"A2":{"v":"c"}}}]}'

    class _Choice:
        message = _Msg()

    class _Resp:
        choices = [_Choice()]

    class _Client:
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    return _Resp()

    with patch("app.adapters.llm.openai_compat.openai_compat_available", return_value=True):
        with patch("app.adapters.llm.openai_compat.get_openai_compat_client", return_value=_Client()):
            with patch("app.adapters.llm.openai_compat.mentrix_llm_chat_model", return_value="gpt-4o-mini"):
                wb = generate_workbook("make a 2x3 grid")
    assert wb["sheets"][0]["cells"]["A1"]["v"] == "a"
    assert "B1" in wb["sheets"][0]["cells"]
    assert "A2" in wb["sheets"][0]["cells"]
