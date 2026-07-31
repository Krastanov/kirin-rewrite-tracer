from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
from browser_harness import BrowserHarness
from kirin import ir
from kirin.dialects import py
from kirin.rewrite.abc import RewriteRule
from selenium.webdriver import ActionChains, Chrome
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from viewer_fixtures import (
    METADATA_ENTITY_IDS,
    METADATA_EVENT_IDS,
    METADATA_HOSTILE,
    METADATA_LONG_TEXT,
    METADATA_MULTILINE_TEXT,
    metadata_trace,
)

from kirin_rewrite_tracer import Trace, export_html, trace_rewrites
from kirin_rewrite_tracer._model import MetadataRecord


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


def _activate(driver: Chrome, event_id: str, *, shift: bool = False) -> None:
    button = driver.find_element(
        By.CSS_SELECTOR, f'.event-button[data-event-id="{event_id}"]'
    )
    if not shift:
        button.click()
        return
    (
        ActionChains(driver)
        .key_down(Keys.SHIFT)
        .click(button)
        .key_up(Keys.SHIFT)
        .perform()
    )


def _activate_without_input(
    driver: Chrome,
    event_id: str,
    *,
    shift: bool = False,
) -> None:
    driver.execute_script(
        """
        activateEvent(arguments[0], {
          shiftKey: arguments[1],
          ctrlKey: false,
          metaKey: false
        });
        """,
        event_id,
        shift,
    )


def _occurrences(
    driver: Chrome,
    column_index: int,
    entity_id: str,
) -> list[WebElement]:
    column = driver.find_elements(By.CSS_SELECTOR, ".state-column")[column_index]
    return column.find_elements(
        By.CSS_SELECTOR, f'.ssa-occurrence[data-entity-id="{entity_id}"]'
    )


def _click(driver: Chrome, target: WebElement) -> None:
    driver.execute_script("arguments[0].click();", target)


def _settle_scroll(driver: Chrome) -> None:
    driver.execute_async_script(
        """
        const done = arguments[0];
        requestAnimationFrame(() => requestAnimationFrame(done));
        """
    )


def _overlay_state(driver: Chrome) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        driver.execute_script(
            """
            const overlays = Array.from(
              document.querySelectorAll(".ssa-metadata-overlay")
            );
            const active = Array.from(
              document.querySelectorAll(
                '.ssa-occurrence[data-metadata-active="true"]'
              )
            );
            if (overlays.length === 0) {
              return {count: 0, activeCount: active.length};
            }
            const overlay = overlays[0];
            const readFields = (selector) => Array.from(
              overlay.querySelectorAll(selector)
            ).map(row => ({
              field: row.dataset.field,
              value: row.querySelector(":scope > dd").textContent
            }));
            const records = Array.from(
              overlay.querySelectorAll(".ssa-metadata-record")
            ).map(record => ({
              ordinal: Number(record.dataset.recordOrdinal),
              fields: readFields(
                `.ssa-metadata-record[data-record-ordinal="${
                  record.dataset.recordOrdinal
                }"] > .ssa-metadata-record-fields > .ssa-metadata-field`
              ),
              valueFields: readFields(
                `.ssa-metadata-record[data-record-ordinal="${
                  record.dataset.recordOrdinal
                }"] > .ssa-metadata-value > .ssa-metadata-field`
              ),
              absent:
                record.querySelector(".ssa-metadata-absent")?.textContent ?? null
            }));
            return {
              count: overlays.length,
              activeCount: active.length,
              activeOccurrenceIds:
                active.length === 1
                  ? active[0].dataset.occurrenceIds.split(" ")
                  : [],
              anchorOccurrenceIds:
                overlay.dataset.anchorOccurrenceIds.split(" "),
              bindingFields: Array.from(
                overlay.querySelectorAll(".ssa-metadata-binding")
              ).map(binding => Array.from(
                binding.querySelectorAll(":scope > .ssa-metadata-field")
              ).map(row => ({
                field: row.dataset.field,
                value: row.querySelector(":scope > dd").textContent
              }))),
              entity:
                overlay.querySelector(".ssa-metadata-inventory").dataset.entityId,
              identityFields: readFields(
                ".ssa-metadata-identity > .ssa-metadata-field"
              ),
              records,
              text: overlay.textContent,
              styleNames: Array.from(overlay.style).sort(),
              styleValues: Array.from(overlay.style)
                .sort()
                .map(name => overlay.style.getPropertyValue(name)),
              box: (() => {
                const value = overlay.getBoundingClientRect();
                return {
                  top: value.top,
                  right: value.right,
                  bottom: value.bottom,
                  left: value.left,
                  width: value.width,
                  height: value.height
                };
              })(),
              clientHeight: overlay.clientHeight,
              scrollTop: overlay.scrollTop,
              scrollHeight: overlay.scrollHeight,
              clientWidth: overlay.clientWidth,
              scrollWidth: overlay.scrollWidth,
              lastRecordBox: (() => {
                const record = overlay.querySelector(
                  ".ssa-metadata-record:last-child"
                );
                if (record === null) {
                  return null;
                }
                const value = record.getBoundingClientRect();
                return {top: value.top, bottom: value.bottom};
              })()
            };
            """
        ),
    )


def _field_values(fields: list[dict[str, str]]) -> dict[str, str]:
    return {field["field"]: field["value"] for field in fields}


