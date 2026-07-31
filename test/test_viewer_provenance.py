from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
from browser_harness import BrowserHarness
from selenium.webdriver import ActionChains, Chrome
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from viewer_fixtures import (
    COARSE_PROVENANCE_ENTITY_IDS,
    COARSE_PROVENANCE_EVENT_ID,
    COARSE_PROVENANCE_RELATION_IDS,
    PIPELINE_ENTITY_IDS,
    PIPELINE_EVENT_IDS,
    PIPELINE_RELATION_IDS,
    coarse_provenance_trace,
    pipeline_provenance_trace,
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


def _activate(
    driver: Chrome,
    event_id: str,
    *,
    shift: bool = False,
) -> None:
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


def _clear(driver: Chrome) -> None:
    driver.find_element(By.CSS_SELECTOR, ".clear-selection").click()


def _occurrences(
    driver: Chrome,
    column_index: int,
    entity_id: str,
) -> list[WebElement]:
    column = driver.find_elements(By.CSS_SELECTOR, ".state-column")[column_index]
    return column.find_elements(
        By.CSS_SELECTOR, f'.ssa-occurrence[data-entity-id="{entity_id}"]'
    )


def _related(driver: Chrome) -> list[dict[str, Any]]:
    return cast(
        list[dict[str, Any]],
        driver.execute_script(
            """
            return Array.from(
              document.querySelectorAll(
                '.ssa-occurrence[data-provenance-related="true"]'
              )
            ).map(target => ({
              column: Number(target.dataset.columnIndex),
              entity: target.dataset.entityId,
              occurrenceIds: target.dataset.occurrenceIds.split(" "),
              identity: target.dataset.provenanceIdentity === "true",
              relationIds: target.dataset.provenanceRelationIds
                ? target.dataset.provenanceRelationIds.split(" ")
                : [],
              relationFacts: target.dataset.provenanceRelationIds
                ? target.dataset.provenanceRelationIds.split(" ").map(id => {
                    const relation = trace.relations.find(item => item.id === id);
                    const operation = trace.operations.find(
                      item => item.id === relation.mutation_operation_id
                    );
                    return {
                      id: relation.id,
                      source: relation.source_entity_id,
                      destination: relation.destination_entity_id,
                      operation: operation.id,
                      owner: operation.owner_event_id
                    };
                  })
                : []
            }));
            """
        ),
    )


def _related_summary(driver: Chrome) -> list[tuple[int, str, bool, tuple[str, ...]]]:
    return [
        (
            cast(int, item["column"]),
            cast(str, item["entity"]),
            cast(bool, item["identity"]),
            tuple(cast(list[str], item["relationIds"])),
        )
        for item in _related(driver)
    ]


def _hover(
    driver: Chrome,
    column_index: int,
    entity_id: str,
    *,
    occurrence_index: int = 0,
) -> WebElement:
    source = _occurrences(driver, column_index, entity_id)[occurrence_index]
    ActionChains(driver).move_to_element(source).perform()
    return source


def _end_hover(driver: Chrome) -> None:
    summary = driver.find_element(By.ID, "trace-summary")
    ActionChains(driver).move_to_element(summary).perform()
    assert _related(driver) == []


def _payload_state(driver: Chrome) -> tuple[str, str]:
    return cast(
        tuple[str, str],
        driver.execute_script(
            """
            return [
              document.getElementById("trace-data").textContent,
              JSON.stringify(trace)
            ];
            """
        ),
    )


def test_canonical_provenance_fixtures_have_independent_owner_oracle() -> None:
    coarse = coarse_provenance_trace()
    entities = COARSE_PROVENANCE_ENTITY_IDS
    relation_ids = COARSE_PROVENANCE_RELATION_IDS
    operation_by_id = {operation.id: operation for operation in coarse.operations}
    relation_by_id = {relation.id: relation for relation in coarse.relations}

    expected = {
        relation_ids["split_left"]: (
            entities["split_source"],
            entities["split_destination_left"],
            COARSE_PROVENANCE_EVENT_ID,
        ),
        relation_ids["split_right"]: (
            entities["split_source"],
            entities["split_destination_right"],
            COARSE_PROVENANCE_EVENT_ID,
        ),
        relation_ids["merge_left"]: (
            entities["merge_source_left"],
            entities["merge_destination"],
            COARSE_PROVENANCE_EVENT_ID,
        ),
        relation_ids["merge_right"]: (
            entities["merge_source_right"],
            entities["merge_destination"],
            COARSE_PROVENANCE_EVENT_ID,
        ),
        relation_ids["depth_1"]: (
            entities["depth_1_source"],
            entities["depth_1_destination"],
            "event-2",
        ),
        relation_ids["depth_2"]: (
            entities["depth_2_source"],
            entities["depth_2_destination"],
            "event-3",
        ),
        relation_ids["depth_5"]: (
            entities["depth_5_source"],
            entities["depth_5_destination"],
            "event-6",
        ),
        relation_ids["incomplete_child"]: (
            entities["incomplete_child_source"],
            entities["incomplete_child_destination"],
            "event-7",
        ),
        relation_ids["ancestor"]: (
            entities["ancestor_source"],
            entities["ancestor_destination"],
            "event-0",
        ),
        relation_ids["sibling"]: (
            entities["sibling_source"],
            entities["sibling_destination"],
            "event-8",
        ),
    }
    for relation_id, (source_id, destination_id, owner_event_id) in expected.items():
        relation = relation_by_id[relation_id]
        operation = operation_by_id[relation.mutation_operation_id]
        assert (
            relation.source_entity_id,
            relation.destination_entity_id,
            operation.owner_event_id,
        ) == (source_id, destination_id, owner_event_id)

    incomplete_child = coarse.index().event("event-7")
    incomplete_child_operation = operation_by_id[
        relation_by_id[relation_ids["incomplete_child"]].mutation_operation_id
    ]
    assert incomplete_child.completion == "incomplete"
    assert incomplete_child.after_snapshot_id is None
    assert incomplete_child_operation.outcome == "completed"
    assert coarse.effects[0].mutation_operation_id == "operation-19"
    assert operation_by_id["operation-17"].outcome == "completed"
    assert coarse.index().relations_from(entities["zero_use_source"]) == ()
    assert operation_by_id["operation-18"].outcome == "incomplete"
    assert coarse.index().relations_from(entities["incomplete_operation_source"]) == ()

    pipeline = pipeline_provenance_trace()
    pipeline_index = pipeline.index()
    assert pipeline.snapshots_semantically_equal("snapshot-1", "snapshot-2")
    assert pipeline.snapshots_semantically_equal("snapshot-3", "snapshot-4")
    assert not pipeline.snapshots_semantically_equal("snapshot-7", "snapshot-8")
    assert pipeline_index.event(PIPELINE_EVENT_IDS["F"]).after_snapshot_id is None
    assert tuple(relation.id for relation in pipeline.relations) == tuple(
        PIPELINE_RELATION_IDS.values()
    )
    pipeline_operations = {operation.id: operation for operation in pipeline.operations}
    pipeline_relations = {relation.id: relation for relation in pipeline.relations}
    assert {
        label: pipeline_operations[
            pipeline_relations[relation_id].mutation_operation_id
        ].owner_event_id
        for label, relation_id in PIPELINE_RELATION_IDS.items()
        if label.startswith("handoff_")
    } == {
        "handoff_owner_d": PIPELINE_EVENT_IDS["D"],
        "handoff_owner_e": PIPELINE_EVENT_IDS["E"],
        "handoff_owner_d_child": PIPELINE_EVENT_IDS["D_CHILD"],
        "handoff_owner_d_ancestor": PIPELINE_EVENT_IDS["C"],
    }
    incomplete_event = pipeline_index.event(PIPELINE_EVENT_IDS["F"])
    successor_event = pipeline_index.event(PIPELINE_EVENT_IDS["G"])
    incomplete_relation = pipeline_relations[
        PIPELINE_RELATION_IDS["incomplete_event_must_not_cross"]
    ]
    incomplete_operation = pipeline_operations[
        incomplete_relation.mutation_operation_id
    ]
    assert incomplete_event.completion == "incomplete"
    assert incomplete_event.after_snapshot_id is None
    assert incomplete_operation.owner_event_id == incomplete_event.id
    assert incomplete_operation.outcome == "completed"
    assert (
        incomplete_relation.source_entity_id
        == PIPELINE_ENTITY_IDS["incomplete_relation_source"]
    )
    assert (
        incomplete_relation.destination_entity_id
        == PIPELINE_ENTITY_IDS["incomplete_relation_destination"]
    )
    assert pipeline_index.occurrences_for(
        incomplete_relation.source_entity_id,
        incomplete_event.before_snapshot_id,
    )
    assert not pipeline_index.occurrences_for(
        incomplete_relation.destination_entity_id,
        incomplete_event.before_snapshot_id,
    )
    assert pipeline_index.occurrences_for(
        incomplete_relation.destination_entity_id,
        successor_event.before_snapshot_id,
    )
    assert successor_event.after_snapshot_id is not None
    assert pipeline_index.occurrences_for(
        incomplete_relation.destination_entity_id,
        successor_event.after_snapshot_id,
    )


@pytest.mark.browser  # type: ignore[untyped-decorator]
def test_coarse_parent_provenance_is_exact_bidirectional_and_owner_scoped(
    headed_chrome: BrowserHarness,
    tmp_path: Path,
) -> None:
    driver = _open_trace(
        headed_chrome,
        tmp_path,
        coarse_provenance_trace(),
        "provenance-coarse-parent",
    )
    payload_before = _payload_state(driver)
    entities = COARSE_PROVENANCE_ENTITY_IDS
    relations = COARSE_PROVENANCE_RELATION_IDS
    _activate(driver, COARSE_PROVENANCE_EVENT_ID)

    columns = driver.find_elements(By.CSS_SELECTOR, ".state-column")
    assert [column.get_attribute("data-roles") for column in columns] == [
        f"{COARSE_PROVENANCE_EVENT_ID}.before",
        f"{COARSE_PROVENANCE_EVENT_ID}.after",
    ]
    wrappers = driver.find_elements(By.CSS_SELECTOR, ".ssa-occurrence")
    assert wrappers
    assert {wrapper.tag_name for wrapper in wrappers} == {"button"}
    assert {wrapper.get_attribute("type") for wrapper in wrappers} == {"button"}
    assert all(wrapper.get_attribute("role") is None for wrapper in wrappers)
    assert all(
        wrapper.get_attribute("data-occurrence-role")
        in {
            "definition",
            "reference",
        }
        for wrapper in wrappers
    )
    survivor = _occurrences(driver, 0, entities["survivor"])[0]
    assert len(survivor.find_elements(By.CSS_SELECTOR, ":scope > span")) == 2
    assert survivor.text == "%stay😀"

    _hover(driver, 0, entities["survivor"])
    assert _related_summary(driver) == [
        (1, entities["survivor"], True, ()),
        (1, entities["survivor"], True, ()),
    ]
    _end_hover(driver)

    _hover(driver, 0, entities["split_source"])
    assert _related_summary(driver) == [
        (1, entities["split_destination_left"], False, (relations["split_left"],)),
        (1, entities["split_destination_left"], False, (relations["split_left"],)),
        (
            1,
            entities["split_destination_right"],
            False,
            (relations["split_right"],),
        ),
    ]
    related_target = driver.find_element(
        By.CSS_SELECTOR, '.ssa-occurrence[data-provenance-related="true"]'
    )
    assert "rgb(251, 191, 36)" in related_target.value_of_css_property("box-shadow")
    _end_hover(driver)

    _hover(driver, 1, entities["merge_destination"])
    assert _related_summary(driver) == [
        (0, entities["merge_source_left"], False, (relations["merge_left"],)),
        (0, entities["merge_source_left"], False, (relations["merge_left"],)),
        (0, entities["merge_source_right"], False, (relations["merge_right"],)),
    ]
    _end_hover(driver)

    _hover(driver, 0, entities["duplicate_source"])
    duplicate = _related(driver)
    assert _related_summary(driver) == [
        (
            1,
            entities["duplicate_destination"],
            False,
            (relations["duplicate_first"], relations["duplicate_second"]),
        )
    ]
    assert duplicate[0]["relationFacts"] == [
        {
            "id": relations["duplicate_first"],
            "source": entities["duplicate_source"],
            "destination": entities["duplicate_destination"],
            "operation": "operation-4",
            "owner": COARSE_PROVENANCE_EVENT_ID,
        },
        {
            "id": relations["duplicate_second"],
            "source": entities["duplicate_source"],
            "destination": entities["duplicate_destination"],
            "operation": "operation-5",
            "owner": COARSE_PROVENANCE_EVENT_ID,
        },
    ]
    _end_hover(driver)

    for source_label, destination_label, relation_label in (
        ("depth_1_source", "depth_1_destination", "depth_1"),
        ("depth_2_source", "depth_2_destination", "depth_2"),
        ("depth_5_source", "depth_5_destination", "depth_5"),
    ):
        _hover(driver, 0, entities[source_label])
        assert _related_summary(driver) == [
            (1, entities[destination_label], False, (relations[relation_label],))
        ]
        _end_hover(driver)

    _hover(driver, 1, entities["incomplete_child_destination"])
    assert _related_summary(driver) == [
        (
            0,
            entities["incomplete_child_source"],
            False,
            (relations["incomplete_child"],),
        )
    ]
    incomplete_fact = _related(driver)[0]["relationFacts"][0]
    assert incomplete_fact["owner"] == "event-7"
    assert incomplete_fact["operation"] == "operation-9"
    _end_hover(driver)

    for column_index, entity_label in (
        (0, "ancestor_source"),
        (0, "sibling_source"),
        (0, "missing_source"),
        (0, "reversed_destination"),
        (1, "reversed_source"),
        (0, "zero_use_source"),
        (0, "incomplete_operation_source"),
        (0, "similar_before"),
    ):
        _hover(driver, column_index, entities[entity_label])
        assert _related(driver) == []
        _end_hover(driver)

    _hover(driver, 0, entities["path_source"])
    assert _related_summary(driver) == [
        (1, entities["path_middle"], False, (relations["path_first"],))
    ]
    assert all(
        item[1] != entities["path_destination"] for item in _related_summary(driver)
    )
    _end_hover(driver)
    _hover(driver, 1, entities["path_destination"])
    assert _related_summary(driver) == [
        (0, entities["path_middle"], False, (relations["path_second"],))
    ]
    assert all(item[1] != entities["path_source"] for item in _related_summary(driver))
    _end_hover(driver)

    facts = cast(
        dict[str, Any],
        driver.execute_script(
            """
            return JSON.parse(document.getElementById("selected-facts").textContent);
            """
        ),
    )
    owned_relation_ids = {
        relation["id"] for relation in facts["canonical"]["relations"]
    }
    assert relations["depth_1"] not in owned_relation_ids
    assert relations["depth_2"] not in owned_relation_ids
    assert relations["depth_5"] not in owned_relation_ids
    assert relations["incomplete_child"] not in owned_relation_ids
    assert relations["split_left"] in owned_relation_ids
    assert _payload_state(driver) == payload_before


@pytest.mark.browser  # type: ignore[untyped-decorator]
def test_shared_and_separate_edges_are_side_isolated_and_barrier_scoped(
    headed_chrome: BrowserHarness,
    tmp_path: Path,
) -> None:
    driver = _open_trace(
        headed_chrome,
        tmp_path,
        pipeline_provenance_trace(),
        "provenance-edge-policies",
    )
    entities = PIPELINE_ENTITY_IDS
    relations = PIPELINE_RELATION_IDS
    payload_before = _payload_state(driver)

    _activate(driver, PIPELINE_EVENT_IDS["A"])
    _activate(driver, PIPELINE_EVENT_IDS["C"], shift=True)
    columns = driver.find_elements(By.CSS_SELECTOR, ".state-column")
    assert [column.get_attribute("data-roles") for column in columns] == [
        f"{PIPELINE_EVENT_IDS['A']}.before",
        f"{PIPELINE_EVENT_IDS['A']}.after|{PIPELINE_EVENT_IDS['B']}.before",
        f"{PIPELINE_EVENT_IDS['B']}.after|{PIPELINE_EVENT_IDS['C']}.before",
        f"{PIPELINE_EVENT_IDS['C']}.after",
    ]
    shared_left = _occurrences(driver, 1, entities["middle_left"])
    shared_right = _occurrences(driver, 2, entities["middle_right"])
    assert len(shared_left) == len(shared_right) == 2
    occurrence_id_values = [
        wrapper.get_attribute("data-occurrence-ids")
        for wrapper in (*shared_left, *shared_right)
    ]
    role_occurrence_values = [
        wrapper.get_attribute("data-role-occurrence-ids")
        for wrapper in (*shared_left, *shared_right)
    ]
    assert all(
        value is not None and len(value.split(" ")) == 2
        for value in occurrence_id_values
    )
    assert all(value is not None and "|" in value for value in role_occurrence_values)

    _hover(driver, 1, entities["middle_left"], occurrence_index=1)
    assert _related_summary(driver) == [
        (0, entities["left"], False, (relations["A"],)),
        (2, entities["middle_right"], False, (relations["B"],)),
        (2, entities["middle_right"], False, (relations["B"],)),
    ]
    assert all(item[0] != 3 for item in _related_summary(driver))
    _end_hover(driver)

    _hover(driver, 2, entities["middle_right"])
    assert _related_summary(driver) == [
        (1, entities["middle_left"], False, (relations["B"],)),
        (1, entities["middle_left"], False, (relations["B"],)),
        (3, entities["right"], False, (relations["C"],)),
    ]
    assert all(item[0] != 0 for item in _related_summary(driver))
    _end_hover(driver)

    _clear(driver)
    _activate(driver, PIPELINE_EVENT_IDS["D"])
    _activate(driver, PIPELINE_EVENT_IDS["E"], shift=True)
    assert [
        column.get_attribute("data-roles")
        for column in driver.find_elements(By.CSS_SELECTOR, ".state-column")
    ] == [
        f"{PIPELINE_EVENT_IDS['D']}.before",
        f"{PIPELINE_EVENT_IDS['D']}.after",
        f"{PIPELINE_EVENT_IDS['E']}.before",
        f"{PIPELINE_EVENT_IDS['E']}.after",
    ]

    _hover(driver, 1, entities["handoff_survivor"])
    assert _related_summary(driver) == [
        (2, entities["handoff_survivor"], True, ()),
        (2, entities["handoff_survivor"], True, ()),
    ]
    _end_hover(driver)

    _hover(driver, 1, entities["handoff_relation_destination"])
    assert _related_summary(driver) == [
        (
            0,
            entities["handoff_relation_source"],
            False,
            (
                relations["handoff_owner_d"],
                relations["handoff_owner_d_child"],
            ),
        ),
        (2, entities["handoff_relation_destination"], True, ()),
    ]
    _end_hover(driver)

    _hover(driver, 1, entities["handoff_relation_source"])
    assert _related_summary(driver) == [
        (0, entities["handoff_relation_source"], True, ())
    ]
    _end_hover(driver)

    _hover(driver, 1, entities["similar_left"])
    assert _related(driver) == []
    _end_hover(driver)

    _activate(driver, PIPELINE_EVENT_IDS["D"])
    _activate(driver, PIPELINE_EVENT_IDS["F"], shift=True)
    assert [
        column.get_attribute("data-roles")
        for column in driver.find_elements(By.CSS_SELECTOR, ".state-column")
    ] == [
        f"{PIPELINE_EVENT_IDS['D']}.before",
        f"{PIPELINE_EVENT_IDS['D']}.after",
        f"{PIPELINE_EVENT_IDS['E']}.before",
        f"{PIPELINE_EVENT_IDS['E']}.after|{PIPELINE_EVENT_IDS['F']}.before",
        f"{PIPELINE_EVENT_IDS['F']}.after",
    ]
    _hover(driver, 3, entities["handoff_relation_destination"])
    assert _related_summary(driver) == [
        (2, entities["handoff_relation_destination"], True, ())
    ]
    _end_hover(driver)

    _activate(driver, PIPELINE_EVENT_IDS["F"])
    _activate(driver, PIPELINE_EVENT_IDS["G"], shift=True)
    assert [
        column.get_attribute("data-roles")
        for column in driver.find_elements(By.CSS_SELECTOR, ".state-column")
    ] == [
        f"{PIPELINE_EVENT_IDS['F']}.before",
        f"{PIPELINE_EVENT_IDS['F']}.after",
        f"{PIPELINE_EVENT_IDS['G']}.before",
        f"{PIPELINE_EVENT_IDS['G']}.after",
    ]
    _hover(driver, 0, entities["barrier_survivor"])
    assert _related(driver) == []
    _end_hover(driver)
    _hover(driver, 0, entities["incomplete_relation_source"])
    assert _related(driver) == []
    _end_hover(driver)
    _hover(driver, 2, entities["barrier_survivor"])
    assert _related_summary(driver) == [(3, entities["barrier_survivor"], True, ())]
    assert all(item[0] != 0 for item in _related_summary(driver))
    _end_hover(driver)
    _hover(driver, 2, entities["incomplete_relation_destination"])
    assert _related_summary(driver) == [
        (3, entities["incomplete_relation_destination"], True, ())
    ]
    assert all(
        relations["incomplete_event_must_not_cross"] not in item[3]
        for item in _related_summary(driver)
    )
    assert all(item[0] != 0 for item in _related_summary(driver))
    _end_hover(driver)
    assert _payload_state(driver) == payload_before


@pytest.mark.browser  # type: ignore[untyped-decorator]
def test_hover_state_is_disposable_across_exit_selection_and_clear(
    headed_chrome: BrowserHarness,
    tmp_path: Path,
) -> None:
    driver = _open_trace(
        headed_chrome,
        tmp_path,
        pipeline_provenance_trace(),
        "provenance-disposable-state",
    )
    entities = PIPELINE_ENTITY_IDS
    relations = PIPELINE_RELATION_IDS
    _activate(driver, PIPELINE_EVENT_IDS["A"])
    _activate(driver, PIPELINE_EVENT_IDS["C"], shift=True)
    stale_source = _occurrences(driver, 1, entities["middle_left"])[0]
    driver.execute_script("globalThis.__staleOccurrence = arguments[0];", stale_source)
    ActionChains(driver).move_to_element(stale_source).perform()
    assert _related(driver)
    _end_hover(driver)

    _clear(driver)
    _activate(driver, PIPELINE_EVENT_IDS["D"])
    _hover(driver, 1, entities["handoff_relation_destination"])
    current = _related_summary(driver)
    assert current == [
        (
            0,
            entities["handoff_relation_source"],
            False,
            (
                relations["handoff_owner_d"],
                relations["handoff_owner_d_child"],
            ),
        )
    ]
    driver.execute_script(
        """
        globalThis.__staleOccurrence.dispatchEvent(
          new PointerEvent("pointerenter", {bubbles: false})
        );
        """
    )
    assert _related_summary(driver) == current

    driver.find_element(By.CSS_SELECTOR, ".clear-selection").click()
    assert driver.find_elements(By.CSS_SELECTOR, ".state-column") == []
    assert _related(driver) == []
    driver.execute_script(
        """
        globalThis.__staleOccurrence.dispatchEvent(
          new PointerEvent("pointerenter", {bubbles: false})
        );
        """
    )
    assert _related(driver) == []
