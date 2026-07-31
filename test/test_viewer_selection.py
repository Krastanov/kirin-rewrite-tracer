from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import pytest
from browser_harness import BrowserHarness
from selenium.webdriver import ActionChains, Chrome
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from viewer_fixtures import (
    HANDOFF_IDS,
    SELECTION_IDS,
    VIEWER_HOSTILE,
    EventSpec,
    event_trace,
    facts_trace,
    handoff_trace,
    selection_trace,
)

from kirin_rewrite_tracer import Trace, export_html
from kirin_rewrite_tracer._model import StyleRecord, StyleSpan


def _open_trace(
    headed_chrome: BrowserHarness,
    tmp_path: Path,
    trace: Trace,
    name: str,
) -> Chrome:
    source = export_html(trace, tmp_path / f"{name}.html")
    relocated = tmp_path / f"{name}-relocated"
    relocated.mkdir()
    headed_chrome.open_relocated(source, relocated)
    return headed_chrome.driver


def _state(driver: Chrome) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        driver.execute_script(
            """
            const tree = document.getElementById("event-tree");
            const rows = Array.from(tree.querySelectorAll("li[data-event-id]"));
            const selectedFacts = document.getElementById("selected-facts");
            const active = document.activeElement;
            return {
              frontier: tree.dataset.frontier
                ? tree.dataset.frontier.split(" ")
                : [],
              anchor: tree.dataset.anchor || null,
              visible: rows.filter(row => !row.hidden)
                .map(row => row.dataset.eventId),
              hidden: rows.filter(row => row.hidden)
                .map(row => row.dataset.eventId),
              selected: Array.from(
                tree.querySelectorAll('.event-button[aria-current="true"]')
              ).map(button => button.dataset.eventId),
              columnRoles: Array.from(
                document.querySelectorAll(".state-column")
              ).map(column => column.dataset.roles),
              columnKeys: Array.from(
                document.querySelectorAll(".state-column")
              ).map(column => column.dataset.columnKey),
              columnHeadings: Array.from(
                document.querySelectorAll(".state-column h2")
              ).map(heading => heading.textContent),
              sharedColumns:
                document.querySelectorAll(".shared-state-column").length,
              absentColumns:
                document.querySelectorAll(".absent-state-column").length,
              facts: selectedFacts.hidden
                ? null
                : JSON.parse(selectedFacts.textContent),
              factsEmpty:
                document.getElementById("facts-empty").textContent,
              status: document.getElementById("selection-status").textContent,
              focusedEvent: active?.classList.contains("event-button")
                ? active.dataset.eventId
                : null,
              clearFocused: active?.classList.contains("clear-selection") || false,
              payloadText: document.getElementById("trace-data").textContent,
              canonicalText: JSON.stringify(trace),
              pwned: Object.prototype.hasOwnProperty.call(
                globalThis, "viewerPwned"
              )
            };
            """
        ),
    )


def _activate(
    driver: Chrome,
    event_id: str,
    *,
    shift: bool = False,
    control: bool = False,
    meta: bool = False,
) -> None:
    button = driver.find_element(
        By.CSS_SELECTOR, f'.event-button[data-event-id="{event_id}"]'
    )
    if not (shift or control or meta):
        button.click()
        return
    actions = ActionChains(driver)
    modifiers: list[str] = []
    if shift:
        modifiers.append(Keys.SHIFT)
    if control:
        modifiers.append(Keys.CONTROL)
    if meta:
        modifiers.append(Keys.META)
    for modifier in modifiers:
        actions.key_down(modifier)
    actions.click(button)
    for modifier in reversed(modifiers):
        actions.key_up(modifier)
    actions.perform()


def _clear(driver: Chrome) -> None:
    driver.find_element(By.CSS_SELECTOR, ".clear-selection").click()