def _browser_inventory(state: dict[str, Any]) -> tuple[tuple[object, ...], ...]:
    inventory: list[tuple[object, ...]] = []
    for record in state["records"]:
        record_fields = _field_values(record["fields"])
        value = (
            None
            if record["absent"] is not None
            else (
                _field_values(record["valueFields"])["qualified-type"],
                _field_values(record["valueFields"])["text"],
                _field_values(record["valueFields"])["path"],
            )
        )
        inventory.append(
            (
                record_fields["namespace"],
                record_fields["key"],
                record_fields["presence"],
                value,
            )
        )
    return tuple(inventory)


def _metadata_records(
    trace: Trace,
    snapshot_id: str,
    entity_id: str,
) -> tuple[MetadataRecord, ...]:
    index = trace.index()
    snapshot = index.snapshot(snapshot_id)
    return tuple(
        record
        for record in (
            index.metadata_record(metadata_id) for metadata_id in snapshot.metadata_ids
        )
        if record.owner_entity_id == entity_id
    )


def _record_fields(record: MetadataRecord) -> tuple[object, ...]:
    value = record.value
    return (
        record.namespace,
        record.key,
        record.presence,
        (None if value is None else (value.qualified_type, value.text, value.path)),
    )


def test_metadata_fixture_has_independent_snapshot_owner_oracles() -> None:
    trace = metadata_trace()
    entities = METADATA_ENTITY_IDS

    assert trace.snapshots_semantically_equal("snapshot-1", "snapshot-2")
    assert not trace.snapshots_semantically_equal("snapshot-0", "snapshot-1")
    survivor_before = _metadata_records(trace, "snapshot-0", entities["survivor"])
    assert tuple(_record_fields(record) for record in survivor_before) == (
        ("ssa", "name", "present", ("builtins.str", "'survivor'", "repr")),
        (
            "ssa",
            "type",
            "present",
            ("fixture.PrintableType", "!fixture.before", "printable"),
        ),
        ("hint", "phase", "present", ("builtins.str", "before", "repr")),
        (
            "hint",
            "long",
            "present",
            ("builtins.str", METADATA_LONG_TEXT, "repr"),
        ),
        (
            "hint",
            "multiline",
            "present",
            ("builtins.str", METADATA_MULTILINE_TEXT, "repr"),
        ),
        ("analysis", "value", "present", ("builtins.bool", "False", "repr")),
    )
    unnamed = _metadata_records(trace, "snapshot-0", entities["unnamed"])
    assert tuple(_record_fields(record) for record in unnamed) == (
        ("ssa", "name", "absent", None),
        (
            "ssa",
            "type",
            "present",
            ("fixture.EmptyPrintable", "", "printable"),
        ),
        ("analysis", "value", "present", ("builtins.str", "", "printable")),
    )
    expected_analysis = {
        "survivor": ("builtins.bool", "False", "repr"),
        "unnamed": ("builtins.str", "", "printable"),
        "block_argument": ("builtins.NoneType", "None", "repr"),
        "pair_left": ("builtins.dict", "{}", "repr"),
        "pair_right": ("builtins.bool", "True", "repr"),
        "similar": ("builtins.int", "0", "repr"),
    }
    for entity_label, expected_value in expected_analysis.items():
        analysis_records = tuple(
            record
            for record in _metadata_records(trace, "snapshot-0", entities[entity_label])
            if record.namespace == "analysis"
        )
        assert tuple(_record_fields(record) for record in analysis_records) == (
            ("analysis", "value", "present", expected_value),
        )
    external = _metadata_records(trace, "snapshot-0", entities["external"])
    assert all(record.namespace != "analysis" for record in external)
    assert _record_fields(external[-1]) == (
        "hint",
        METADATA_HOSTILE,
        "present",
        (
            "builtins.str",
            f"{METADATA_HOSTILE}\n{METADATA_LONG_TEXT}",
            "repr",
        ),
    )
    pair_left = _metadata_records(trace, "snapshot-0", entities["pair_left"])[1]
    pair_right = _metadata_records(trace, "snapshot-0", entities["pair_right"])[1]
    assert pair_left.value is not None
    assert pair_right.value is not None
    assert pair_left.value.text == pair_right.value.text == "same-type"
    assert pair_left.value.qualified_type == "fixture.EqualTextA"
    assert pair_right.value.qualified_type == "fixture.EqualTextB"

    for snapshot in trace.snapshots:
        for occurrence_id in snapshot.occurrence_ids:
            occurrence = trace.index().occurrence(occurrence_id)
            if occurrence.role not in {"definition", "reference"}:
                continue
            type_records = tuple(
                record
                for record in _metadata_records(
                    trace, snapshot.id, occurrence.entity_id
                )
                if record.namespace == "ssa" and record.key == "type"
            )
            assert len(type_records) == 1
            assert type_records[0].value is not None


