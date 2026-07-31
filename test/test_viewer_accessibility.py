from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest
from browser_harness import BrowserHarness
from selenium.webdriver import ActionChains, Chrome
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from viewer_fixtures import (
    COARSE_PROVENANCE_ENTITY_IDS,
    COARSE_PROVENANCE_EVENT_ID,
    METADATA_ENTITY_IDS,
    METADATA_EVENT_IDS,
    SELECTION_IDS,
    coarse_provenance_trace,
    metadata_trace,
    selection_trace,
)

from kirin_rewrite_tracer import Trace, export_html


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


def _frontier(driver: Chrome) -> tuple[str, ...]:
    value = cast(
        str,
        driver.find_element(By.ID, "event-tree").get_attribute("data-frontier"),
    )
    return tuple(value.split()) if value else ()


def _related(driver: Chrome) -> tuple[tuple[int, str], ...]:
    return tuple(
        (
            int(cast(str, element.get_attribute("data-column-index"))),
            cast(str, element.get_attribute("data-entity-id")),
        )
        for element in driver.find_elements(
            By.CSS_SELECTOR,
            '.ssa-occurrence[data-provenance-related="true"]',
        )
    )


def _settle(driver: Chrome) -> None:
    driver.execute_async_script(
        """
        const done = arguments[0];
        requestAnimationFrame(() => requestAnimationFrame(done));
        """
    )


def _send_native_key(
    driver: Chrome,
    target: WebElement,
    key: str,
    modifiers: tuple[str, ...] = (),
) -> None:
    driver.execute_script(
        "arguments[0].focus({preventScroll: true});",
        target,
    )
    actions = ActionChains(driver)
    for modifier in modifiers:
        actions.key_down(modifier)
    actions.send_keys(key)
    for modifier in reversed(modifiers):
        actions.key_up(modifier)
    actions.perform()
    _settle(driver)


def _true_tab_to(driver: Chrome, target: WebElement) -> None:
    previous = cast(
        WebElement,
        driver.execute_script(
            """
            const target = arguments[0];
            const controls = Array.from(
              document.querySelectorAll(
                'a[href], button, [tabindex]:not([tabindex="-1"])'
              )
            ).filter(control =>
              !control.hidden &&
              control.closest("[hidden]") === null &&
              !control.disabled &&
              control.tabIndex >= 0
            );
            const index = controls.indexOf(target);
            if (index <= 0) {
              throw new Error("target lacks a preceding sequential control");
            }
            controls[index - 1].focus({preventScroll: true});
            return controls[index - 1];
            """,
            target,
        ),
    )
    assert previous != target
    ActionChains(driver).send_keys(Keys.TAB).perform()
    _settle(driver)
    assert driver.switch_to.active_element == target


def _install_activation_oracle(
    driver: Chrome,
    target: WebElement,
) -> None:
    driver.execute_script(
        """
        globalThis.__krtActivationObserver?.disconnect();
        globalThis.__krtActivationClicks = 0;
        globalThis.__krtColumnMutations = 0;
        globalThis.__krtObservedActivations ??= new WeakSet();
        if (!globalThis.__krtObservedActivations.has(arguments[0])) {
          arguments[0].addEventListener(
            "click",
            () => { globalThis.__krtActivationClicks += 1; },
            true
          );
          globalThis.__krtObservedActivations.add(arguments[0]);
        }
        globalThis.__krtActivationObserver = new MutationObserver(records => {
          globalThis.__krtColumnMutations += records.filter(
            record => record.type === "childList"
          ).length;
        });
        globalThis.__krtActivationObserver.observe(
          document.getElementById("ssa-columns"),
          {childList: true}
        );
        """,
        target,
    )


def _activation_counts(driver: Chrome) -> tuple[int, int]:
    values = cast(
        list[int],
        driver.execute_script(
            """
            return [
              globalThis.__krtActivationClicks,
              globalThis.__krtColumnMutations
            ];
            """
        ),
    )
    return (values[0], values[1])


