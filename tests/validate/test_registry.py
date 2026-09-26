"""W4: the code registry ``khg-codes/1.1.0`` (Q013 since 1.1.0, ruling 23) and the pipelines (DESIGN §8.1)."""
from __future__ import annotations

import pytest

from khg_contracts import data
from khg_contracts.validate import KINDS, PIPELINES, Registry, layers, pipeline_letters, registry
from khg_contracts.validate.registry import Code, layer_of

RESERVED = ["KHG-D004", "KHG-D006", "KHG-S008", "KHG-S012", "KHG-P006", "KHG-P015"]


def test_the_registry_counts_as_the_design_states():
    reg = registry()
    assert reg.format == "khg-codes/1.1.0"
    assert len(reg) == 135 and len(reg.active()) == 129
    assert sorted(reg.reserved()) == sorted(RESERVED)
    assert len(reg.planned()) == 31
    assert all(not reg.is_planned(c) for c in reg) and all(p.code not in reg for p in reg.planned())
    assert reg is registry()  # loaded once


def test_every_code_has_its_letter_as_layer_and_a_known_severity():
    reg = registry()
    for code in reg:
        entry = reg[code]
        assert isinstance(entry, Code) and entry.code == code
        assert entry.layer == layer_of(code) == code[4]
        assert entry.severity in ("error", "warning", "info")
        assert entry.status in ("active", "reserved") and entry.active == (entry.status == "active")
        assert entry.meaning
    assert [c.code for c in reg.codes(layer="V")] == ["KHG-V001"]
    assert reg.severity("KHG-L008") == "warning" and reg.severity("KHG-F006") == "info"
    assert reg.get("KHG-S017") is None and reg.is_planned("KHG-S017")  # planned for 1.1, not registered


def test_the_planned_codes_are_the_ones_of_later_versions():
    planned = {p.code for p in registry().planned()}
    want = {"KHG-S017", "KHG-L009", "KHG-L110"} | {f"KHG-L{i:03d}" for i in range(1, 8)} | \
        {f"KHG-L{i:03d}" for i in range(101, 109)} | {f"KHG-F{i:03d}" for i in (1, 2, 3, 4, 5)} | \
        {f"KHG-F{i:03d}" for i in range(7, 15)}
    assert planned == want
    assert all(p.status == "planned" and p.version.startswith("1.1") for p in registry().planned())


def test_layer_of_refuses_what_is_not_a_code():
    assert layer_of("KHG-Q012") == "Q"
    for bad in ("KHG-q012", "KHG-Q12", "Q012", "KHG-QQ12", None, 12):
        with pytest.raises(ValueError):
            layer_of(bad)  # type: ignore[arg-type]


def test_the_layers_and_the_layer_rule_are_listed():
    reg = registry()
    assert reg.layer_order == ("J", "V", "H", "R", "P", "D", "C", "S", "M", "Q", "I", "L", "F")
    assert "earliest letter" in reg.layer_rule and "J and V findings stop later layers" in reg.layer_rule


def test_the_static_table_lists_every_layer_letter_once_and_d_twice():
    letters = [s.letter for s in layers.LAYERS]
    assert sorted(set(letters)) == sorted("JVHRPDCSMQI")
    assert letters.count("D") == 2 and len(letters) == 12
    owners = {s.name: s.owner for s in layers.LAYERS}
    assert owners == {"j": "W4", "v": "W4", "h": "W6", "r": "W6", "p": "W6", "d_decode": "W6",
                      "d_container": "W5", "c": "W4", "s": "W4", "m": "W4", "q": "W9", "i": "W11a"}
    for s in layers.LAYERS:
        module = layers.module(s.name)
        assert (module.LETTER, module.OWNER) == (s.letter, s.owner)
        assert callable(module.run) and isinstance(module.IMPLEMENTED, bool)
    assert {s.name for s in layers.LAYERS if layers.implemented(s.name)} >= {"j", "v", "c", "s", "m"}


@pytest.mark.parametrize("kind", KINDS)
def test_the_pipelines_are_the_registry_pipelines(kind):
    """The modules of each kind, with repeats of a letter dropped, spell the registry's pipeline."""
    reg = registry()
    assert pipeline_letters(kind) == layers.letters(kind) == reg.pipelines[layers.REGISTRY_PIPELINE[kind]]
    assert PIPELINES[kind][0] == "j"
    assert set(PIPELINES[kind]) <= {s.name for s in layers.LAYERS}


def test_the_hif_pipeline_decodes_before_c_and_s_and_checks_d_after():
    assert PIPELINES["hif"] == ("j", "v", "h", "r", "p", "d_decode", "c", "s", "d_container")
    assert pipeline_letters("hif") == ("J", "V", "H", "R", "P", "D", "C", "S")
    assert pipeline_letters("c1") == pipeline_letters("container") == ("J", "V", "C", "S", "D")
    assert pipeline_letters("relation-schema") == ("J", "V", "M") and pipeline_letters("c4") == ("J", "V", "I")
    assert pipeline_letters("json") == ("J",) and pipeline_letters(None) == ("J",)


def test_a_registry_with_another_format_is_refused():
    for fmt in ("khg-codes/2.0.0", "khg-codes/1.2.0", "khg-codes/1.0", None):
        doc = dict(data.load_json("error-codes.json"), format=fmt)
        with pytest.raises(ValueError):
            Registry(doc)
    assert Registry(dict(data.load_json("error-codes.json"), format="khg-codes/1.0.3")).format == "khg-codes/1.0.3"