@pytest.mark.browser  # type: ignore[untyped-decorator]
def test_every_rendered_occurrence_uses_its_exact_snapshot_owner_inventory(
    headed_chrome: BrowserHarness,
    tmp_path: Path,
) -> None:
    trace = metadata_trace()
    index = trace.index()
    event = index.event(METADATA_EVENT_IDS["A"])
    snapshot_ids = (event.before_snapshot_id, event.after_snapshot_id)
    assert snapshot_ids[1] is not None
    driver = _open_trace(
        headed_chrome,
        tmp_path,
        trace,
        "metadata-every-occurrence",
    )
    _activate(driver, event.id)
    _settle_scroll(driver)

    covered_entities: set[str] = set()
    covered_occurrences: list[str] = []
    for column_index, snapshot_id in enumerate(snapshot_ids):
        assert snapshot_id is not None
        snapshot = index.snapshot(snapshot_id)
        expected_occurrences = tuple(
            index.occurrence(occurrence_id)
            for occurrence_id in snapshot.occurrence_ids
            if index.occurrence(occurrence_id).role in {"definition", "reference"}
        )
        column = driver.find_elements(By.CSS_SELECTOR, ".state-column")[column_index]
        wrappers = column.find_elements(By.CSS_SELECTOR, ".ssa-occurrence")
        assert [
            wrapper.get_attribute("data-occurrence-id") for wrapper in wrappers
        ] == [occurrence.id for occurrence in expected_occurrences]

        for wrapper, occurrence in zip(wrappers, expected_occurrences, strict=True):
            covered_entities.add(occurrence.entity_id)
            covered_occurrences.append(occurrence.id)
            assert wrapper.get_attribute("data-entity-id") == occurrence.entity_id
            assert wrapper.get_attribute("data-occurrence-role") == occurrence.role
            assert (
                wrapper.get_attribute("textContent")
                == snapshot.text[occurrence.start : occurrence.end]
            )

            driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});",
                wrapper,
            )
            _settle_scroll(driver)
            ActionChains(driver).move_to_element(wrapper).perform()
            _settle_scroll(driver)
            assert _overlay_state(driver) == {"count": 0, "activeCount": 0}

            suffix = cast(
                dict[str, Any] | None,
                driver.execute_script(
                    """
                    const sibling = arguments[0].nextElementSibling;
                    if (
                      sibling === null ||
                      !sibling.classList.contains("ssa-metadata-suffix")
                    ) {
                      return null;
                    }
                    const computed = getComputedStyle(sibling);
                    return {
                      text: sibling.textContent,
                      attributes: Array.from(sibling.attributes).map(
                        attribute => [attribute.name, attribute.value]
                      ),
                      color: computed.color,
                      fontStyle: computed.fontStyle,
                      metadataToken: getComputedStyle(document.documentElement)
                        .getPropertyValue("--metadata").trim()
                    };
                    """,
                    wrapper,
                ),
            )
            if occurrence.role == "reference":
                assert suffix is None
            else:
                type_records = tuple(
                    record
                    for record in _metadata_records(
                        trace, snapshot.id, occurrence.entity_id
                    )
                    if record.namespace == "ssa" and record.key == "type"
                )
                assert len(type_records) == 1
                assert type_records[0].value is not None
                assert suffix == {
                    "attributes": [["class", "ssa-metadata-suffix"]],
                    "color": "rgb(125, 211, 252)",
                    "fontStyle": "italic",
                    "metadataToken": "#7dd3fc",
                    "text": f" ⟦{type_records[0].value.text}⟧",
                }

            _click(driver, wrapper)
            state = _overlay_state(driver)
            assert state["count"] == state["activeCount"] == 1
            assert state["activeOccurrenceIds"] == [occurrence.id]
            assert state["anchorOccurrenceIds"] == [occurrence.id]
            assert state["entity"] == occurrence.entity_id
            binding = _field_values(state["bindingFields"][0])
            assert binding == {
                "role": f"{event.id}.{snapshot.state}",
                "snapshot-id": snapshot.id,
                "occurrence-id": occurrence.id,
            }
            entity = index.entity(occurrence.entity_id)
            assert _field_values(state["identityFields"]) == {
                "entity-id": entity.id,
                "defining-owner-id": entity.defining_owner_id or "Absent",
            }
            assert _browser_inventory(state) == tuple(
                _record_fields(record)
                for record in _metadata_records(trace, snapshot.id, entity.id)
            )

            _click(driver, wrapper)
            assert _overlay_state(driver) == {"count": 0, "activeCount": 0}

    assert covered_entities == {
        entity.id for entity in trace.entities if entity.kind == "ssa"
    }
    assert covered_occurrences == [
        occurrence.id
        for snapshot_id in snapshot_ids
        if snapshot_id is not None
        for occurrence in (
            index.occurrence(occurrence_id)
            for occurrence_id in index.snapshot(snapshot_id).occurrence_ids
        )
        if occurrence.role in {"definition", "reference"}
    ]