@pytest.mark.browser  # type: ignore[untyped-decorator]
def test_skip_native_document_semantics_and_empty_workspace(
    headed_chrome: BrowserHarness,
    tmp_path: Path,
) -> None:
    driver = _open_trace(
        headed_chrome,
        tmp_path,
        Trace(schema_version=1, complete=True),
        "accessibility-empty",
    )

    ActionChains(driver).send_keys(Keys.TAB).perform()
    assert driver.switch_to.active_element.get_attribute("class") == "skip-link"
    driver.switch_to.active_element.send_keys(Keys.ENTER)
    assert driver.switch_to.active_element.get_attribute("id") == "ssa-workspace"
    assert _frontier(driver) == ()
    assert driver.find_elements(By.CSS_SELECTOR, ".event-button") == []
    assert driver.find_elements(By.CSS_SELECTOR, ".ssa-occurrence") == []
    assert driver.find_element(By.ID, "ssa-empty").get_attribute("textContent") == (
        "No rewrite events were captured."
    )

    tree = headed_chrome.accessibility_tree()
    assert tree.matching(role="link", name="Skip event hierarchy")
    assert tree.matching(role="button", name="Clear selection")
    assert tree.matching(role="region", name="SSA states")
    assert tree.matching(role="region", name="Selected event facts")
    status = driver.find_element(By.ID, "selection-status")
    assert status.get_attribute("role") == "status"
    assert status.get_attribute("aria-live") == "polite"
    assert tree.matching(role="status")
    assert not any(
        node.role in {"tree", "treegrid", "grid", "dialog"} for node in tree.nodes
    )

    driver = _open_trace(
        headed_chrome,
        tmp_path,
        selection_trace(),
        "accessibility-nonempty-no-selection",
    )
    ActionChains(driver).send_keys(Keys.TAB).perform()
    assert driver.switch_to.active_element.get_attribute("class") == "skip-link"
    driver.switch_to.active_element.send_keys(Keys.ENTER)
    assert driver.switch_to.active_element.get_attribute("id") == "ssa-workspace"
    assert _frontier(driver) == ()
    assert driver.find_elements(By.CSS_SELECTOR, ".ssa-occurrence") == []
    assert driver.find_element(By.ID, "ssa-empty").get_attribute("textContent") == (
        "Select an event to inspect states."
    )


