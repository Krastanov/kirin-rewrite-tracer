from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
from browser_harness import BrowserHarness
from selenium.webdriver import ActionChains, Chrome
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from viewer_fixtures import EventSpec, event_trace

from kirin_rewrite_tracer import Trace, export_html

EVENT_IDS = {
    "changed": "event-0",
    "unchanged_parent": "event-1",
    "changed_child": "event-2",
    "inconsistent_equal": "event-3",
    "unchanged_leaf": "event-4",
    "inconsistent_different": "event-5",
    "incomplete": "event-6",
}


def _classification_trace() -> Trace:
    return event_trace(
        (
            EventSpec("Changed", None, "changed before", "shared"),
            EventSpec("UnchangedParent", None, "parent same", "parent same"),
            EventSpec(
                "ChangedChild",
                "UnchangedParent",
                "child before",
                "child after",
            ),
            EventSpec(
                "InconsistentEqual",
                None,
                "shared",
                "shared",
                has_done_something=True,
            ),
            EventSpec("UnchangedLeaf", None, "leaf same", "leaf same"),
            EventSpec(
                "InconsistentDifferent",
                None,
                "shared",
                "different after",
                has_done_something=False,
            ),
            EventSpec("Incomplete", None, "different after", None),
        )
    )


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


def _event_button(driver: Chrome, event_id: str) -> WebElement:
    return driver.find_element(
        By.CSS_SELECTOR,
        f'.event-button[data-event-id="{event_id}"]',
    )


def _filter_button(driver: Chrome) -> WebElement:
    return driver.find_element(By.CSS_SELECTOR, ".unchanged-filter")


def _activate(driver: Chrome, event_id: str, *, shift: bool = False) -> None:
    button = _event_button(driver, event_id)
    if not shift:
        button.click()
        return
    ActionChains(driver).key_down(Keys.SHIFT).click(button).key_up(Keys.SHIFT).perform()


def _state(driver: Chrome) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        driver.execute_script(
            """
            const tree = document.getElementById("event-tree");
            const rows = Array.from(tree.querySelectorAll("li[data-event-id]"));
            const filter = document.querySelector(".unchanged-filter");
            const facts = document.getElementById("selected-facts");
            return {
              classifications: Object.fromEntries(rows.map(row => [
                row.dataset.eventId,
                row.dataset.eventClassification
              ])),
              visible: rows.filter(row => !row.hidden)
                .map(row => row.dataset.eventId),
              hidden: rows.filter(row => row.hidden)
                .map(row => row.dataset.eventId),
              selected: Array.from(
                tree.querySelectorAll('.event-button[aria-current="true"]')
              ).map(button => button.dataset.eventId),
              frontier: tree.dataset.frontier
                ? tree.dataset.frontier.split(" ")
                : [],
              anchor: tree.dataset.anchor || null,
              collapsed: tree.dataset.collapsed
                ? tree.dataset.collapsed.split(" ")
                : [],
              hideUnchanged: tree.dataset.hideUnchanged,
              filterText: filter.textContent,
              filterPressed: filter.getAttribute("aria-pressed"),
              filterControls: filter.getAttribute("aria-controls"),
              filterDisabled: filter.disabled,
              filterFocused: document.activeElement === filter,
              status: document.getElementById("selection-status").textContent,
              columnRoles: Array.from(
                document.querySelectorAll(".state-column")
              ).map(column => column.dataset.roles),
              columnHeadings: Array.from(
                document.querySelectorAll(".state-column h2")
              ).map(heading => heading.textContent),
              facts: facts.hidden ? null : JSON.parse(facts.textContent),
              factsEmpty: document.getElementById("facts-empty").textContent,
              payloadText: document.getElementById("trace-data").textContent,
              canonicalText: JSON.stringify(trace),
              inlineStyles: document.querySelectorAll(
                '.event-tree [style], .unchanged-filter[style]'
              ).length
            };
            """
        ),
    )


def _computed_style(driver: Chrome, element: WebElement) -> dict[str, str]:
    return cast(
        dict[str, str],
        driver.execute_script(
            """
            const style = getComputedStyle(arguments[0]);
            return {
              color: style.color,
              background: style.backgroundColor,
              boxShadow: style.boxShadow,
              outlineColor: style.outlineColor,
              outlineStyle: style.outlineStyle,
              outlineWidth: style.outlineWidth
            };
            """,
            element,
        ),
    )