@pytest.mark.browser  # type: ignore[untyped-decorator]
def test_definition_suffixes_and_owner_exact_overlay_lifecycle_are_inert(
    headed_chrome: BrowserHarness,
    tmp_path: Path,
) -> None:
    trace = metadata_trace()
    driver = _open_trace(
        headed_chrome,
        tmp_path,
        trace,
        "metadata-suffix-owner-lifecycle",
    )
    payload_before = driver.execute_script(
        """
        return [
          document.getElementById("trace-data").textContent,
          JSON.stringify(trace)
        ];
        """
    )
    _activate(driver, METADATA_EVENT_IDS["A"])
    _settle_scroll(driver)

    wrappers = cast(
        list[dict[str, Any]],
        driver.execute_script(
            """
            return Array.from(document.querySelectorAll(".ssa-occurrence")).map(
              wrapper => ({
                column: Number(wrapper.dataset.columnIndex),
                entity: wrapper.dataset.entityId,
                role: wrapper.dataset.occurrenceRole,
                text: wrapper.textContent,
                childRuns: wrapper.querySelectorAll(":scope > span").length,
                suffix:
                  wrapper.nextElementSibling?.classList.contains(
                    "ssa-metadata-suffix"
                  )
                    ? wrapper.nextElementSibling.textContent
                    : null,
                suffixIsChild:
                  wrapper.querySelector(".ssa-metadata-suffix") !== null
              })
            );
            """
        ),
    )
    definition_suffixes = [
        item["suffix"] for item in wrappers if item["role"] == "definition"
    ]
    assert all(value is not None for value in definition_suffixes)
    assert all(
        item["suffix"] is None for item in wrappers if item["role"] == "reference"
    )
    assert all(not item["suffixIsChild"] for item in wrappers)
    assert " ⟦!fixture.before⟧" in definition_suffixes
    assert " ⟦!fixture.after⟧" in definition_suffixes
    assert " ⟦⟧" in definition_suffixes
    assert " ⟦  spaced\n type  ⟧" in definition_suffixes
    assert f" ⟦{METADATA_HOSTILE}⟧" in definition_suffixes
    styled = next(
        item
        for item in wrappers
        if item["column"] == 0
        and item["entity"] == METADATA_ENTITY_IDS["survivor"]
        and item["role"] == "definition"
    )
    assert styled["text"] == "%survive😀"
    assert styled["childRuns"] == 2

    first = _occurrences(driver, 0, METADATA_ENTITY_IDS["survivor"])[0]
    ActionChains(driver).move_to_element(first).perform()
    assert _overlay_state(driver) == {"count": 0, "activeCount": 0}
    _click(driver, first)
    first_state = _overlay_state(driver)
    assert first_state["count"] == first_state["activeCount"] == 1
    assert first_state["entity"] == METADATA_ENTITY_IDS["survivor"]
    assert len(first_state["bindingFields"]) == 1
    assert [
        tuple((field["field"], field["value"]) for field in record["fields"])
        for record in first_state["records"]
    ] == [
        (
            ("namespace", "ssa"),
            ("key", "name"),
            ("presence", "present"),
        ),
        (
            ("namespace", "ssa"),
            ("key", "type"),
            ("presence", "present"),
        ),
        (
            ("namespace", "hint"),
            ("key", "phase"),
            ("presence", "present"),
        ),
        (
            ("namespace", "hint"),
            ("key", "long"),
            ("presence", "present"),
        ),
        (
            ("namespace", "hint"),
            ("key", "multiline"),
            ("presence", "present"),
        ),
        (
            ("namespace", "analysis"),
            ("key", "value"),
            ("presence", "present"),
        ),
    ]
    assert first_state["records"][1]["valueFields"] == [
        {"field": "qualified-type", "value": "fixture.PrintableType"},
        {"field": "text", "value": "!fixture.before"},
        {"field": "path", "value": "printable"},
    ]
    assert first_state["styleNames"] == [
        "--overlay-block-start",
        "--overlay-inline-start",
    ]
    assert all(value.endswith("px") for value in first_state["styleValues"])

    second = _occurrences(driver, 0, METADATA_ENTITY_IDS["survivor"])[1]
    _click(driver, second)
    second_state = _overlay_state(driver)
    assert second_state["count"] == second_state["activeCount"] == 1
    assert second_state["anchorOccurrenceIds"] != first_state["anchorOccurrenceIds"]
    assert second_state["entity"] == first_state["entity"]

    external = _occurrences(driver, 0, METADATA_ENTITY_IDS["external"])[0]
    _click(driver, external)
    external_state = _overlay_state(driver)
    assert external_state["count"] == external_state["activeCount"] == 1
    assert external_state["entity"] == METADATA_ENTITY_IDS["external"]
    assert all(
        dict((field["field"], field["value"]) for field in record["fields"])[
            "namespace"
        ]
        != "analysis"
        for record in external_state["records"]
    )
    assert METADATA_HOSTILE in external_state["text"]
    inert = cast(
        dict[str, Any],
        driver.execute_script(
            """
            const overlay = document.querySelector(".ssa-metadata-overlay");
            const styleElements = Array.from(document.querySelectorAll("[style]"));
            return {
              pwned: Object.prototype.hasOwnProperty.call(
                globalThis, "metadataPwned"
              ),
              interpreted: overlay.querySelector(
                "img,iframe,object,embed,link,form,a[href]"
              ) !== null,
              handlerAttributes: Array.from(overlay.querySelectorAll("*")).reduce(
                (count, element) => count + Array.from(element.attributes)
                  .filter(attribute =>
                    attribute.name.toLowerCase().startsWith("on")
                  ).length,
                0
              ),
              styleCount: styleElements.length,
              styleOwnerIsOverlay:
                styleElements.length === 1 && styleElements[0] === overlay
            };
            """
        ),
    )
    assert inert == {
        "handlerAttributes": 0,
        "interpreted": False,
        "pwned": False,
        "styleCount": 1,
        "styleOwnerIsOverlay": True,
    }

    _click(driver, external)
    assert _overlay_state(driver) == {"count": 0, "activeCount": 0}
    _click(driver, first)
    nested_value = driver.find_element(
        By.CSS_SELECTOR,
        ".ssa-metadata-overlay .ssa-metadata-exact-value",
    )
    _click(driver, nested_value)
    assert _overlay_state(driver)["count"] == 1
    blank_code = driver.find_elements(By.CSS_SELECTOR, ".trace-code")[0]
    _click(driver, blank_code)
    assert _overlay_state(driver) == {"count": 0, "activeCount": 0}

    nested_run = first.find_elements(By.CSS_SELECTOR, ":scope > span")[0]
    _click(driver, nested_run)
    assert _overlay_state(driver)["count"] == 1
    driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
    assert _overlay_state(driver) == {"count": 0, "activeCount": 0}
    driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
    assert _overlay_state(driver) == {"count": 0, "activeCount": 0}

    _click(driver, first)
    driver.find_element(
        By.CSS_SELECTOR,
        f'.event-button[data-event-id="{METADATA_EVENT_IDS["B"]}"]',
    ).click()
    assert _overlay_state(driver) == {"count": 0, "activeCount": 0}
    assert (
        driver.find_element(
            By.CSS_SELECTOR, '.event-button[aria-current="true"]'
        ).get_attribute("data-event-id")
        == METADATA_EVENT_IDS["B"]
    )
    _activate(driver, METADATA_EVENT_IDS["A"])
    assert _overlay_state(driver) == {"count": 0, "activeCount": 0}

    payload_after = driver.execute_script(
        """
        return [
          document.getElementById("trace-data").textContent,
          JSON.stringify(trace)
        ];
        """
    )
    assert payload_after == payload_before
    observations = headed_chrome.observations()
    assert observations.page_network_requests() == ()
    assert observations.csp_violations == ()
    assert not [
        entry for entry in observations.console if entry.level in {"SEVERE", "WARNING"}
    ]