@pytest.mark.browser  # type: ignore[untyped-decorator]
def test_pre_action_ranges_parent_dominance_and_anchor_rebase(
    headed_chrome: BrowserHarness,
    tmp_path: Path,
) -> None:
    driver = _open_trace(headed_chrome, tmp_path, selection_trace(), "selection-ranges")
    all_events = [
        SELECTION_IDS[label] for label in ("R9", "C4", "G8", "C1", "S7", "D2", "T0")
    ]

    assert _state(driver) | {"payloadText": "", "canonicalText": ""} == {
        "frontier": [],
        "anchor": None,
        "visible": all_events,
        "hidden": [],
        "selected": [],
        "columnRoles": [],
        "columnKeys": [],
        "columnHeadings": [],
        "sharedColumns": 0,
        "absentColumns": 0,
        "facts": None,
        "factsEmpty": "No event selected.",
        "status": "Selected: 0; hidden: 0.",
        "focusedEvent": None,
        "clearFocused": False,
        "payloadText": "",
        "canonicalText": "",
        "pwned": False,
    }

    _activate(driver, SELECTION_IDS["T0"], shift=True)
    state = _state(driver)
    assert (state["frontier"], state["anchor"]) == (
        [SELECTION_IDS["T0"]],
        SELECTION_IDS["T0"],
    )

    _activate(driver, SELECTION_IDS["G8"])
    _activate(driver, SELECTION_IDS["D2"], shift=True)
    state = _state(driver)
    assert state["frontier"] == [
        SELECTION_IDS["G8"],
        SELECTION_IDS["C1"],
        SELECTION_IDS["S7"],
    ]
    assert state["anchor"] == SELECTION_IDS["G8"]
    assert SELECTION_IDS["D2"] in state["hidden"]
    assert state["focusedEvent"] == SELECTION_IDS["S7"]

    _activate(driver, SELECTION_IDS["G8"], shift=True)
    state = _state(driver)
    assert state["frontier"] == [SELECTION_IDS["G8"]]
    assert state["anchor"] == SELECTION_IDS["G8"]

    _activate(driver, SELECTION_IDS["D2"], shift=True)
    _activate(driver, SELECTION_IDS["C1"])
    selected_member = _state(driver)
    _activate(driver, SELECTION_IDS["C1"])
    repeated_member = _state(driver)
    assert (
        selected_member["frontier"]
        == repeated_member["frontier"]
        == [SELECTION_IDS["C1"]]
    )
    assert selected_member["anchor"] == repeated_member["anchor"] == SELECTION_IDS["C1"]

    _activate(driver, SELECTION_IDS["G8"])
    _activate(driver, SELECTION_IDS["D2"], shift=True)
    _activate(driver, SELECTION_IDS["C1"], shift=True)
    state = _state(driver)
    assert state["frontier"] == [SELECTION_IDS["G8"], SELECTION_IDS["C1"]]
    assert state["anchor"] == SELECTION_IDS["G8"]
    assert SELECTION_IDS["D2"] in state["visible"]
    assert SELECTION_IDS["D2"] not in state["selected"]

    _activate(driver, SELECTION_IDS["G8"])
    _activate(driver, SELECTION_IDS["C4"], shift=True)
    state = _state(driver)
    assert state["frontier"] == [SELECTION_IDS["C4"]]
    assert state["anchor"] == SELECTION_IDS["C4"]
    assert SELECTION_IDS["G8"] in state["hidden"]

    _activate(driver, SELECTION_IDS["S7"], shift=True)
    state = _state(driver)
    assert state["frontier"] == [
        SELECTION_IDS["C4"],
        SELECTION_IDS["C1"],
        SELECTION_IDS["S7"],
    ]
    assert state["anchor"] == SELECTION_IDS["C4"]

    _clear(driver)
    _activate(driver, SELECTION_IDS["G8"])
    _activate(driver, SELECTION_IDS["R9"], shift=True)
    state = _state(driver)
    assert state["frontier"] == [SELECTION_IDS["R9"]]
    assert state["anchor"] == SELECTION_IDS["R9"]
    assert state["focusedEvent"] == SELECTION_IDS["R9"]
    assert state["columnRoles"] == [
        f"{SELECTION_IDS['R9']}.before",
        f"{SELECTION_IDS['R9']}.after",
    ]
    assert state["absentColumns"] == 1