@pytest.mark.browser  # type: ignore[untyped-decorator]
def test_classification_rows_badges_descriptions_and_muted_cues(
    headed_chrome: BrowserHarness,
    tmp_path: Path,
) -> None:
    driver = _open_trace(
        headed_chrome,
        tmp_path,
        _classification_trace(),
        "unchanged-classification",
    )
    state = _state(driver)
    assert state["classifications"] == {
        EVENT_IDS["changed"]: "changed",
        EVENT_IDS["unchanged_parent"]: "unchanged",
        EVENT_IDS["changed_child"]: "changed",
        EVENT_IDS["inconsistent_equal"]: "inconsistent",
        EVENT_IDS["unchanged_leaf"]: "unchanged",
        EVENT_IDS["inconsistent_different"]: "inconsistent",
        EVENT_IDS["incomplete"]: "incomplete",
    }
    assert state["inlineStyles"] == 0

    badges = driver.find_elements(By.CSS_SELECTOR, ".event-inconsistency-badge")
    assert [badge.get_attribute("textContent") for badge in badges] == [
        "Inconsistent change flag",
        "Inconsistent change flag",
    ]
    assert all(badge.get_attribute("aria-hidden") == "true" for badge in badges)

    equal_description = cast(
        str,
        driver.find_element(
            By.ID,
            cast(
                str,
                _event_button(driver, EVENT_IDS["inconsistent_equal"]).get_attribute(
                    "aria-describedby"
                ),
            ),
        ).get_attribute("textContent"),
    )
    different_description = cast(
        str,
        driver.find_element(
            By.ID,
            cast(
                str,
                _event_button(
                    driver, EVENT_IDS["inconsistent_different"]
                ).get_attribute("aria-describedby"),
            ),
        ).get_attribute("textContent"),
    )
    assert equal_description.endswith(
        "Inconsistent change flag: retained before and after snapshots are "
        "semantically equal, but has_done_something is true."
    )
    assert different_description.endswith(
        "Inconsistent change flag: retained before and after snapshots are "
        "semantically different, but has_done_something is false."
    )
    incomplete_description = driver.find_element(
        By.ID,
        cast(
            str,
            _event_button(driver, EVENT_IDS["incomplete"]).get_attribute(
                "aria-describedby"
            ),
        ),
    ).get_attribute("textContent")
    assert "change classification incomplete" in cast(str, incomplete_description)

    unchanged = _event_button(driver, EVENT_IDS["unchanged_leaf"])
    changed = _event_button(driver, EVENT_IDS["changed"])
    unchanged_style = _computed_style(driver, unchanged)
    assert unchanged_style["color"] == "rgb(203, 213, 225)"
    assert unchanged_style["background"] == "rgb(17, 24, 39)"
    assert _computed_style(driver, changed)["background"] == "rgb(31, 41, 55)"

    unchanged.send_keys(Keys.SPACE)
    selected_style = _computed_style(driver, unchanged)
    assert selected_style["color"] == "rgb(243, 244, 246)"
    assert selected_style["background"] == "rgb(30, 58, 95)"
    assert "rgb(147, 197, 253)" in selected_style["boxShadow"]
    assert selected_style["outlineColor"] == "rgb(244, 114, 182)"
    assert selected_style["outlineStyle"] == "solid"
    assert selected_style["outlineWidth"] == "2px"