@pytest.mark.browser  # type: ignore[untyped-decorator]
def test_shared_inventory_and_column_role_transitions_never_migrate_anchor(
    headed_chrome: BrowserHarness,
    tmp_path: Path,
) -> None:
    trace = metadata_trace()
    index = trace.index()
    event_a = index.event(METADATA_EVENT_IDS["A"])
    event_b = index.event(METADATA_EVENT_IDS["B"])
    assert event_a.after_snapshot_id is not None
    driver = _open_trace(
        headed_chrome,
        tmp_path,
        trace,
        "metadata-shared-lifecycle",
    )
    _activate(driver, METADATA_EVENT_IDS["A"])
    _settle_scroll(driver)
    single = _occurrences(driver, 1, METADATA_ENTITY_IDS["survivor"])[0]
    driver.execute_script(
        "arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});",
        single,
    )
    _settle_scroll(driver)
    _click(driver, single)
    assert _overlay_state(driver)["count"] == 1

    _activate_without_input(driver, METADATA_EVENT_IDS["B"], shift=True)
    assert _overlay_state(driver) == {"count": 0, "activeCount": 0}
    assert [
        column.get_attribute("data-roles")
        for column in driver.find_elements(By.CSS_SELECTOR, ".state-column")
    ] == [
        f"{METADATA_EVENT_IDS['A']}.before",
        f"{METADATA_EVENT_IDS['A']}.after|{METADATA_EVENT_IDS['B']}.before",
        f"{METADATA_EVENT_IDS['B']}.after",
    ]

    left_snapshot = index.snapshot(event_a.after_snapshot_id)
    right_snapshot = index.snapshot(event_b.before_snapshot_id)
    left_occurrences = tuple(
        index.occurrence(occurrence_id)
        for occurrence_id in left_snapshot.occurrence_ids
        if index.occurrence(occurrence_id).role in {"definition", "reference"}
    )
    right_occurrences = tuple(
        index.occurrence(occurrence_id)
        for occurrence_id in right_snapshot.occurrence_ids
        if index.occurrence(occurrence_id).role in {"definition", "reference"}
    )
    shared_column = driver.find_elements(By.CSS_SELECTOR, ".state-column")[1]
    shared_wrappers = shared_column.find_elements(By.CSS_SELECTOR, ".ssa-occurrence")
    assert len(shared_wrappers) == len(left_occurrences) == len(right_occurrences)
    retained_binding_ids: list[str] = []
    expected_suffix_count = 0
    for wrapper, left, right in zip(
        shared_wrappers,
        left_occurrences,
        right_occurrences,
        strict=True,
    ):
        assert (left.entity_id, left.role, left.start, left.end) == (
            right.entity_id,
            right.role,
            right.start,
            right.end,
        )
        binding_ids = cast(str, wrapper.get_attribute("data-occurrence-ids")).split(" ")
        assert binding_ids == [left.id, right.id]
        retained_binding_ids.extend(binding_ids)
        sibling_is_suffix = cast(
            bool,
            driver.execute_script(
                """
                return arguments[0].nextElementSibling?.classList.contains(
                  "ssa-metadata-suffix"
                ) ?? false;
                """,
                wrapper,
            ),
        )
        assert sibling_is_suffix is (left.role == "definition")
        expected_suffix_count += int(left.role == "definition")
    assert len(retained_binding_ids) == len(set(retained_binding_ids))
    assert set(retained_binding_ids) == {
        occurrence.id for occurrence in (*left_occurrences, *right_occurrences)
    }
    assert (
        len(shared_column.find_elements(By.CSS_SELECTOR, ".ssa-metadata-suffix"))
        == expected_suffix_count
    )

    shared = next(
        wrapper
        for wrapper in shared_wrappers
        if wrapper.get_attribute("data-entity-id") == METADATA_ENTITY_IDS["survivor"]
        and wrapper.get_attribute("data-occurrence-role") == "definition"
    )
    assert (
        shared.find_elements(
            By.XPATH,
            "following-sibling::*[1][contains(@class, 'ssa-metadata-suffix')]",
        )[0].get_attribute("textContent")
        == " ⟦!fixture.after⟧"
    )
    driver.execute_script(
        "arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});",
        shared,
    )
    _settle_scroll(driver)
    _click(driver, shared)
    shared_state = _overlay_state(driver)
    assert shared_state["count"] == shared_state["activeCount"] == 1
    shared_left = left_occurrences[0]
    shared_right = right_occurrences[0]
    assert (
        shared_left.entity_id
        == shared_right.entity_id
        == METADATA_ENTITY_IDS["survivor"]
    )
    assert [_field_values(binding) for binding in shared_state["bindingFields"]] == [
        {
            "role": f"{METADATA_EVENT_IDS['A']}.after",
            "snapshot-id": left_snapshot.id,
            "occurrence-id": shared_left.id,
        },
        {
            "role": f"{METADATA_EVENT_IDS['B']}.before",
            "snapshot-id": right_snapshot.id,
            "occurrence-id": shared_right.id,
        },
    ]
    assert shared_state["anchorOccurrenceIds"] == [shared_left.id, shared_right.id]
    left_inventory = tuple(
        _record_fields(record)
        for record in _metadata_records(
            trace, left_snapshot.id, METADATA_ENTITY_IDS["survivor"]
        )
    )
    right_inventory = tuple(
        _record_fields(record)
        for record in _metadata_records(
            trace, right_snapshot.id, METADATA_ENTITY_IDS["survivor"]
        )
    )
    assert left_inventory == right_inventory
    assert _browser_inventory(shared_state) == left_inventory
    assert driver.execute_script(
        """
        return [
          document.querySelectorAll(".ssa-metadata-inventory").length,
          document.querySelectorAll(".ssa-metadata-record").length
        ];
        """
    ) == [1, len(left_inventory)]
    assert "metadata-" not in shared_state["text"]
    assert driver.execute_script(
        """
            const anchor = document.querySelector(
              '.ssa-occurrence[data-metadata-active="true"]'
            );
            return [
              anchor.querySelectorAll(".ssa-metadata-suffix").length,
              anchor.nextElementSibling.classList.contains(
                "ssa-metadata-suffix"
              )
            ];
            """
    ) == [0, True]

    _activate_without_input(driver, METADATA_EVENT_IDS["A"])
    assert _overlay_state(driver) == {"count": 0, "activeCount": 0}
    assert len(driver.find_elements(By.CSS_SELECTOR, ".state-column")) == 2
    _activate_without_input(driver, METADATA_EVENT_IDS["B"], shift=True)
    assert _overlay_state(driver) == {"count": 0, "activeCount": 0}

    shared_after_rebuild = _occurrences(driver, 1, METADATA_ENTITY_IDS["survivor"])[0]
    driver.execute_script(
        "arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});",
        shared_after_rebuild,
    )
    _settle_scroll(driver)
    _click(driver, shared_after_rebuild)
    assert _overlay_state(driver)["count"] == 1
    driver.execute_script(
        """
        const columns = document.querySelector(".ssa-columns");
        const replaceChildren = columns.replaceChildren.bind(columns);
        columns.replaceChildren = (...children) => {
          globalThis.__metadataActiveAtColumnRebuild = document.querySelectorAll(
            '.ssa-occurrence[data-metadata-active="true"]'
          ).length;
          return replaceChildren(...children);
        };
        """
    )
    driver.find_element(By.CSS_SELECTOR, ".clear-selection").click()
    assert _overlay_state(driver) == {"count": 0, "activeCount": 0}
    assert (
        driver.execute_script("return globalThis.__metadataActiveAtColumnRebuild;") == 0
    )
    assert driver.find_elements(By.CSS_SELECTOR, ".state-column") == []
    _activate_without_input(driver, METADATA_EVENT_IDS["A"])
    assert _overlay_state(driver) == {"count": 0, "activeCount": 0}