@pytest.mark.browser  # type: ignore[untyped-decorator]
@pytest.mark.parametrize("modifier", ["control", "meta"])  # type: ignore[untyped-decorator]
def test_non_toggle_modifiers_drag_and_clear_reset_anchor(
    headed_chrome: BrowserHarness,
    tmp_path: Path,
    modifier: str,
) -> None:
    driver = _open_trace(
        headed_chrome,
        tmp_path,
        selection_trace(),
        f"selection-modifier-{modifier}",
    )
    modifier_arguments = {modifier: True}

    _activate(driver, SELECTION_IDS["G8"])
    _activate(driver, SELECTION_IDS["D2"], shift=True)
    assert len(_state(driver)["frontier"]) == 3

    _activate(driver, SELECTION_IDS["T0"], **modifier_arguments)
    first = _state(driver)
    _activate(driver, SELECTION_IDS["T0"], **modifier_arguments)
    second = _state(driver)
    assert first["frontier"] == second["frontier"] == [SELECTION_IDS["T0"]]
    assert first["anchor"] == second["anchor"] == SELECTION_IDS["T0"]

    _activate(driver, SELECTION_IDS["G8"])
    _activate(
        driver,
        SELECTION_IDS["D2"],
        shift=True,
        **modifier_arguments,
    )
    assert _state(driver)["frontier"] == [
        SELECTION_IDS["G8"],
        SELECTION_IDS["C1"],
        SELECTION_IDS["S7"],
    ]

    before_drag = _state(driver)
    driver.execute_script(
        """
        const button = document.querySelector(
          '.event-button[data-event-id="' + arguments[0] + '"]'
        );
        for (const type of ["pointermove", "dragstart", "drag", "dragend"]) {
          button.dispatchEvent(new Event(type, {bubbles: true}));
        }
        """,
        SELECTION_IDS["T0"],
    )
    after_drag = _state(driver)
    assert after_drag["frontier"] == before_drag["frontier"]
    assert after_drag["anchor"] == before_drag["anchor"]

    _clear(driver)
    cleared = _state(driver)
    assert cleared["frontier"] == []
    assert cleared["anchor"] is None
    assert cleared["visible"] == [
        SELECTION_IDS[label] for label in ("R9", "C4", "G8", "C1", "S7", "D2", "T0")
    ]
    assert cleared["columnRoles"] == []
    assert cleared["facts"] is None
    assert cleared["clearFocused"] is True

    _clear(driver)
    assert _state(driver)["clearFocused"] is True
    _activate(driver, SELECTION_IDS["C1"], shift=True)
    reset = _state(driver)
    assert reset["frontier"] == [SELECTION_IDS["C1"]]
    assert reset["anchor"] == SELECTION_IDS["C1"]


@pytest.mark.browser  # type: ignore[untyped-decorator]
def test_hidden_descendants_leave_no_accessibility_target_and_restore_cleanly(
    headed_chrome: BrowserHarness,
    tmp_path: Path,
) -> None:
    driver = _open_trace(headed_chrome, tmp_path, selection_trace(), "selection-hidden")
    _activate(driver, SELECTION_IDS["R9"])

    state = _state(driver)
    assert state["hidden"] == [SELECTION_IDS["C4"], SELECTION_IDS["G8"]]
    tree = headed_chrome.accessibility_tree()
    visible_button_names = {
        node.name
        for node in tree.nodes
        if node.role == "button" and node.name is not None
    }
    assert not any("C4" in name or "G8" in name for name in visible_button_names)

    hidden_activation = cast(
        dict[str, object],
        driver.execute_script(
            """
            const beforeColumn = document.querySelector(".state-column");
            const beforeFacts = document.getElementById("selected-facts").textContent;
            document.querySelector(
              '.event-button[data-event-id="' + arguments[0] + '"]'
            ).click();
            return {
              sameColumn:
                beforeColumn === document.querySelector(".state-column"),
              sameFacts:
                beforeFacts ===
                document.getElementById("selected-facts").textContent,
              frontier: document.getElementById("event-tree").dataset.frontier,
              anchor: document.getElementById("event-tree").dataset.anchor
            };
            """,
            SELECTION_IDS["G8"],
        ),
    )
    assert hidden_activation == {
        "sameColumn": True,
        "sameFacts": True,
        "frontier": SELECTION_IDS["R9"],
        "anchor": SELECTION_IDS["R9"],
    }

    _activate(driver, SELECTION_IDS["C1"])
    restored = _state(driver)
    assert restored["hidden"] == []
    assert restored["selected"] == [SELECTION_IDS["C1"]]
    assert restored["visible"] == [
        SELECTION_IDS[label] for label in ("R9", "C4", "G8", "C1", "S7", "D2", "T0")
    ]