@pytest.mark.browser  # type: ignore[untyped-decorator]
@pytest.mark.parametrize(
    ("key", "modifiers", "shift_range"),
    [
        pytest.param(Keys.ENTER, (), False, id="enter"),
        pytest.param(Keys.SPACE, (), False, id="space"),
        pytest.param(Keys.ENTER, (Keys.SHIFT,), True, id="shift-enter"),
        pytest.param(Keys.SPACE, (Keys.SHIFT,), True, id="shift-space"),
        pytest.param(Keys.ENTER, (Keys.CONTROL,), False, id="control-enter"),
        pytest.param(Keys.SPACE, (Keys.CONTROL,), False, id="control-space"),
        pytest.param(Keys.ENTER, (Keys.META,), False, id="meta-enter"),
        pytest.param(Keys.SPACE, (Keys.META,), False, id="meta-space"),
        pytest.param(
            Keys.ENTER,
            (Keys.SHIFT, Keys.CONTROL),
            True,
            id="shift-control-enter",
        ),
        pytest.param(
            Keys.SPACE,
            (Keys.SHIFT, Keys.META),
            True,
            id="shift-meta-space",
        ),
    ],
)  # type: ignore[untyped-decorator]
def test_native_event_keyboard_activation_is_exactly_once(
    headed_chrome: BrowserHarness,
    tmp_path: Path,
    key: str,
    modifiers: tuple[str, ...],
    shift_range: bool,
) -> None:
    driver = _open_trace(
        headed_chrome,
        tmp_path,
        selection_trace(),
        f"accessibility-event-{key.encode().hex()}-{len(modifiers)}",
    )
    target_id = SELECTION_IDS["C4"]
    target = _event_button(driver, target_id)
    if shift_range:
        _event_button(driver, SELECTION_IDS["C1"]).click()
    _install_activation_oracle(driver, target)

    before = _frontier(driver)
    driver.execute_script("arguments[0].focus({preventScroll: true});", target)
    assert _frontier(driver) == before
    _send_native_key(driver, target, key, modifiers)

    expected = (target_id, SELECTION_IDS["C1"]) if shift_range else (target_id,)
    assert _frontier(driver) == expected
    assert driver.switch_to.active_element == target
    assert _activation_counts(driver) == (1, 1)
    assert target.get_attribute("aria-describedby") and "selection selected" in cast(
        str,
        driver.find_element(
            By.ID,
            cast(str, target.get_attribute("aria-describedby")),
        ).get_attribute("textContent"),
    )

    status = driver.find_element(By.ID, "selection-status")
    if shift_range:
        assert status.get_attribute("textContent") == (
            f"Selected: 2; first: {target_id}; last: {SELECTION_IDS['C1']}; hidden: 1."
        )
    else:
        assert status.get_attribute("textContent") == (
            f"Selected: 1; event: {target_id}; hidden: 1."
        )

    clear = driver.find_element(By.CSS_SELECTOR, ".clear-selection")
    _install_activation_oracle(driver, clear)
    _send_native_key(driver, clear, Keys.SPACE)
    assert _activation_counts(driver) == (1, 1)
    assert _frontier(driver) == ()
    assert driver.switch_to.active_element == clear
    assert status.get_attribute("textContent") == "Selected: 0; hidden: 0."
    assert not driver.find_element(By.ID, "facts-empty").get_attribute("hidden")

    _install_activation_oracle(driver, clear)
    _send_native_key(driver, clear, Keys.ENTER)
    assert _activation_counts(driver)[0] == 1
    assert _frontier(driver) == ()
    assert driver.switch_to.active_element == clear
    assert status.get_attribute("textContent") == "Selected: 0; hidden: 0."


@pytest.mark.browser  # type: ignore[untyped-decorator]
def test_keyboard_focus_fallback_hidden_rows_and_restoration(
    headed_chrome: BrowserHarness,
    tmp_path: Path,
) -> None:
    driver = _open_trace(
        headed_chrome,
        tmp_path,
        selection_trace(),
        "accessibility-focus-fallback",
    )

    grandchild = _event_button(driver, SELECTION_IDS["G8"])
    swallowed_target = _event_button(driver, SELECTION_IDS["D2"])
    _send_native_key(driver, grandchild, Keys.ENTER)
    _send_native_key(
        driver,
        swallowed_target,
        Keys.SPACE,
        (Keys.SHIFT,),
    )
    assert _frontier(driver) == (
        SELECTION_IDS["G8"],
        SELECTION_IDS["C1"],
        SELECTION_IDS["S7"],
    )
    assert driver.switch_to.active_element == _event_button(
        driver,
        SELECTION_IDS["S7"],
    )
    assert (
        _event_button(
            driver,
            SELECTION_IDS["D2"],
        )
        .find_element(By.XPATH, "ancestor::li[1]")
        .get_attribute("hidden")
    )

    driver.find_element(By.CSS_SELECTOR, ".clear-selection").click()
    _send_native_key(driver, grandchild, Keys.ENTER)
    root = _event_button(driver, SELECTION_IDS["R9"])
    _send_native_key(driver, root, Keys.ENTER, (Keys.SHIFT,))
    assert _frontier(driver) == (SELECTION_IDS["R9"],)
    assert driver.switch_to.active_element == root
    root_nodes = headed_chrome.accessibility_tree().matching(
        role="button",
        name=cast(str, root.get_attribute("textContent")),
    )
    assert len(root_nodes) == 1
    root_description = (
        f"Event {SELECTION_IDS['R9']}; rule R9; depth 0; parent absent; "
        "sibling 1 of 4; completion incomplete; selection selected."
    )
    assert root_nodes[0].description == root_description
    root_tree = headed_chrome.accessibility_tree()
    assert not any(
        node.role == "StaticText" and node.name == root_description
        for node in root_tree.nodes
    )
    assert driver.find_element(
        By.ID,
        cast(str, root.get_attribute("aria-describedby")),
    ).get_attribute("hidden")

    hidden_ids = (SELECTION_IDS["C4"], SELECTION_IDS["G8"])
    tree = headed_chrome.accessibility_tree()
    for event_id in hidden_ids:
        name = _event_button(driver, event_id).get_attribute("textContent")
        assert tree.matching(role="button", name=cast(str, name)) == ()

    ActionChains(driver).send_keys(Keys.TAB).perform()
    assert driver.switch_to.active_element == _event_button(
        driver,
        SELECTION_IDS["C1"],
    )
    _send_native_key(
        driver,
        _event_button(driver, SELECTION_IDS["C1"]),
        Keys.ENTER,
    )
    assert driver.switch_to.active_element == _event_button(
        driver,
        SELECTION_IDS["C1"],
    )
    assert all(
        not _event_button(driver, event_id)
        .find_element(By.XPATH, "ancestor::li[1]")
        .get_attribute("hidden")
        for event_id in hidden_ids
    )
    restored_tree = headed_chrome.accessibility_tree()
    for event_id in hidden_ids:
        name = _event_button(driver, event_id).get_attribute("textContent")
        assert len(restored_tree.matching(role="button", name=cast(str, name))) == 1
        assert _event_button(driver, event_id).get_attribute("aria-current") is None

    ActionChains(driver).key_down(Keys.SHIFT).send_keys(Keys.TAB).key_up(
        Keys.SHIFT
    ).perform()
    assert driver.switch_to.active_element == _event_button(
        driver,
        SELECTION_IDS["G8"],
    )