@pytest.mark.browser  # type: ignore[untyped-decorator]
def test_overlay_measured_geometry_and_scroll_resize_lifecycle(
    headed_chrome: BrowserHarness,
    tmp_path: Path,
) -> None:
    driver = _open_trace(
        headed_chrome,
        tmp_path,
        metadata_trace(),
        "metadata-geometry",
    )
    headed_chrome.set_css_viewport(640, 480)
    _activate(driver, METADATA_EVENT_IDS["A"])
    anchor = _occurrences(driver, 0, METADATA_ENTITY_IDS["survivor"])[0]
    driver.execute_script(
        "arguments[0].scrollIntoView({block: 'start', inline: 'nearest'});",
        anchor,
    )
    _settle_scroll(driver)
    _click(driver, anchor)
    state = _overlay_state(driver)
    anchor_box = cast(
        dict[str, float],
        driver.execute_script(
            """
            const box = arguments[0].getBoundingClientRect();
            return {top: box.top, right: box.right, bottom: box.bottom, left: box.left};
            """,
            anchor,
        ),
    )
    assert state["box"]["top"] == pytest.approx(anchor_box["bottom"] + 8, abs=0.1)
    assert state["box"]["left"] >= 8
    assert state["box"]["right"] <= 632
    assert state["box"]["top"] >= 0
    assert state["box"]["bottom"] <= 480
    assert state["box"]["width"] <= 576
    assert state["box"]["height"] <= 208
    assert state["scrollHeight"] > state["clientHeight"]
    assert state["scrollWidth"] > state["clientWidth"]

    driver.execute_script(
        """
        const overlay = document.querySelector(".ssa-metadata-overlay");
        overlay.scrollTop = overlay.scrollHeight;
        overlay.scrollLeft = overlay.scrollWidth;
        """,
    )
    WebDriverWait(driver, 2).until(
        lambda browser: browser.execute_script(
            """
            const overlay = document.querySelector(".ssa-metadata-overlay");
            return (
              overlay !== null &&
              overlay.scrollTop > 0 &&
              overlay.scrollLeft > 0
            );
            """
        )
    )
    internally_scrolled = _overlay_state(driver)
    assert internally_scrolled["count"] == 1
    assert internally_scrolled["scrollTop"] > 0
    assert (
        internally_scrolled["lastRecordBox"]["bottom"]
        >= internally_scrolled["box"]["top"]
    )
    assert (
        internally_scrolled["lastRecordBox"]["bottom"]
        <= internally_scrolled["box"]["bottom"] + 1.5
    )
    horizontal_reachability = cast(
        dict[str, float],
        driver.execute_script(
            """
            const overlay = document.querySelector(".ssa-metadata-overlay");
            const values = Array.from(
              overlay.querySelectorAll(".ssa-metadata-exact-value")
            );
            const longest = values.reduce(
              (current, candidate) =>
                candidate.textContent.length > current.textContent.length
                  ? candidate
                  : current
            );
            const overlayBox = overlay.getBoundingClientRect();
            const valueBox = longest.getBoundingClientRect();
            return {
              scrollLeft: overlay.scrollLeft,
              maximumScrollLeft: overlay.scrollWidth - overlay.clientWidth,
              overlayLeft: overlayBox.left,
              overlayRight: overlayBox.right,
              valueRight: valueBox.right
            };
            """
        ),
    )
    assert horizontal_reachability["scrollLeft"] == pytest.approx(
        horizontal_reachability["maximumScrollLeft"], abs=1
    )
    assert (
        horizontal_reachability["overlayLeft"]
        <= horizontal_reachability["valueRight"]
        <= horizontal_reachability["overlayRight"]
    )

    overlay_height = cast(float, state["box"]["height"])
    driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
    driver.execute_script(
        """
        const anchor = arguments[0];
        const original = anchor.getBoundingClientRect.bind(anchor);
        globalThis.__metadataOriginalRect = original;
        const height = arguments[1];
        anchor.getBoundingClientRect = () => ({
          top: height + 12,
          right: 120,
          bottom: height + 28,
          left: 24,
          width: 96,
          height: 16,
          x: 24,
          y: height + 12,
          toJSON() { return this; }
        });
        anchor.click();
        """,
        anchor,
        overlay_height,
    )
    near_top = _overlay_state(driver)
    assert 0 <= near_top["box"]["top"] <= 7
    patched_anchor = cast(
        dict[str, float],
        driver.execute_script(
            """
            const box = arguments[0].getBoundingClientRect();
            return {top: box.top, bottom: box.bottom};
            """,
            anchor,
        ),
    )
    assert patched_anchor["top"] - near_top["box"]["bottom"] == pytest.approx(
        8, abs=0.1
    )

    driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
    driver.execute_script(
        """
        const anchor = arguments[0];
        const height = arguments[1];
        anchor.getBoundingClientRect = () => ({
          top: height + 40,
          right: 16,
          bottom: height + 56,
          left: -40,
          width: 56,
          height: 16,
          x: -40,
          y: height + 40,
          toJSON() { return this; }
        });
        anchor.click();
        """,
        anchor,
        overlay_height,
    )
    left_edge = _overlay_state(driver)
    assert left_edge["box"]["left"] == pytest.approx(8, abs=0.1)
    assert left_edge["box"]["right"] <= 632

    driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
    driver.execute_script(
        """
        const anchor = arguments[0];
        const height = arguments[1];
        const viewportHeight = document.documentElement.clientHeight;
        const bottom = viewportHeight - 12 - height;
        anchor.getBoundingClientRect = () => ({
          top: 100,
          right: 632,
          bottom,
          left: 620,
          width: 12,
          height: bottom - 100,
          x: 620,
          y: 100,
          toJSON() { return this; }
        });
        anchor.click();
        """,
        anchor,
        overlay_height,
    )
    near_bottom = _overlay_state(driver)
    assert near_bottom["box"]["bottom"] == pytest.approx(476, abs=0.2)
    assert near_bottom["box"]["right"] <= 632
    assert near_bottom["box"]["top"] > 0

    driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
    driver.execute_script(
        """
        arguments[0].getBoundingClientRect = globalThis.__metadataOriginalRect;
        """,
        anchor,
    )
    workspace = driver.find_element(By.CSS_SELECTOR, ".workspace")
    driver.execute_script("arguments[0].scrollLeft = 0;", workspace)
    _settle_scroll(driver)
    _click(driver, anchor)
    assert _overlay_state(driver)["count"] == 1
    workspace_positions = cast(
        list[float],
        driver.execute_script(
            """
            const workspace = arguments[0];
            const before = workspace.scrollLeft;
            workspace.scrollLeft = Math.min(
              workspace.scrollWidth - workspace.clientWidth,
              before + 64
            );
            return [before, workspace.scrollLeft];
            """,
            workspace,
        ),
    )
    assert workspace_positions[1] > workspace_positions[0]
    WebDriverWait(driver, 2).until(
        lambda browser: (
            not browser.find_elements(By.CSS_SELECTOR, ".ssa-metadata-overlay")
        )
    )

    driver.execute_script(
        "arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});",
        anchor,
    )
    _settle_scroll(driver)
    _click(driver, anchor)
    assert _overlay_state(driver)["count"] == 1
    page_positions = cast(
        list[float],
        driver.execute_script(
            """
            const before = window.scrollY;
            const maximum =
              document.documentElement.scrollHeight -
              document.documentElement.clientHeight;
            if (maximum <= 0) {
              return [before, before, maximum];
            }
            const target = before < maximum ? before + 1 : before - 1;
            window.scrollTo(window.scrollX, target);
            return [before, window.scrollY, maximum];
            """
        ),
    )
    assert page_positions[2] > 0
    assert page_positions[1] != page_positions[0]
    WebDriverWait(driver, 2).until(
        lambda browser: (
            not browser.find_elements(By.CSS_SELECTOR, ".ssa-metadata-overlay")
        )
    )

    driver.execute_script(
        "arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});",
        anchor,
    )
    _settle_scroll(driver)
    _click(driver, anchor)
    assert _overlay_state(driver)["count"] == 1
    headed_chrome.set_css_viewport(641, 480)
    assert _overlay_state(driver) == {"count": 0, "activeCount": 0}