@pytest.mark.browser  # type: ignore[untyped-decorator]
def test_exact_handoffs_are_boundary_only_nontransitive_and_absence_is_barrier(
    headed_chrome: BrowserHarness,
    tmp_path: Path,
) -> None:
    driver = _open_trace(headed_chrome, tmp_path, handoff_trace(), "selection-handoffs")

    _activate(driver, HANDOFF_IDS["A"])
    _activate(driver, HANDOFF_IDS["C"], shift=True)
    state = _state(driver)
    assert state["columnRoles"] == [
        f"{HANDOFF_IDS['A']}.before",
        f"{HANDOFF_IDS['A']}.after|{HANDOFF_IDS['B']}.before",
        f"{HANDOFF_IDS['B']}.after|{HANDOFF_IDS['C']}.before",
        f"{HANDOFF_IDS['C']}.after",
    ]
    assert state["sharedColumns"] == 2
    assert len(set(state["columnKeys"][1:3])) == 2
    assert state["columnHeadings"][1].startswith("Shared by exact equality:")

    _activate(driver, HANDOFF_IDS["B"])
    state = _state(driver)
    assert state["columnRoles"] == [
        f"{HANDOFF_IDS['B']}.before",
        f"{HANDOFF_IDS['B']}.after",
    ]
    assert state["sharedColumns"] == 0

    _activate(driver, HANDOFF_IDS["D"])
    _activate(driver, HANDOFF_IDS["E"], shift=True)
    state = _state(driver)
    assert state["columnRoles"] == [
        f"{HANDOFF_IDS['D']}.before",
        f"{HANDOFF_IDS['D']}.after",
        f"{HANDOFF_IDS['E']}.before",
        f"{HANDOFF_IDS['E']}.after",
    ]
    assert state["sharedColumns"] == 0
    assert state["absentColumns"] == 1

    _activate(driver, HANDOFF_IDS["F"])
    _activate(driver, HANDOFF_IDS["G"], shift=True)
    state = _state(driver)
    assert state["columnRoles"] == [
        f"{HANDOFF_IDS['F']}.before",
        f"{HANDOFF_IDS['F']}.after|{HANDOFF_IDS['G']}.before",
        f"{HANDOFF_IDS['G']}.after",
    ]
    assert state["sharedColumns"] == 1
    assert state["absentColumns"] == 1


def _styled_boundary_trace(*, equivalent: bool) -> Trace:
    trace = event_trace(
        (
            EventSpec("Left", None, "left", "same"),
            EventSpec("Right", None, "same", "right"),
        )
    )
    second_style = (
        replace(trace.styles[0], id="style-1")
        if equivalent
        else StyleRecord("style-1", bold=True)
    )
    right_before = replace(
        trace.snapshots[2],
        style_spans=(
            StyleSpan(0, 2, "style-1"),
            StyleSpan(2, len(trace.snapshots[2].text), "style-1"),
        ),
    )
    return replace(
        trace,
        styles=(trace.styles[0], second_style),
        snapshots=(*trace.snapshots[:2], right_before, trace.snapshots[3]),
    )


@pytest.mark.browser  # type: ignore[untyped-decorator]
@pytest.mark.parametrize("equivalent", [True, False])  # type: ignore[untyped-decorator]
def test_browser_handoff_uses_python_normalized_semantic_class(
    headed_chrome: BrowserHarness,
    tmp_path: Path,
    equivalent: bool,
) -> None:
    driver = _open_trace(
        headed_chrome,
        tmp_path,
        _styled_boundary_trace(equivalent=equivalent),
        f"selection-style-{equivalent}",
    )
    _activate(driver, "event-0")
    _activate(driver, "event-1", shift=True)

    state = _state(driver)

    assert state["sharedColumns"] == (1 if equivalent else 0)
    assert len(state["columnRoles"]) == (3 if equivalent else 4)


