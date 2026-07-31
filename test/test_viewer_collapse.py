from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
from browser_harness import BrowserHarness
from selenium.webdriver import ActionChains, Chrome
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from viewer_fixtures import SELECTION_IDS, selection_trace

from kirin_rewrite_tracer import Trace, export_html

_ALL_LABELS = ("R9", "C4", "G8", "C1", "S7", "D2", "T0")
_BRANCH_LABELS = ("R9", "C4", "S7")


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


def _identifiers(*labels: str) -> list[str]:
    return [SELECTION_IDS[label] for label in labels]


def _toggle_element(driver: Chrome, label: str) -> WebElement:
    return driver.find_element(
        By.CSS_SELECTOR,
        f'.event-collapse[data-event-id="{SELECTION_IDS[label]}"]',
    )


def _event_button(driver: Chrome, label: str) -> WebElement:
    return driver.find_element(
        By.CSS_SELECTOR,
        f'.event-button[data-event-id="{SELECTION_IDS[label]}"]',
    )


def _state(driver: Chrome) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        driver.execute_script(
            """
            const tree = document.getElementById("event-tree");
            const rows = Array.from(tree.querySelectorAll("li[data-event-id]"));
            const toggles = Array.from(tree.querySelectorAll(".event-collapse"));
            const active = document.activeElement;
            return {
              visible: rows.filter(row => !row.hidden)
                .map(row => row.dataset.eventId),
              hidden: rows.filter(row => row.hidden)
                .map(row => row.dataset.eventId),
              frontier: tree.dataset.frontier
                ? tree.dataset.frontier.split(" ")
                : [],
              anchor: tree.dataset.anchor || null,
              collapsed: tree.dataset.collapsed
                ? tree.dataset.collapsed.split(" ")
                : [],
              toggles: toggles.map(toggle => ({
                event: toggle.dataset.eventId,
                disabled: toggle.disabled,
                expanded: toggle.getAttribute("aria-expanded"),
                collapsedFlag: toggle.dataset.collapsed,
                label: toggle.getAttribute("aria-label"),
                marker: toggle.textContent,
                controls: toggle.getAttribute("aria-controls")
              })),
              status: document.getElementById("selection-status").textContent,
              columnRoles: Array.from(
                document.querySelectorAll(".state-column")
              ).map(column => column.dataset.roles),
              facts: document.getElementById("selected-facts").hidden
                ? null
                : document.getElementById("selected-facts").textContent,
              sequential: Array.from(
                document.querySelectorAll(
                  'a[href], button, [tabindex]:not([tabindex="-1"])'
                )
              ).filter(control =>
                !control.hidden &&
                control.closest("[hidden]") === null &&
                !control.disabled &&
                control.tabIndex >= 0
              ).map(control =>
                `${control.className}:${control.dataset.eventId || ""}`
              ),
              activeControl: active === null
                ? null
                : `${active.className}:${active.dataset.eventId || ""}`
            };
            """
        ),
    )


def _toggle_states(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        cast(str, entry["event"]): entry
        for entry in cast(list[dict[str, Any]], state["toggles"])
    }


def _expected_toggle(
    label: str,
    *,
    collapsed: bool,
    disabled: bool,
    controls: str,
) -> dict[str, Any]:
    action = "Expand" if collapsed else "Collapse"
    availability = (
        "; unavailable while its subtree contains a selected event" if disabled else ""
    )
    return {
        "event": SELECTION_IDS[label],
        "disabled": disabled,
        "expanded": "false" if collapsed else "true",
        "collapsedFlag": "true" if collapsed else "false",
        "label": f"{action} event {SELECTION_IDS[label]} children{availability}.",
        "marker": "\N{BLACK RIGHT-POINTING SMALL TRIANGLE}"
        if collapsed
        else "\N{BLACK DOWN-POINTING SMALL TRIANGLE}",
        "controls": controls,
    }


def _install_column_observer(driver: Chrome) -> None:
    driver.execute_script(
        """
        globalThis.__krtColumnObserver?.disconnect();
        globalThis.__krtColumnMutations = 0;
        globalThis.__krtColumnObserver = new MutationObserver(records => {
          globalThis.__krtColumnMutations += records.length;
        });
        globalThis.__krtColumnObserver.observe(
          document.getElementById("ssa-columns"),
          {childList: true, subtree: true}
        );
        """
    )


def _column_mutations(driver: Chrome) -> int:
    return cast(int, driver.execute_script("return globalThis.__krtColumnMutations;"))


