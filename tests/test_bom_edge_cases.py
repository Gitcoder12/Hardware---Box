import pytest

from hardware_box.bom import bom_rows


def test_bom_rejects_missing_components_list():
    with pytest.raises(ValueError, match="components list"):
        bom_rows({"name": "controller"})


@pytest.mark.parametrize("component,expected", [
    ({"quantity": 1}, ".name is required"),
    ({"name": "Resistor"}, ".quantity must be a positive integer"),
    ({"name": "Resistor", "quantity": 0}, ".quantity must be a positive integer"),
    ({"name": "Resistor", "quantity": True}, ".quantity must be a positive integer"),
    ({"name": "Resistor", "quantity": 1, "specifications": []}, ".specifications must be an object"),
])
def test_bom_rejects_missing_or_invalid_component_fields(component, expected):
    with pytest.raises(ValueError, match=expected):
        bom_rows({"components": [component]})


def test_bom_allows_explicit_empty_component_list():
    assert bom_rows({"components": []}) == []