@pytest.mark.browser  # type: ignore[untyped-decorator]
def test_native_filter_hides_subtrees_retains_collapse_and_has_keyboard_parity(
    headed_chrome: BrowserHarness,
    tmp_path: Path,
) -> None:
    driver = _open_trace(
        headed_chrome,
        tmp_path,
        _classification_trace(),
        "unchanged-filter-subtrees",
    )
    filter_button = _filter_button(driver)
    assert filter_button.tag_name == "button"
    assert filter_button.get_attribute("type") == "button"
    assert _state(driver) | {"payloadText": "", "canonicalText": ""} == {
        "classifications": {
            EVENT_IDS["changed"]: "changed",
            EVENT_IDS["unchanged_parent"]: "unchanged",
            EVENT_IDS["changed_child"]: "changed",
            EVENT_IDS["inconsistent_equal"]: "inconsistent",
            EVENT_IDS["unchanged_leaf"]: "unchanged",
            EVENT_IDS["inconsistent_different"]: "inconsistent",
            EVENT_IDS["incomplete"]: "incomplete",
        },
        "visible": list(EVENT_IDS.values()),
        "hidden": [],
        "selected": [],
        "frontier": [],
        "anchor": None,
        "collapsed": [],
        "hideUnchanged": "false",
        "filterText": "Hide unchanged events",
        "filterPressed": "false",
        "filterControls": "event-tree",
        "filterDisabled": False,
        "filterFocused": False,
        "status": "Selected: 0; hidden: 0.",
        "columnRoles": [],
        "columnHeadings": [],
        "facts": None,
        "factsEmpty": "No event selected.",
        "payloadText": "",
        "canonicalText": "",
        "inlineStyles": 0,
    }
    baseline = _state(driver)

    parent_toggle = driver.find_element(
        By.CSS_SELECTOR,
        f'.event-collapse[data-event-id="{EVENT_IDS["unchanged_parent"]}"]',
    )
    parent_toggle.click()
    assert _state(driver)["collapsed"] == [EVENT_IDS["unchanged_parent"]]

    driver.execute_script(
        """
        globalThis.__unchangedFilterClicks = 0;
        arguments[0].addEventListener("click", () => {
          globalThis.__unchangedFilterClicks += 1;
        });
        """,
        filter_button,
    )
    filter_button.send_keys(Keys.ENTER)
    filtered = _state(driver)
    assert filtered["visible"] == [
        EVENT_IDS["changed"],
        EVENT_IDS["inconsistent_equal"],
        EVENT_IDS["inconsistent_different"],
        EVENT_IDS["incomplete"],
    ]
    assert filtered["hidden"] == [
        EVENT_IDS["unchanged_parent"],
        EVENT_IDS["changed_child"],
        EVENT_IDS["unchanged_leaf"],
    ]
    assert filtered["collapsed"] == [EVENT_IDS["unchanged_parent"]]
    assert filtered["status"] == "Selected: 0; hidden: 3."
    assert filtered["filterText"] == "Show unchanged events"
    assert filtered["filterPressed"] == "true"
    assert filtered["filterFocused"] is True
    assert driver.execute_script("return globalThis.__unchangedFilterClicks;") == 1

    hidden_names = [
        _event_button(driver, event_id).get_attribute("textContent")
        for event_id in (
            EVENT_IDS["unchanged_parent"],
            EVENT_IDS["changed_child"],
            EVENT_IDS["unchanged_leaf"],
        )
    ]
    tree = headed_chrome.accessibility_tree()
    for name in hidden_names:
        assert tree.matching(role="button", name=cast(str, name)) == ()

    driver.execute_script("arguments[0].click();", parent_toggle)
    assert _state(driver)["collapsed"] == [EVENT_IDS["unchanged_parent"]]

    filter_button.send_keys(Keys.SPACE)
    restored = _state(driver)
    assert restored["visible"] == [
        EVENT_IDS["changed"],
        EVENT_IDS["unchanged_parent"],
        EVENT_IDS["inconsistent_equal"],
        EVENT_IDS["unchanged_leaf"],
        EVENT_IDS["inconsistent_different"],
        EVENT_IDS["incomplete"],
    ]
    assert restored["hidden"] == [EVENT_IDS["changed_child"]]
    assert restored["collapsed"] == [EVENT_IDS["unchanged_parent"]]
    assert restored["selected"] == []
    assert restored["filterFocused"] is True
    assert driver.execute_script("return globalThis.__unchangedFilterClicks;") == 2
    assert restored["payloadText"] == baseline["payloadText"]
    assert restored["canonicalText"] == baseline["canonicalText"]

    nested_trace = event_trace(
        (
            EventSpec("UnchangedRoot", None, "root same", "root same"),
            EventSpec(
                "ChangedBranch", "UnchangedRoot", "branch before", "branch after"
            ),
            EventSpec(
                "ChangedGrandchild",
                "ChangedBranch",
                "grandchild before",
                "grandchild after",
            ),
            EventSpec("ChangedSibling", None, "sibling before", "sibling after"),
        )
    )
    driver = _open_trace(
        headed_chrome,
        tmp_path,
        nested_trace,
        "unchanged-filter-nested-collapse",
    )
    root_toggle = driver.find_element(
        By.CSS_SELECTOR,
        '.event-collapse[data-event-id="event-0"]',
    )
    branch_toggle = driver.find_element(
        By.CSS_SELECTOR,
        '.event-collapse[data-event-id="event-1"]',
    )
    branch_toggle.click()
    root_toggle.click()
    assert _state(driver)["collapsed"] == ["event-0", "event-1"]
    _filter_button(driver).click()
    assert _state(driver)["visible"] == ["event-3"]
    _filter_button(driver).click()
    nested_restored = _state(driver)
    assert nested_restored["collapsed"] == ["event-0", "event-1"]
    assert nested_restored["visible"] == ["event-0", "event-3"]
    root_toggle.click()
    expanded_root = _state(driver)
    assert expanded_root["collapsed"] == ["event-1"]
    assert expanded_root["visible"] == ["event-0", "event-1", "event-3"]
    assert expanded_root["hidden"] == ["event-2"]

    observations = headed_chrome.observations()
    assert observations.page_network_requests() == ()
    assert observations.csp_violations == ()
    assert not [
        entry for entry in observations.console if entry.level in {"SEVERE", "WARNING"}
    ]