@pytest.mark.browser  # type: ignore[untyped-decorator]
def test_only_non_leaf_rows_expose_one_expanded_collapse_toggle(
    headed_chrome: BrowserHarness,
    tmp_path: Path,
) -> None:
    driver = _open_trace(headed_chrome, tmp_path, selection_trace(), "collapse-shape")
    state = _state(driver)
    controls = {
        entry["event"]: entry["controls"]
        for entry in cast(list[dict[str, Any]], state["toggles"])
    }

    assert [entry["event"] for entry in state["toggles"]] == _identifiers(
        *_BRANCH_LABELS
    )
    assert state["collapsed"] == []
    assert state["visible"] == _identifiers(*_ALL_LABELS)
    assert _toggle_states(state) == {
        SELECTION_IDS[label]: _expected_toggle(
            label,
            collapsed=False,
            disabled=False,
            controls=cast(str, controls[SELECTION_IDS[label]]),
        )
        for label in _BRANCH_LABELS
    }

    subtrees = cast(
        dict[str, list[str]],
        driver.execute_script(
            """
            return Object.fromEntries(
              Array.from(
                document.querySelectorAll(".event-collapse")
              ).map(toggle => [
                toggle.dataset.eventId,
                Array.from(
                  document.getElementById(
                    toggle.getAttribute("aria-controls")
                  ).querySelectorAll("li[data-event-id]")
                ).map(row => row.dataset.eventId)
              ])
            );
            """
        ),
    )
    assert subtrees == {
        SELECTION_IDS["R9"]: _identifiers("C4", "G8"),
        SELECTION_IDS["C4"]: _identifiers("G8"),
        SELECTION_IDS["S7"]: _identifiers("D2"),
    }

    leaf_toggles = cast(
        list[str],
        driver.execute_script(
            """
            return Array.from(
              document.querySelectorAll("li[data-event-id]")
            ).filter(row =>
              row.querySelector(":scope > .event-row > .event-collapse") !== null &&
              row.querySelector(":scope > ol") === null
            ).map(row => row.dataset.eventId);
            """
        ),
    )
    assert leaf_toggles == []

    accessibility = headed_chrome.accessibility_tree()
    for label in _BRANCH_LABELS:
        assert (
            len(
                accessibility.matching(
                    role="button",
                    name=f"Collapse event {SELECTION_IDS[label]} children.",
                )
            )
            == 1
        )
    assert not any(
        node.role in {"tree", "treegrid", "grid", "dialog"}
        for node in accessibility.nodes
    )

    assert state["sequential"] == [
        "skip-link:",
        "clear-selection:",
        f"event-collapse:{SELECTION_IDS['R9']}",
        f"event-button:{SELECTION_IDS['R9']}",
        f"event-collapse:{SELECTION_IDS['C4']}",
        f"event-button:{SELECTION_IDS['C4']}",
        f"event-button:{SELECTION_IDS['G8']}",
        f"event-button:{SELECTION_IDS['C1']}",
        f"event-collapse:{SELECTION_IDS['S7']}",
        f"event-button:{SELECTION_IDS['S7']}",
        f"event-button:{SELECTION_IDS['D2']}",
        f"event-button:{SELECTION_IDS['T0']}",
    ]


