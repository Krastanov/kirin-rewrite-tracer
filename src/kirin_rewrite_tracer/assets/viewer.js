"use strict";

const payloadNode = document.getElementById("trace-data");
const payload = JSON.parse(payloadNode.textContent);
const trace = payload.trace;
const projection = payload.projection;
const eventTree = document.getElementById("event-tree");
const summary = document.getElementById("trace-summary");
const columns = document.getElementById("ssa-columns");
const emptyWorkspace = document.getElementById("ssa-empty");
const facts = document.getElementById("selected-facts");
const factsEmpty = document.getElementById("facts-empty");
const selectionStatus = document.getElementById("selection-status");
const clearSelection = document.querySelector(".clear-selection");

const eventsByParent = new Map();
const eventsById = new Map();
const snapshotsById = new Map();
const runsBySnapshot = new Map();
const classesByStyle = new Map();
const eventButtons = new Map();

for (const event of trace.events) {
  eventsById.set(event.id, event);
  const children = eventsByParent.get(event.parent_id) || [];
  children.push(event);
  eventsByParent.set(event.parent_id, children);
}
for (const snapshot of trace.snapshots) {
  snapshotsById.set(snapshot.id, snapshot);
}
for (const snapshot of projection.snapshots) {
  runsBySnapshot.set(snapshot.snapshot_id, snapshot.render_runs);
}
for (const style of projection.styles) {
  classesByStyle.set(style.style_id, style.css_class);
}

summary.textContent = `${trace.events.length} event${trace.events.length === 1 ? "" : "s"}; aggregate ${trace.complete ? "complete" : "incomplete"}.`;

function renderBranch(parentId) {
  const list = document.createElement("ol");
  for (const event of eventsByParent.get(parentId) || []) {
    const item = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.className = "event-button";
    button.textContent = `${event.id} — ${event.rule_type} — ${event.completion}`;
    button.addEventListener("click", () => selectEvent(event.id));
    eventButtons.set(event.id, button);
    item.append(button);
    if ((eventsByParent.get(event.id) || []).length > 0) {
      item.append(renderBranch(event.id));
    }
    list.append(item);
  }
  return list;
}

function renderSnapshot(snapshotId, role) {
  const snapshot = snapshotsById.get(snapshotId);
  const section = document.createElement("section");
  section.className = "state-column";
  const heading = document.createElement("h2");
  heading.textContent = `${role}: ${snapshot.state}`;
  const code = document.createElement("code");
  code.className = "trace-code";
  for (const run of runsBySnapshot.get(snapshot.id) || []) {
    const span = document.createElement("span");
    span.textContent = run.text;
    const styleClass = classesByStyle.get(run.style_id);
    if (styleClass !== undefined) {
      span.classList.add(styleClass);
    }
    code.append(span);
  }
  section.append(heading, code);
  return section;
}

function selectEvent(eventId) {
  const event = eventsById.get(eventId);
  for (const [id, button] of eventButtons) {
    if (id === eventId) {
      button.setAttribute("aria-current", "true");
    } else {
      button.removeAttribute("aria-current");
    }
  }
  columns.replaceChildren();
  columns.append(renderSnapshot(event.before_snapshot_id, "Before"));
  if (event.after_snapshot_id === null) {
    const absent = document.createElement("section");
    absent.className = "state-column";
    const heading = document.createElement("h2");
    heading.textContent = "After";
    const message = document.createElement("p");
    message.textContent = "Absent (event incomplete).";
    absent.append(heading, message);
    columns.append(absent);
  } else {
    columns.append(renderSnapshot(event.after_snapshot_id, "After"));
  }
  emptyWorkspace.hidden = true;
  facts.textContent = JSON.stringify(event, null, 2);
  facts.hidden = false;
  factsEmpty.hidden = true;
  selectionStatus.textContent = `Selected: 1; event: ${event.id}; hidden: 0.`;
}

function clearCurrentSelection() {
  for (const button of eventButtons.values()) {
    button.removeAttribute("aria-current");
  }
  columns.replaceChildren();
  emptyWorkspace.hidden = false;
  facts.textContent = "";
  facts.hidden = true;
  factsEmpty.hidden = false;
  selectionStatus.textContent = "Selected: 0; hidden: 0.";
}

const roots = renderBranch(null);
eventTree.replaceWith(roots);
roots.id = "event-tree";
roots.className = "event-tree";
clearSelection.addEventListener("click", clearCurrentSelection);
document.documentElement.setAttribute("data-krt-ready", "true");