@pytest.mark.browser  # type: ignore[untyped-decorator]
def test_occurrence_names_descriptions_and_metadata_focus_lifecycle(
    headed_chrome: BrowserHarness,
    tmp_path: Path,
) -> None:
    trace = metadata_trace()
    driver = _open_trace(
        headed_chrome,
        tmp_path,
        trace,
        "accessibility-occurrence-metadata",
    )
    _event_button(driver, METADATA_EVENT_IDS["A"]).click()
    event = trace.index().event(METADATA_EVENT_IDS["A"])
    snapshot_ids = (event.before_snapshot_id, event.after_snapshot_id)

    for column_index, snapshot_id in enumerate(snapshot_ids):
        assert snapshot_id is not None
        snapshot = trace.index().snapshot(snapshot_id)
        expected = tuple(
            trace.index().occurrence(occurrence_id)
            for occurrence_id in snapshot.occurrence_ids
            if trace.index().occurrence(occurrence_id).role
            in {"definition", "reference"}
        )
        controls = driver.find_elements(
            By.CSS_SELECTOR,
            f".state-column:nth-child({column_index + 1}) .ssa-occurrence",
        )
        assert [control.tag_name for control in controls] == ["button"] * len(expected)
        assert [control.get_attribute("aria-label") for control in controls] == [
            snapshot.text[occurrence.start : occurrence.end] for occurrence in expected
        ]
        for control, occurrence in zip(controls, expected, strict=True):
            entity = trace.index().entity(occurrence.entity_id)
            description = cast(
                str,
                driver.find_element(
                    By.ID,
                    cast(str, control.get_attribute("aria-describedby")),
                ).get_attribute("textContent"),
            )
            assert f"entity {entity.id}" in description
            assert f"defining owner {entity.defining_owner_id}" in description
            assert f"{event.id}.{snapshot.state}" in description
            assert control.get_attribute("aria-expanded") == "false"
            assert cast(str, control.get_attribute("aria-controls")).startswith(
                "ssa-metadata-overlay-"
            )

    relationship_ids = [
        cast(str, control.get_attribute("aria-controls"))
        for control in driver.find_elements(By.CSS_SELECTOR, ".ssa-occurrence")
    ]
    assert len(relationship_ids) == len(set(relationship_ids))

    anchor = driver.find_elements(
        By.CSS_SELECTOR,
        (
            '.state-column:first-child .ssa-occurrence[data-entity-id="'
            f'{METADATA_ENTITY_IDS["survivor"]}"]'
        ),
    )[0]
    suffix = anchor.find_elements(
        By.XPATH,
        "following-sibling::*[1][contains(@class, 'ssa-metadata-suffix')]",
    )[0]
    assert suffix.get_attribute("aria-hidden") == "true"
    assert not anchor.find_elements(By.CSS_SELECTOR, ".ssa-metadata-suffix")

    _install_activation_oracle(driver, anchor)
    _send_native_key(driver, anchor, Keys.ENTER)
    assert _activation_counts(driver)[0] == 1
    overlay = driver.find_element(By.CSS_SELECTOR, ".ssa-metadata-overlay")
    assert overlay.get_attribute("id") == anchor.get_attribute("aria-controls")
    assert driver.switch_to.active_element == anchor
    assert anchor.get_attribute("aria-expanded") == "true"
    assert overlay.get_attribute("role") == "region"
    assert overlay.get_attribute("tabindex") == "0"
    assert all(
        item.tag_name == "li"
        and len(item.find_elements(By.CSS_SELECTOR, ":scope > dl")) == 1
        and all(
            len(field.find_elements(By.CSS_SELECTOR, ":scope > dt")) == 1
            and len(field.find_elements(By.CSS_SELECTOR, ":scope > dd")) == 1
            for field in item.find_elements(
                By.CSS_SELECTOR,
                ":scope > dl > .ssa-metadata-field",
            )
        )
        for item in overlay.find_elements(
            By.CSS_SELECTOR,
            ".ssa-metadata-bindings > .ssa-metadata-binding",
        )
    )

    tree = headed_chrome.accessibility_tree()
    anchor_description = driver.find_element(
        By.ID,
        cast(str, anchor.get_attribute("aria-describedby")),
    ).get_attribute("textContent")
    assert any(
        node.description == anchor_description
        for node in tree.matching(
            role="button",
            name=cast(str, anchor.get_attribute("aria-label")),
        )
    )
    assert not any(
        node.role == "StaticText" and node.name == anchor_description
        for node in tree.nodes
    )
    assert driver.find_element(
        By.ID,
        cast(str, anchor.get_attribute("aria-describedby")),
    ).get_attribute("hidden")
    region = tree.matching(role="region", name=overlay.accessible_name)
    assert len(region) == 1
    region_name = cast(str, region[0].name)
    assert cast(str, anchor.get_attribute("aria-label")) in region_name
    assert METADATA_ENTITY_IDS["survivor"] in region_name

    ActionChains(driver).send_keys(Keys.TAB).perform()
    assert driver.switch_to.active_element == overlay
    ActionChains(driver).key_down(Keys.SHIFT).send_keys(Keys.TAB).key_up(
        Keys.SHIFT
    ).perform()
    assert driver.switch_to.active_element == anchor
    assert driver.find_element(By.CSS_SELECTOR, ".ssa-metadata-overlay")
    ActionChains(driver).send_keys(Keys.TAB).perform()
    assert driver.switch_to.active_element == overlay
    overlay.send_keys(Keys.ESCAPE)
    assert driver.find_elements(By.CSS_SELECTOR, ".ssa-metadata-overlay") == []
    assert driver.switch_to.active_element == anchor
    assert anchor.get_attribute("aria-expanded") == "false"
    assert _related(driver) == ()

    _send_native_key(driver, anchor, Keys.SPACE)
    overlay = driver.find_element(By.CSS_SELECTOR, ".ssa-metadata-overlay")
    overlay.click()
    driver.execute_script("arguments[0].focus();", overlay)
    driver.execute_script("window.dispatchEvent(new Event('resize'));")
    _settle(driver)
    assert driver.find_elements(By.CSS_SELECTOR, ".ssa-metadata-overlay") == []
    assert driver.switch_to.active_element == anchor

    _send_native_key(driver, anchor, Keys.ENTER)
    ActionChains(driver).send_keys(Keys.TAB).perform()
    overlay = driver.find_element(By.CSS_SELECTOR, ".ssa-metadata-overlay")
    assert driver.switch_to.active_element == overlay
    driver.execute_script("document.dispatchEvent(new Event('scroll'));")
    _settle(driver)
    assert driver.find_elements(By.CSS_SELECTOR, ".ssa-metadata-overlay") == []
    assert driver.switch_to.active_element == anchor
    assert _related(driver) == ()

    _send_native_key(driver, anchor, Keys.SPACE)
    event_b = _event_button(driver, METADATA_EVENT_IDS["B"])
    _send_native_key(driver, event_b, Keys.ENTER)
    assert driver.find_elements(By.CSS_SELECTOR, ".ssa-metadata-overlay") == []
    assert driver.switch_to.active_element == event_b
    assert _frontier(driver) == (METADATA_EVENT_IDS["B"],)

    _event_button(driver, METADATA_EVENT_IDS["A"]).click()
    anchor = driver.find_elements(
        By.CSS_SELECTOR,
        (
            '.state-column:first-child .ssa-occurrence[data-entity-id="'
            f'{METADATA_ENTITY_IDS["survivor"]}"]'
        ),
    )[0]
    _send_native_key(driver, anchor, Keys.ENTER)
    clear = driver.find_element(By.CSS_SELECTOR, ".clear-selection")
    driver.execute_script("arguments[0].focus();", clear)
    clear.send_keys(Keys.ESCAPE)
    assert driver.find_elements(By.CSS_SELECTOR, ".ssa-metadata-overlay") == []
    assert driver.switch_to.active_element == clear