@pytest.mark.browser  # type: ignore[untyped-decorator]
def test_collapse_hides_the_whole_subtree_and_retains_nested_state(
    headed_chrome: BrowserHarness,
    tmp_path: Path,
) -> None:
    driver = _open_trace(headed_chrome, tmp_path, selection_trace(), "collapse-subtree")
    _install_column_observer(driver)

    _toggle_element(driver, "R9").click()
    collapsed_root = _state(driver)
    assert collapsed_root["collapsed"] == _identifiers("R9")
    assert collapsed_root["visible"] == _identifiers("R9", "C1", "S7", "D2", "T0")
    assert collapsed_root["hidden"] == _identifiers("C4", "G8")
    assert collapsed_root["status"] == "Selected: 0; hidden: 2."
    assert collapsed_root["frontier"] == []
    assert collapsed_root["columnRoles"] == []
    assert collapsed_root["facts"] is None
    assert collapsed_root["activeControl"] == f"event-collapse:{SELECTION_IDS['R9']}"
    assert _column_mutations(driver) == 0

    hidden_tree = headed_chrome.accessibility_tree()
    for label in ("C4", "G8"):
        name = _event_button(driver, label).get_attribute("textContent")
        assert hidden_tree.matching(role="button", name=cast(str, name)) == ()
    assert f"event-collapse:{SELECTION_IDS['C4']}" not in collapsed_root["sequential"]
    assert _toggle_states(collapsed_root)[SELECTION_IDS["R9"]] == _expected_toggle(
        "R9",
        collapsed=True,
        disabled=False,
        controls=cast(
            str,
            _toggle_element(driver, "R9").get_attribute("aria-controls"),
        ),
    )

    _toggle_element(driver, "R9").click()
    _toggle_element(driver, "C4").click()
    nested = _state(driver)
    assert nested["collapsed"] == _identifiers("C4")
    assert nested["visible"] == _identifiers("R9", "C4", "C1", "S7", "D2", "T0")
    assert nested["hidden"] == _identifiers("G8")

    _toggle_element(driver, "R9").click()
    both = _state(driver)
    assert both["collapsed"] == _identifiers("R9", "C4")
    assert both["hidden"] == _identifiers("C4", "G8")
    assert both["status"] == "Selected: 0; hidden: 2."

    _toggle_element(driver, "R9").click()
    retained = _state(driver)
    assert retained["collapsed"] == _identifiers("C4")
    assert retained["hidden"] == _identifiers("G8")
    assert _toggle_states(retained)[SELECTION_IDS["C4"]]["expanded"] == "false"
    assert _toggle_states(retained)[SELECTION_IDS["R9"]]["expanded"] == "true"

    _toggle_element(driver, "R9").click()
    driver.execute_script("toggleEventCollapse(arguments[0]);", SELECTION_IDS["C4"])
    unreachable = _state(driver)
    assert unreachable["collapsed"] == _identifiers("R9", "C4")
    assert unreachable["hidden"] == _identifiers("C4", "G8")

    _toggle_element(driver, "R9").click()
    _toggle_element(driver, "C4").click()
    restored = _state(driver)
    assert restored["collapsed"] == []
    assert restored["visible"] == _identifiers(*_ALL_LABELS)
    assert restored["hidden"] == []
    assert restored["status"] == "Selected: 0; hidden: 0."
    assert _column_mutations(driver) == 0

    observations = headed_chrome.observations()
    assert observations.page_network_requests() == ()
    assert observations.csp_violations == ()
    assert observations.console == ()


@pytest.mark.browser  # type: ignore[untyped-decorator]
def test_toggle_is_enabled_only_with_no_selected_event_downstream(
    headed_chrome: BrowserHarness,
    tmp_path: Path,
) -> None:
    driver = _open_trace(
        headed_chrome,
        tmp_path,
        selection_trace(),
        "collapse-eligibility",
    )

    _event_button(driver, "G8").click()
    descendant_selected = _toggle_states(_state(driver))
    assert descendant_selected[SELECTION_IDS["R9"]]["disabled"] is True
    assert descendant_selected[SELECTION_IDS["C4"]]["disabled"] is True
    assert descendant_selected[SELECTION_IDS["S7"]]["disabled"] is False
    assert descendant_selected[SELECTION_IDS["R9"]]["label"] == (
        f"Collapse event {SELECTION_IDS['R9']} children; "
        "unavailable while its subtree contains a selected event."
    )

    blocked_before = _state(driver)
    driver.execute_script(
        """
        for (const eventId of arguments[0]) {
          document.querySelector(
            '.event-collapse[data-event-id="' + eventId + '"]'
          ).click();
          toggleEventCollapse(eventId);
        }
        """,
        _identifiers("R9", "C4"),
    )
    blocked_after = _state(driver)
    assert blocked_after["collapsed"] == []
    assert blocked_after["visible"] == blocked_before["visible"]
    assert blocked_after["frontier"] == blocked_before["frontier"]
    assert blocked_after["toggles"] == blocked_before["toggles"]

    assert cast(
        list[dict[str, str]],
        driver.execute_script(
            """
            return arguments[0].map(eventId => {
              const style = getComputedStyle(
                document.querySelector(
                  '.event-collapse[data-event-id="' + eventId + '"]'
                )
              );
              return {
                color: style.color,
                borderStyle: style.borderTopStyle
              };
            });
            """,
            _identifiers("R9", "S7"),
        ),
    ) == [
        {"color": "rgb(203, 213, 225)", "borderStyle": "dashed"},
        {"color": "rgb(243, 244, 246)", "borderStyle": "solid"},
    ]

    _event_button(driver, "R9").click()
    self_selected = _toggle_states(_state(driver))
    assert self_selected[SELECTION_IDS["R9"]]["disabled"] is True
    assert self_selected[SELECTION_IDS["S7"]]["disabled"] is False

    driver.find_element(By.CSS_SELECTOR, ".clear-selection").click()
    cleared = _state(driver)
    assert [entry["disabled"] for entry in cleared["toggles"]] == [False, False, False]

    _toggle_element(driver, "S7").click()
    _event_button(driver, "S7").click()
    collapsed_and_selected = _state(driver)
    assert collapsed_and_selected["collapsed"] == _identifiers("S7")
    assert collapsed_and_selected["frontier"] == _identifiers("S7")
    assert _toggle_states(collapsed_and_selected)[
        SELECTION_IDS["S7"]
    ] == _expected_toggle(
        "S7",
        collapsed=True,
        disabled=True,
        controls=cast(
            str,
            _toggle_element(driver, "S7").get_attribute("aria-controls"),
        ),
    )
    assert (
        f"event-collapse:{SELECTION_IDS['S7']}"
        not in collapsed_and_selected["sequential"]
    )