@pytest.mark.browser  # type: ignore[untyped-decorator]
def test_filter_reconciles_selection_anchor_workspace_and_restoration(
    headed_chrome: BrowserHarness,
    tmp_path: Path,
) -> None:
    driver = _open_trace(
        headed_chrome,
        tmp_path,
        _classification_trace(),
        "unchanged-filter-surviving-anchor",
    )
    baseline = _state(driver)
    _activate(driver, EVENT_IDS["changed"])
    _activate(driver, EVENT_IDS["unchanged_leaf"], shift=True)
    assert _state(driver)["frontier"] == [
        EVENT_IDS["changed"],
        EVENT_IDS["unchanged_parent"],
        EVENT_IDS["inconsistent_equal"],
        EVENT_IDS["unchanged_leaf"],
    ]
    _filter_button(driver).click()
    surviving_anchor = _state(driver)
    assert surviving_anchor["frontier"] == [
        EVENT_IDS["changed"],
        EVENT_IDS["inconsistent_equal"],
    ]
    assert surviving_anchor["anchor"] == EVENT_IDS["changed"]
    assert surviving_anchor["columnRoles"] == [
        f"{EVENT_IDS['changed']}.before",
        (f"{EVENT_IDS['changed']}.after|{EVENT_IDS['inconsistent_equal']}.before"),
        f"{EVENT_IDS['inconsistent_equal']}.after",
    ]
    assert surviving_anchor["payloadText"] == baseline["payloadText"]
    assert surviving_anchor["canonicalText"] == baseline["canonicalText"]
    _filter_button(driver).click()
    restored = _state(driver)
    assert restored["selected"] == [
        EVENT_IDS["changed"],
        EVENT_IDS["inconsistent_equal"],
    ]
    assert EVENT_IDS["unchanged_parent"] in restored["visible"]
    assert EVENT_IDS["unchanged_leaf"] in restored["visible"]

    driver = _open_trace(
        headed_chrome,
        tmp_path,
        _classification_trace(),
        "unchanged-filter-removed-anchor",
    )
    _activate(driver, EVENT_IDS["unchanged_parent"])
    _activate(driver, EVENT_IDS["inconsistent_equal"], shift=True)
    assert _state(driver)["anchor"] == EVENT_IDS["unchanged_parent"]
    _filter_button(driver).click()
    removed_anchor = _state(driver)
    assert removed_anchor["frontier"] == [EVENT_IDS["inconsistent_equal"]]
    assert removed_anchor["anchor"] == EVENT_IDS["inconsistent_equal"]
    assert removed_anchor["filterFocused"] is True

    driver = _open_trace(
        headed_chrome,
        tmp_path,
        _classification_trace(),
        "unchanged-filter-fully-removed",
    )
    _activate(driver, EVENT_IDS["unchanged_leaf"])
    _filter_button(driver).click()
    cleared = _state(driver)
    assert cleared["frontier"] == []
    assert cleared["anchor"] is None
    assert cleared["columnRoles"] == []
    assert cleared["facts"] is None
    assert cleared["factsEmpty"] == "No event selected."
    assert cleared["filterFocused"] is True


