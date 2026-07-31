from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest
from browser_harness import BrowserHarness
from test_export import _HOSTILE, _hostile_trace

from kirin_rewrite_tracer import export_html


@pytest.mark.browser  # type: ignore[untyped-decorator]
def test_exported_hostile_trace_is_inert_offline_and_relocatable(
    headed_chrome: BrowserHarness,
    tmp_path: Path,
) -> None:
    source = export_html(_hostile_trace(), tmp_path / "hostile.html")
    destination = tmp_path / "relocated"
    destination.mkdir()

    relocated = headed_chrome.open_relocated(source, destination)

    assert relocated.parent == destination
    assert tuple(destination.iterdir()) == (relocated,)
    assert headed_chrome.driver.current_url == relocated.as_uri()
    state = cast(
        dict[str, object],
        headed_chrome.driver.execute_script(
            """
            const elements = Array.from(document.querySelectorAll("*"));
            return {
              ready: document.documentElement.getAttribute("data-krt-ready"),
              pwned: Object.prototype.hasOwnProperty.call(globalThis, "pwned"),
              activeNodes: document.querySelectorAll(
                "img,iframe,object,embed,link,form,a[href^='http']"
              ).length,
              handlerAttributes: elements.reduce(
                (count, element) => count + Array.from(element.attributes)
                  .filter(attribute => attribute.name.toLowerCase().startsWith("on"))
                  .length,
                0
              ),
              styleAttributes: document.querySelectorAll("[style]").length,
              eventButtons: document.querySelectorAll(".event-button").length,
              dataType: document.getElementById("trace-data").type,
              hostileIsText: document.body.textContent.includes(arguments[0]),
              factsInitiallyHidden:
                document.getElementById("selected-facts").hidden === true,
              pwnedElement: document.querySelector("[onerror]") !== null
            };
            """,
            _HOSTILE,
        ),
    )
    assert state == {
        "activeNodes": 0,
        "dataType": "application/json",
        "eventButtons": 1,
        "factsInitiallyHidden": True,
        "handlerAttributes": 0,
        "hostileIsText": True,
        "pwned": False,
        "pwnedElement": False,
        "ready": "true",
        "styleAttributes": 0,
    }

    observations = headed_chrome.observations()
    assert observations.page_network_requests(document_url=relocated.as_uri()) == ()
    assert observations.auxiliary_requests_for(relocated.as_uri()) == ()
    assert observations.csp_violations == ()
    assert not [
        entry for entry in observations.console if entry.level in {"SEVERE", "WARNING"}
    ]

    tree = headed_chrome.accessibility_tree()
    assert tree.matching(role="link", name="Skip event hierarchy")
    assert tree.matching(role="button", name="Clear selection")