@pytest.mark.browser  # type: ignore[untyped-decorator]
def test_collapse_bounds_shift_ranges_and_survives_selection_and_clear(
    headed_chrome: BrowserHarness,
    tmp_path: Path,
) -> None:
    driver = _open_trace(
        headed_chrome,
        tmp_path,
        selection_trace(),
        "collapse-selection-interaction",
    )

    _toggle_element(driver, "S7").click()
    _event_button(driver, "C1").click()
    target = _event_button(driver, "T0")
    ActionChains(driver).key_down(Keys.SHIFT).click(target).key_up(Keys.SHIFT).perform()

    ranged = _state(driver)
    assert ranged["frontier"] == _identifiers("C1", "S7", "T0")
    assert ranged["anchor"] == SELECTION_IDS["C1"]
    assert ranged["visible"] == _identifiers("R9", "C4", "G8", "C1", "S7", "T0")
    assert ranged["hidden"] == _identifiers("D2")
    assert ranged["status"] == (
        f"Selected: 3; first: {SELECTION_IDS['C1']}; "
        f"last: {SELECTION_IDS['T0']}; hidden: 1."
    )
    assert ranged["columnRoles"] == [
        f"{SELECTION_IDS['C1']}.before",
        f"{SELECTION_IDS['C1']}.after",
        f"{SELECTION_IDS['S7']}.before",
        f"{SELECTION_IDS['S7']}.after",
        f"{SELECTION_IDS['T0']}.before",
        f"{SELECTION_IDS['T0']}.after",
    ]

    driver.find_element(By.CSS_SELECTOR, ".clear-selection").click()
    cleared = _state(driver)
    assert cleared["frontier"] == []
    assert cleared["anchor"] is None
    assert cleared["collapsed"] == _identifiers("S7")
    assert cleared["visible"] == _identifiers("R9", "C4", "G8", "C1", "S7", "T0")
    assert cleared["status"] == "Selected: 0; hidden: 1."
    assert cleared["columnRoles"] == []

    _toggle_element(driver, "S7").click()
    expanded = _state(driver)
    assert expanded["collapsed"] == []
    assert expanded["visible"] == _identifiers(*_ALL_LABELS)

    observations = headed_chrome.observations()
    assert observations.page_network_requests() == ()
    assert observations.csp_violations == ()
    assert observations.console == ()


@pytest.mark.browser  # type: ignore[untyped-decorator]
@pytest.mark.parametrize("key", [Keys.ENTER, Keys.SPACE])  # type: ignore[untyped-decorator]
def test_native_keyboard_collapse_matches_pointer_exactly_once(
    headed_chrome: BrowserHarness,
    tmp_path: Path,
    key: str,
) -> None:
    driver = _open_trace(
        headed_chrome,
        tmp_path,
        selection_trace(),
        f"collapse-keyboard-{key.encode().hex()}",
    )
    toggle = _toggle_element(driver, "R9")
    driver.execute_script(
        """
        globalThis.__krtToggleActivations = 0;
        arguments[0].addEventListener(
          "click",
          () => { globalThis.__krtToggleActivations += 1; },
          true
        );
        arguments[0].focus({preventScroll: true});
        """,
        toggle,
    )
    assert _state(driver)["collapsed"] == []

    ActionChains(driver).send_keys(key).perform()
    collapsed = _state(driver)
    assert collapsed["collapsed"] == _identifiers("R9")
    assert collapsed["hidden"] == _identifiers("C4", "G8")
    assert collapsed["activeControl"] == f"event-collapse:{SELECTION_IDS['R9']}"
    assert (
        cast(int, driver.execute_script("return globalThis.__krtToggleActivations;"))
        == 1
    )

    ActionChains(driver).send_keys(key).perform()
    expanded = _state(driver)
    assert expanded["collapsed"] == []
    assert expanded["visible"] == _identifiers(*_ALL_LABELS)
    assert (
        cast(int, driver.execute_script("return globalThis.__krtToggleActivations;"))
        == 2
    )