@pytest.mark.browser  # type: ignore[untyped-decorator]
def test_keyboard_provenance_uses_hover_projection_and_newest_candidate(
    headed_chrome: BrowserHarness,
    tmp_path: Path,
) -> None:
    trace = coarse_provenance_trace()
    driver = _open_trace(
        headed_chrome,
        tmp_path,
        trace,
        "accessibility-provenance",
    )
    _event_button(driver, COARSE_PROVENANCE_EVENT_ID).click()
    entities = COARSE_PROVENANCE_ENTITY_IDS

    def occurrence(entity_id: str, ordinal: int = 0) -> WebElement:
        return driver.find_elements(
            By.CSS_SELECTOR,
            (
                '.state-column:first-child .ssa-occurrence[data-entity-id="'
                f'{entity_id}"]'
            ),
        )[ordinal]

    split = occurrence(entities["split_source"])
    ActionChains(driver).move_to_element(split).perform()
    hover_oracle = _related(driver)
    assert {entity for _, entity in hover_oracle} == {
        entities["split_destination_left"],
        entities["split_destination_right"],
    }
    ActionChains(driver).move_to_element(
        driver.find_element(By.ID, "trace-summary")
    ).perform()
    assert _related(driver) == ()

    driver.execute_script(
        "arguments[0].focus({preventScroll: true});",
        split,
    )
    assert _related(driver) == ()
    _install_activation_oracle(driver, split)
    _send_native_key(driver, split, Keys.ENTER)
    assert _activation_counts(driver)[0] == 1
    assert _related(driver) == hover_oracle
    split.send_keys(Keys.ESCAPE)
    driver.execute_script(
        "arguments[0].focus({preventScroll: true});",
        _event_button(driver, COARSE_PROVENANCE_EVENT_ID),
    )
    _settle(driver)
    assert _related(driver) == ()

    ActionChains(driver).click(split).perform()
    assert _related(driver) == hover_oracle
    ActionChains(driver).move_to_element(
        driver.find_element(By.ID, "trace-summary")
    ).perform()
    assert driver.switch_to.active_element == split
    assert _related(driver) == ()
    split.send_keys(Keys.ESCAPE)
    _install_activation_oracle(driver, split)
    _send_native_key(driver, split, Keys.SPACE)
    assert _activation_counts(driver)[0] == 1
    assert _related(driver) == hover_oracle
    split.send_keys(Keys.ESCAPE)
    driver.execute_script(
        "arguments[0].focus({preventScroll: true});",
        _event_button(driver, COARSE_PROVENANCE_EVENT_ID),
    )
    _settle(driver)
    assert _related(driver) == ()

    _true_tab_to(driver, split)
    assert _related(driver) == hover_oracle
    description = cast(
        str,
        driver.find_element(
            By.ID,
            cast(str, split.get_attribute("aria-describedby")),
        ).get_attribute("textContent"),
    )
    assert "Right neighbor" in description
    assert "column roles" in description
    for _, target_id in hover_oracle:
        target = trace.index().entity(target_id)
        assert f"entity {target.id}" in description
        assert f"defining owner {target.defining_owner_id}" in description
    assert "Neighbor occurrence ordinal " in description

    missing = occurrence(entities["missing_source"])
    _true_tab_to(driver, missing)
    missing_description = cast(
        str,
        driver.find_element(
            By.ID,
            cast(str, missing.get_attribute("aria-describedby")),
        ).get_attribute("textContent"),
    )
    assert "Right neighbor" in missing_description
    assert "present; matches 0." in missing_description

    survivor = occurrence(entities["survivor"])
    _true_tab_to(driver, survivor)
    survivor_oracle = _related(driver)
    ActionChains(driver).move_to_element(split).perform()
    assert _related(driver) == hover_oracle
    ActionChains(driver).send_keys(Keys.TAB).perform()
    _settle(driver)
    assert _related(driver) == survivor_oracle
    driver.execute_script(
        "arguments[0].focus({preventScroll: true});",
        _event_button(driver, COARSE_PROVENANCE_EVENT_ID),
    )
    _settle(driver)
    assert _related(driver) == hover_oracle
    ActionChains(driver).move_to_element(
        driver.find_element(By.ID, "trace-summary")
    ).perform()
    assert _related(driver) == ()

    ActionChains(driver).move_to_element(split).perform()
    assert _related(driver) == hover_oracle
    driver.execute_script(
        "globalThis.__krtStaleOccurrence = arguments[0];",
        split,
    )
    payload_before = tuple(
        cast(
            list[str],
            driver.execute_script(
                """
                return [
                  document.getElementById("trace-data").textContent,
                  JSON.stringify(trace)
                ];
                """
            ),
        )
    )
    driver.execute_script("renderSelection(selectionState);")
    _settle(driver)
    assert cast(
        bool,
        driver.execute_script("return !globalThis.__krtStaleOccurrence.isConnected;"),
    )
    assert _related(driver) == ()
    recreated_split = occurrence(entities["split_source"])
    ActionChains(driver).move_by_offset(1, 0).perform()
    _settle(driver)
    assert _related(driver) == hover_oracle
    ActionChains(driver).move_to_element(
        driver.find_element(By.ID, "trace-summary")
    ).perform()
    assert _related(driver) == ()
    driver.execute_script(
        """
        globalThis.__krtStaleOccurrence.dispatchEvent(
          new PointerEvent("pointerenter", {bubbles: false})
        );
        """
    )
    assert _related(driver) == ()

    _true_tab_to(driver, recreated_split)
    assert _related(driver) == hover_oracle
    driver.execute_script(
        "globalThis.__krtKeyboardStaleOccurrence = arguments[0];",
        recreated_split,
    )
    driver.execute_script("renderSelection(selectionState);")
    _settle(driver)
    assert cast(
        bool,
        driver.execute_script(
            "return !globalThis.__krtKeyboardStaleOccurrence.isConnected;"
        ),
    )
    assert _related(driver) == ()
    assert (
        tuple(
            cast(
                list[str],
                driver.execute_script(
                    """
                    return [
                      document.getElementById("trace-data").textContent,
                      JSON.stringify(trace)
                    ];
                    """
                ),
            )
        )
        == payload_before
    )

    observations = headed_chrome.observations()
    assert observations.page_network_requests() == ()
    assert observations.csp_violations == ()
    assert observations.console == ()