@pytest.mark.browser  # type: ignore[untyped-decorator]
def test_selected_facts_use_exact_owner_closure_and_dedupe_canonical_records(
    headed_chrome: BrowserHarness,
    tmp_path: Path,
) -> None:
    driver = _open_trace(headed_chrome, tmp_path, facts_trace(), "selection-facts")
    initial_state = _state(driver)
    initial_payload = initial_state["payloadText"]
    initial_canonical = initial_state["canonicalText"]

    _activate(driver, "event-0")
    parent_state = _state(driver)
    parent = parent_state["facts"]
    assert parent["selected_event_ids"] == ["event-0"]
    assert parent["inventories"] == [
        {
            "event_id": "event-0",
            "before_snapshot_id": "snapshot-0",
            "after_snapshot_id": "snapshot-1",
            "configuration_ids": ["configuration-0"],
            "style_ids": ["style-0"],
            "entity_ids": ["entity-0", "entity-1", "entity-7"],
            "snapshot_ids": ["snapshot-0", "snapshot-1"],
            "occurrence_ids": [
                "occurrence-0",
                "occurrence-1",
                "occurrence-2",
                "occurrence-3",
            ],
            "metadata_ids": [
                "metadata-0",
                "metadata-1",
                "metadata-2",
                "metadata-3",
                "metadata-4",
                "metadata-5",
            ],
            "stack_ids": ["stack-0", "stack-2"],
            "operation_ids": ["operation-0"],
            "relation_ids": [],
            "effect_ids": ["effect-0"],
        }
    ]
    assert [item["id"] for item in parent["canonical"]["events"]] == ["event-0"]
    assert [item["id"] for item in parent["canonical"]["operations"]] == ["operation-0"]
    assert [item["id"] for item in parent["canonical"]["effects"]] == ["effect-0"]
    assert parent["canonical"]["relations"] == []
    assert parent_state["hidden"] == ["event-1"]
    assert "configuration-1" not in json.dumps(parent)
    assert "style-1" not in json.dumps(parent)
    assert "ChildRule" not in json.dumps(parent)

    _clear(driver)
    _activate(driver, "event-1")
    child = _state(driver)["facts"]
    assert child["selected_event_ids"] == ["event-1"]
    assert child["inventories"][0]["after_snapshot_id"] is None
    assert child["inventories"][0]["configuration_ids"] == ["configuration-1"]
    assert child["inventories"][0]["style_ids"] == ["style-1"]
    assert child["inventories"][0]["operation_ids"] == [
        "operation-1",
        "operation-2",
        "operation-3",
    ]
    assert child["inventories"][0]["relation_ids"] == ["relation-0"]
    assert child["inventories"][0]["effect_ids"] == ["effect-1"]
    assert child["inventories"][0]["entity_ids"] == [
        "entity-2",
        "entity-3",
        "entity-1",
        "entity-5",
        "entity-6",
        "entity-0",
        "entity-4",
    ]
    assert [item["id"] for item in child["canonical"]["entities"]] == [
        "entity-0",
        "entity-1",
        "entity-2",
        "entity-3",
        "entity-4",
        "entity-5",
        "entity-6",
    ]
    assert [item["id"] for item in child["canonical"]["occurrences"]] == [
        "occurrence-4",
        "occurrence-5",
    ]
    assert [item["id"] for item in child["canonical"]["metadata"]] == [
        "metadata-6",
        "metadata-7",
        "metadata-8",
    ]
    assert child["canonical"]["events"][0]["after_snapshot_id"] is None
    assert child["canonical"]["events"][0]["result"] is None
    assert "parent metadata" not in json.dumps(child)

    _activate(driver, "event-2", shift=True)
    multiple = _state(driver)["facts"]
    assert multiple["selected_event_ids"] == ["event-1", "event-2"]
    assert [item["event_id"] for item in multiple["inventories"]] == [
        "event-1",
        "event-2",
    ]
    for records in multiple["canonical"].values():
        identifiers = [record["id"] for record in records]
        assert identifiers == list(dict.fromkeys(identifiers))
    assert [item["id"] for item in multiple["canonical"]["entities"]] == [
        f"entity-{index}" for index in range(7)
    ]

    final_state = _state(driver)
    assert final_state["payloadText"] == initial_payload
    assert final_state["canonicalText"] == initial_canonical
    assert final_state["pwned"] is False
    assert VIEWER_HOSTILE in driver.find_element(By.TAG_NAME, "body").text
    observations = headed_chrome.observations()
    assert observations.page_network_requests() == ()
    assert observations.csp_violations == ()