class _PostTraceSentinel:
    pass


def _qualified_type_label(value: object) -> str:
    return f"{type(value).__module__}.{type(value).__qualname__}"


def _captured_trace_with_mutated_live_type() -> tuple[
    Trace,
    str,
    tuple[tuple[object, ...], ...],
    str,
    str,
    ir.Statement,
    ir.Region,
]:
    source = py.Constant(7)
    source.result.name = "captured"
    source.result.hints["phase"] = ir.PyAttr("captured-hint")
    root = ir.Region(ir.Block([source]))
    captured_type = source.result.type
    captured_hint = source.result.hints["phase"]
    direct_type_text = captured_type.print_str(end="")
    expected_inventory = (
        (
            "ssa",
            "name",
            "present",
            ("builtins.str", "'captured'", "repr"),
        ),
        (
            "ssa",
            "type",
            "present",
            (
                _qualified_type_label(captured_type),
                direct_type_text,
                "printable",
            ),
        ),
        (
            "hint",
            "phase",
            "present",
            (
                _qualified_type_label(captured_hint),
                captured_hint.print_str(end=""),
                "printable",
            ),
        ),
        (
            "analysis",
            "value",
            "present",
            ("builtins.bool", "False", "repr"),
        ),
    )
    with trace_rewrites(analysis={source.result: False}) as recorder:
        RewriteRule().rewrite(root)
    trace = recorder.trace
    before = trace.index().snapshot(trace.events[0].before_snapshot_id)
    type_record = next(
        record
        for record in (
            trace.index().metadata_record(metadata_id)
            for metadata_id in before.metadata_ids
        )
        if record.namespace == "ssa" and record.key == "type"
    )
    assert type_record.value is not None
    assert type_record.value.text == direct_type_text
    owner_entity_id = type_record.owner_entity_id
    assert (
        tuple(
            _record_fields(record)
            for record in _metadata_records(trace, before.id, owner_entity_id)
        )
        == expected_inventory
    )

    source.result.type = ir.attrs.types.PyClass(_PostTraceSentinel)
    sentinel = source.result.type.print_str(end="")
    assert sentinel != direct_type_text
    return (
        trace,
        owner_entity_id,
        expected_inventory,
        f" ⟦{direct_type_text}⟧",
        sentinel,
        source,
        root,
    )