@pytest.mark.browser  # type: ignore[untyped-decorator]
def test_suspended_candidates_do_not_survive_shared_role_transitions(
    headed_chrome: BrowserHarness,
    tmp_path: Path,
) -> None:
    driver = _open_trace(
        headed_chrome,
        tmp_path,
        metadata_trace(),
        "accessibility-candidate-role-transition",
    )
    _event_button(driver, METADATA_EVENT_IDS["A"]).click()

    before_survivor = driver.find_elements(
        By.CSS_SELECTOR,
        (
            '.state-column:first-child .ssa-occurrence[data-entity-id="'
            f'{METADATA_ENTITY_IDS["survivor"]}"]'
        ),
    )[0]
    after_external = driver.find_elements(
        By.CSS_SELECTOR,
        (
            '.state-column:nth-child(2) .ssa-occurrence[data-entity-id="'
            f'{METADATA_ENTITY_IDS["external"]}"]'
        ),
    )[0]
    _true_tab_to(driver, after_external)
    keyboard_targets = _related(driver)
    assert keyboard_targets
    ActionChains(driver).move_to_element(before_survivor).perform()
    pointer_targets = _related(driver)
    assert pointer_targets
    assert pointer_targets != keyboard_targets
    driver.execute_script(
        """
        globalThis.__krtSuspendedKeyboard = arguments[0];
        globalThis.__krtOwningPointer = arguments[1];
        """,
        after_external,
        before_survivor,
    )

    driver.execute_script(
        """
        const next = reduceSelection(
          selectionState,
          {
            kind: "activate",
            targetId: arguments[0],
            shiftKey: true,
            ctrlKey: false,
            metaKey: false
          },
          visibleEventIds(selectionState).slice()
        );
        selectionState = next;
        renderSelection(selectionState);
        """,
        METADATA_EVENT_IDS["B"],
    )
    _settle(driver)
    assert [
        column.get_attribute("data-roles")
        for column in driver.find_elements(By.CSS_SELECTOR, ".state-column")
    ] == [
        f"{METADATA_EVENT_IDS['A']}.before",
        (f"{METADATA_EVENT_IDS['A']}.after|{METADATA_EVENT_IDS['B']}.before"),
        f"{METADATA_EVENT_IDS['B']}.after",
    ]
    shared_occurrence = driver.find_elements(
        By.CSS_SELECTOR,
        (
            '.state-column:nth-child(2) .ssa-occurrence[data-entity-id="'
            f'{METADATA_ENTITY_IDS["survivor"]}"]'
        ),
    )[0]
    shared_description = cast(
        str,
        driver.find_element(
            By.ID,
            cast(str, shared_occurrence.get_attribute("aria-describedby")),
        ).get_attribute("textContent"),
    )
    assert f"{METADATA_EVENT_IDS['A']}.after" in shared_description
    assert f"{METADATA_EVENT_IDS['B']}.before" in shared_description
    assert _related(driver) == ()
    assert cast(
        list[bool],
        driver.execute_script(
            """
            return [
              globalThis.__krtSuspendedKeyboard.isConnected,
              globalThis.__krtOwningPointer.isConnected
            ];
            """
        ),
    ) == [False, False]

    driver.execute_script(
        """
        const next = reduceSelection(
          selectionState,
          {
            kind: "activate",
            targetId: arguments[0],
            shiftKey: false,
            ctrlKey: false,
            metaKey: false
          },
          visibleEventIds(selectionState).slice()
        );
        selectionState = next;
        renderSelection(selectionState);
        """,
        METADATA_EVENT_IDS["A"],
    )
    _settle(driver)
    assert [
        column.get_attribute("data-roles")
        for column in driver.find_elements(By.CSS_SELECTOR, ".state-column")
    ] == [
        f"{METADATA_EVENT_IDS['A']}.before",
        f"{METADATA_EVENT_IDS['A']}.after",
    ]
    assert _related(driver) == ()
