import pytest

from hardware_box.kicad_native import inspect_kicad_native, parse_sexpr


@pytest.mark.parametrize("content", [
    "",
    "(kicad_pcb",
    "(kicad_pcb))",
    "(kicad_sch (version 1)) (kicad_sch (version 2))",
    "garbage outside root",
])
def test_rejects_corrupted_native_kicad_expressions(tmp_path, content):
    path = tmp_path / "corrupt.kicad_pcb"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError):
        inspect_kicad_native(path)


def test_rejects_invalid_utf8_kicad_file(tmp_path):
    path = tmp_path / "invalid-encoding.kicad_sch"
    path.write_bytes(b"(kicad_sch \xff)")
    with pytest.raises(ValueError, match="valid UTF-8"):
        inspect_kicad_native(path)


def test_parser_rejects_trailing_data_after_root():
    with pytest.raises(ValueError):
        parse_sexpr("(kicad_pcb (version 1)) trailing")