@pytest.mark.browser  # type: ignore[untyped-decorator]
def test_real_capture_survives_later_live_type_mutation_in_suffix_and_overlay(
    headed_chrome: BrowserHarness,
    tmp_path: Path,
) -> None:
    (
        trace,
        owner_entity_id,
        expected_inventory,
        expected_suffix,
        sentinel,
        live_source,
        live_root,
    ) = _captured_trace_with_mutated_live_type()
    driver = _open_trace(
        headed_chrome,
        tmp_path,
        trace,
        "metadata-real-capture-freeze",
    )
    _activate(driver, trace.events[0].id)
    definition = next(
        occurrence
        for occurrence in _occurrences(driver, 0, owner_entity_id)
        if occurrence.get_attribute("data-occurrence-role") == "definition"
    )
    suffix = definition.find_element(
        By.XPATH,
        "following-sibling::*[1][contains(@class, 'ssa-metadata-suffix')]",
    )
    assert suffix.get_attribute("textContent") == expected_suffix
    _click(driver, definition)
    state = _overlay_state(driver)
    assert _browser_inventory(state) == expected_inventory
    body_text = cast(
        str,
        driver.find_element(By.TAG_NAME, "body").get_attribute("textContent"),
    )
    assert sentinel not in body_text
    assert live_source.results[0].type.print_str(end="") == sentinel
    assert tuple(live_root.blocks[0].stmts) == (live_source,)
    observations = headed_chrome.observations()
    assert observations.page_network_requests() == ()
    assert observations.csp_violations == ()