@pytest.mark.browser  # type: ignore[untyped-decorator]
def test_filtered_shift_ranges_use_visible_order_and_clear_keeps_filter(
    headed_chrome: BrowserHarness,
    tmp_path: Path,
) -> None:
    driver = _open_trace(
        headed_chrome,
        tmp_path,
        _classification_trace(),
        "unchanged-filter-ranges",
    )
    _filter_button(driver).click()
    visible_frontier = [
        EVENT_IDS["changed"],
        EVENT_IDS["inconsistent_equal"],
        EVENT_IDS["inconsistent_different"],
        EVENT_IDS["incomplete"],
    ]
    expected_columns = [
        f"{EVENT_IDS['changed']}.before",
        (f"{EVENT_IDS['changed']}.after|{EVENT_IDS['inconsistent_equal']}.before"),
        (
            f"{EVENT_IDS['inconsistent_equal']}.after|"
            f"{EVENT_IDS['inconsistent_different']}.before"
        ),
        (
            f"{EVENT_IDS['inconsistent_different']}.after|"
            f"{EVENT_IDS['incomplete']}.before"
        ),
        f"{EVENT_IDS['incomplete']}.after",
    ]

    _activate(driver, EVENT_IDS["changed"])
    _activate(driver, EVENT_IDS["incomplete"], shift=True)
    forward = _state(driver)
    assert forward["frontier"] == visible_frontier
    assert forward["anchor"] == EVENT_IDS["changed"]
    assert forward["columnRoles"] == expected_columns
    assert forward["columnHeadings"][1:4] == [
        (
            "Shared by exact equality: "
            f"{EVENT_IDS['changed']}.after | "
            f"{EVENT_IDS['inconsistent_equal']}.before"
        ),
        (
            "Shared by exact equality: "
            f"{EVENT_IDS['inconsistent_equal']}.after | "
            f"{EVENT_IDS['inconsistent_different']}.before"
        ),
        (
            "Shared by exact equality: "
            f"{EVENT_IDS['inconsistent_different']}.after | "
            f"{EVENT_IDS['incomplete']}.before"
        ),
    ]

    driver.find_element(By.CSS_SELECTOR, ".clear-selection").click()
    after_clear = _state(driver)
    assert after_clear["frontier"] == []
    assert after_clear["anchor"] is None
    assert after_clear["hideUnchanged"] == "true"
    assert after_clear["hidden"] == [
        EVENT_IDS["unchanged_parent"],
        EVENT_IDS["changed_child"],
        EVENT_IDS["unchanged_leaf"],
    ]

    _activate(driver, EVENT_IDS["incomplete"])
    _activate(driver, EVENT_IDS["changed"], shift=True)
    reverse = _state(driver)
    assert reverse["frontier"] == visible_frontier
    assert reverse["anchor"] == EVENT_IDS["incomplete"]
    assert reverse["columnRoles"] == expected_columns


@pytest.mark.browser  # type: ignore[untyped-decorator]
@pytest.mark.parametrize(
    "trace,name",
    [
        (Trace(schema_version=1, complete=True), "empty"),
        (
            event_trace((EventSpec("ChangedOnly", None, "before", "after"),)),
            "no-unchanged",
        ),
    ],
)  # type: ignore[untyped-decorator]
def test_filter_is_disabled_when_no_event_is_unchanged(
    headed_chrome: BrowserHarness,
    tmp_path: Path,
    trace: Trace,
    name: str,
) -> None:
    driver = _open_trace(headed_chrome, tmp_path, trace, f"unchanged-disabled-{name}")
    filter_button = _filter_button(driver)
    assert filter_button.get_attribute("disabled") == "true"
    assert filter_button.get_attribute("aria-pressed") == "false"
    assert filter_button.get_attribute("aria-controls") == "event-tree"
    assert filter_button.get_attribute("textContent") == "Hide unchanged events"
    assert _state(driver)["hideUnchanged"] == "false"
    tree = headed_chrome.accessibility_tree()
    assert tree.matching(role="button", name="Hide unchanged events")
