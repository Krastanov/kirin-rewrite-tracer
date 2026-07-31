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
const skipLink = document.querySelector(".skip-link");
const ssaWorkspace = document.getElementById("ssa-workspace");

/*
 * These maps are disposable browser indexes. Values remain the canonical decoded
 * records and the canonical arrays are never sorted, spliced, or otherwise mutated.
 */
const eventById = new Map();
const parentByEvent = new Map();
const childrenByParent = new Map();
const snapshotById = new Map();
const configurationById = new Map();
const styleById = new Map();
const entityById = new Map();
const occurrenceById = new Map();
const metadataById = new Map();
const stackById = new Map();
const operationById = new Map();
const operationsByEvent = new Map();
const relationsByOperation = new Map();
const relationsBySource = new Map();
const relationsByDestination = new Map();
const effectsByOperation = new Map();
const occurrencesBySnapshotAndEntity = new Map();
const occurrenceOrdinalById = new Map();
const applicableRelationsByEvent = new Map();
const metadataInventoryBySnapshotAndEntity = new Map();
const projectedSnapshotById = new Map();
const occurrenceTextById = new Map();
const classesByStyle = new Map();
const eventButtons = new Map();
const eventRows = new Map();
const eventDescriptions = new Map();
const occurrenceRecordByElement = new WeakMap();
const neighborProjectionByRecord = new WeakMap();

for (const configuration of trace.configurations) {
  configurationById.set(configuration.id, configuration);
}
for (const style of trace.styles) {
  styleById.set(style.id, style);
}
for (const entity of trace.entities) {
  entityById.set(entity.id, entity);
}
for (const occurrence of trace.occurrences) {
  occurrenceById.set(occurrence.id, occurrence);
}
for (const snapshot of trace.snapshots) {
  snapshotById.set(snapshot.id, snapshot);
  const byEntity = new Map();
  for (
    let occurrenceOrdinal = 0;
    occurrenceOrdinal < snapshot.occurrence_ids.length;
    occurrenceOrdinal += 1
  ) {
    const occurrenceId = snapshot.occurrence_ids[occurrenceOrdinal];
    const occurrence = occurrenceById.get(occurrenceId);
    if (occurrence === undefined) {
      throw new Error(`missing canonical occurrence: ${occurrenceId}`);
    }
    occurrenceOrdinalById.set(occurrence.id, occurrenceOrdinal);
    const entityOccurrences = byEntity.get(occurrence.entity_id) || [];
    entityOccurrences.push(occurrence);
    byEntity.set(occurrence.entity_id, entityOccurrences);
  }
  occurrencesBySnapshotAndEntity.set(snapshot.id, byEntity);
}
for (const record of trace.metadata) {
  metadataById.set(record.id, record);
}
for (const stack of trace.stacks) {
  stackById.set(stack.id, stack);
}
for (const event of trace.events) {
  eventById.set(event.id, event);
  parentByEvent.set(event.id, event.parent_id);
  const children = childrenByParent.get(event.parent_id) || [];
  children.push(event);
  childrenByParent.set(event.parent_id, children);
}
for (const children of childrenByParent.values()) {
  children.sort(
    (left, right) =>
      left.sibling_ordinal - right.sibling_ordinal ||
      left.sequence - right.sequence,
  );
}
for (const operation of trace.operations) {
  operationById.set(operation.id, operation);
  const owned = operationsByEvent.get(operation.owner_event_id) || [];
  owned.push(operation);
  operationsByEvent.set(operation.owner_event_id, owned);
}
for (const relation of trace.relations) {
  const owned =
    relationsByOperation.get(relation.mutation_operation_id) || [];
  owned.push(relation);
  relationsByOperation.set(relation.mutation_operation_id, owned);
  const outgoing = relationsBySource.get(relation.source_entity_id) || [];
  outgoing.push(relation);
  relationsBySource.set(relation.source_entity_id, outgoing);
  const incoming =
    relationsByDestination.get(relation.destination_entity_id) || [];
  incoming.push(relation);
  relationsByDestination.set(relation.destination_entity_id, incoming);
}
for (const effect of trace.effects) {
  const owned = effectsByOperation.get(effect.mutation_operation_id) || [];
  owned.push(effect);
  effectsByOperation.set(effect.mutation_operation_id, owned);
}
for (const snapshot of projection.snapshots) {
  projectedSnapshotById.set(snapshot.snapshot_id, snapshot);
}
for (const occurrence of projection.occurrences) {
  occurrenceTextById.set(occurrence.occurrence_id, occurrence.text);
}
for (const style of projection.styles) {
  classesByStyle.set(style.style_id, style.css_class);
}

const eventPreorder = [];
function appendPreorder(parentId) {
  for (const event of childrenByParent.get(parentId) || []) {
    eventPreorder.push(event.id);
    appendPreorder(event.id);
  }
}
appendPreorder(null);

summary.textContent = `${trace.events.length} event${trace.events.length === 1 ? "" : "s"}; aggregate ${trace.complete ? "complete" : "incomplete"}.`;
if (trace.events.length === 0) {
  emptyWorkspace.textContent = "No rewrite events were captured.";
}

function isStrictDescendant(candidateId, ancestorId) {
  let parentId = parentByEvent.get(candidateId);
  while (parentId !== null && parentId !== undefined) {
    if (parentId === ancestorId) {
      return true;
    }
    parentId = parentByEvent.get(parentId);
  }
  return false;
}

function interactiveOccurrences(snapshotId, entityId) {
  const byEntity = occurrencesBySnapshotAndEntity.get(snapshotId);
  return (byEntity?.get(entityId) || []).filter(
    (occurrence) =>
      occurrence.role === "definition" || occurrence.role === "reference",
  );
}

function appendApplicableRelation(eventId, relation) {
  const applicable = applicableRelationsByEvent.get(eventId) || [];
  applicable.push(relation);
  applicableRelationsByEvent.set(eventId, applicable);
}

for (const relation of trace.relations) {
  const source = entityById.get(relation.source_entity_id);
  const destination = entityById.get(relation.destination_entity_id);
  if (source?.kind !== "ssa" || destination?.kind !== "ssa") {
    continue;
  }
  const operation = operationById.get(relation.mutation_operation_id);
  if (operation === undefined) {
    throw new Error(
      `missing canonical mutation operation: ${relation.mutation_operation_id}`,
    );
  }

  let candidateEventId = operation.owner_event_id;
  while (candidateEventId !== null && candidateEventId !== undefined) {
    const candidateEvent = eventById.get(candidateEventId);
    if (candidateEvent === undefined) {
      throw new Error(`missing canonical event: ${candidateEventId}`);
    }
    if (
      candidateEvent.after_snapshot_id !== null &&
      interactiveOccurrences(
        candidateEvent.before_snapshot_id,
        relation.source_entity_id,
      ).length > 0 &&
      interactiveOccurrences(
        candidateEvent.after_snapshot_id,
        relation.destination_entity_id,
      ).length > 0
    ) {
      appendApplicableRelation(candidateEvent.id, relation);
    }
    candidateEventId = parentByEvent.get(candidateEventId);
  }
}

function orderedUnique(eventIds) {
  const identifiers = new Set(eventIds);
  return eventPreorder.filter((eventId) => identifiers.has(eventId));
}

function freezeSelection(frontier, anchor) {
  const ordered = orderedUnique(frontier);
  if (ordered.length !== frontier.length) {
    throw new Error("selection frontier must contain unique retained events");
  }
  for (const candidateId of ordered) {
    if (
      ordered.some(
        (otherId) =>
          otherId !== candidateId &&
          isStrictDescendant(candidateId, otherId),
      )
    ) {
      throw new Error("selection frontier must be ancestor-free");
    }
  }
  if (ordered.length === 0) {
    if (anchor !== null) {
      throw new Error("an empty selection must have a null anchor");
    }
  } else if (anchor === null || !ordered.includes(anchor)) {
    throw new Error("the range anchor must be a visible frontier event");
  }
  return Object.freeze({
    frontier: Object.freeze(ordered),
    anchor,
  });
}

function visibleEventIds(state) {
  return eventPreorder.filter(
    (eventId) =>
      !state.frontier.some((selectedId) =>
        isStrictDescendant(eventId, selectedId),
      ),
  );
}

function normalizeCandidates(candidates) {
  return candidates.filter(
    (candidateId) =>
      !candidates.some(
        (otherId) =>
          otherId !== candidateId &&
          isStrictDescendant(candidateId, otherId),
      ),
  );
}

function reduceSelection(current, input, visibleBefore) {
  if (input.kind === "clear") {
    if (current.frontier.length === 0 && current.anchor === null) {
      return current;
    }
    return freezeSelection([], null);
  }
  if (input.kind !== "activate") {
    return current;
  }

  const targetId = input.targetId;
  if (!eventById.has(targetId) || !visibleBefore.includes(targetId)) {
    return current;
  }
  if (!input.shiftKey || current.anchor === null) {
    return freezeSelection([targetId], targetId);
  }

  const anchorIndex = visibleBefore.indexOf(current.anchor);
  const targetIndex = visibleBefore.indexOf(targetId);
  if (anchorIndex < 0 || targetIndex < 0) {
    return current;
  }
  const start = Math.min(anchorIndex, targetIndex);
  const end = Math.max(anchorIndex, targetIndex);
  const frontier = normalizeCandidates(visibleBefore.slice(start, end + 1));

  let anchor = current.anchor;
  if (!frontier.includes(anchor)) {
    const survivingAncestors = frontier.filter((candidateId) =>
      isStrictDescendant(anchor, candidateId),
    );
    if (survivingAncestors.length !== 1) {
      throw new Error("a swallowed anchor must have one surviving ancestor");
    }
    [anchor] = survivingAncestors;
  }
  return freezeSelection(frontier, anchor);
}

function snapshotRole(eventId, state, snapshotId) {
  return Object.freeze({
    kind: "snapshot",
    eventId,
    state,
    snapshotId,
  });
}

function absentRole(eventId) {
  return Object.freeze({
    kind: "absent",
    eventId,
    state: "after",
    snapshotId: null,
  });
}

function roleName(role) {
  return `${role.eventId}.${role.state}`;
}

function freezeColumn(roles) {
  const frozenRoles = Object.freeze(roles.slice());
  const key = JSON.stringify(
    frozenRoles.map((role) => [
      role.kind,
      role.eventId,
      role.state,
      role.snapshotId,
    ]),
  );
  return Object.freeze({key, roles: frozenRoles});
}

function snapshotSemanticClass(snapshotId) {
  const projected = projectedSnapshotById.get(snapshotId);
  if (projected === undefined) {
    throw new Error(`missing projected snapshot: ${snapshotId}`);
  }
  return projected.semantic_class;
}

function reduceColumns(frontier) {
  const reduced = [];
  let previousEvent = null;
  for (const eventId of frontier) {
    const event = eventById.get(eventId);
    const before = snapshotRole(event.id, "before", event.before_snapshot_id);

    let shared = false;
    if (
      previousEvent !== null &&
      previousEvent.after_snapshot_id !== null &&
      reduced.length > 0 &&
      snapshotSemanticClass(previousEvent.after_snapshot_id) ===
        snapshotSemanticClass(event.before_snapshot_id)
    ) {
      const previousColumn = reduced[reduced.length - 1];
      const previousRole = previousColumn.roles[0];
      if (
        previousColumn.roles.length === 1 &&
        previousRole.kind === "snapshot" &&
        previousRole.eventId === previousEvent.id &&
        previousRole.state === "after"
      ) {
        reduced[reduced.length - 1] = freezeColumn([previousRole, before]);
        shared = true;
      }
    }
    if (!shared) {
      reduced.push(freezeColumn([before]));
    }

    if (event.after_snapshot_id === null) {
      reduced.push(freezeColumn([absentRole(event.id)]));
    } else {
      reduced.push(
        freezeColumn([
          snapshotRole(event.id, "after", event.after_snapshot_id),
        ]),
      );
    }
    previousEvent = event;
  }
  return Object.freeze(reduced);
}

function reduceAdjacentEdge(leftColumn, rightColumn) {
  const leftRole = leftColumn.roles[leftColumn.roles.length - 1];
  const rightRole = rightColumn.roles[0];
  if (leftRole.kind === "absent" || rightRole.kind === "absent") {
    return Object.freeze({
      kind: "barrier",
      eventId: null,
      leftRole,
      rightRole,
    });
  }
  if (
    leftRole.eventId === rightRole.eventId &&
    leftRole.state === "before" &&
    rightRole.state === "after"
  ) {
    return Object.freeze({
      kind: "event",
      eventId: leftRole.eventId,
      leftRole,
      rightRole,
    });
  }
  if (leftRole.state === "after" && rightRole.state === "before") {
    return Object.freeze({
      kind: "handoff",
      eventId: null,
      leftRole,
      rightRole,
    });
  }
  return Object.freeze({
    kind: "disconnected",
    eventId: null,
    leftRole,
    rightRole,
  });
}

let eventDescriptionSequence = 0;
let occurrenceControlSequence = 0;
let columnSequence = 0;
let overlayHeadingSequence = 0;

function eventDescription(event, depth, selected) {
  const siblings = childrenByParent.get(event.parent_id) || [];
  const sibling = siblings.indexOf(event) + 1;
  const parent =
    event.parent_id === null ? "absent" : event.parent_id;
  return `Event ${event.id}; rule ${event.rule_type}; depth ${depth}; parent ${parent}; sibling ${sibling} of ${siblings.length}; completion ${event.completion}; selection ${selected ? "selected" : "unselected"}.`;
}

function appendEventBranch(parentId, list, depth) {
  for (const event of childrenByParent.get(parentId) || []) {
    const item = document.createElement("li");
    item.dataset.eventId = event.id;
    const button = document.createElement("button");
    const description = document.createElement("span");
    const descriptionId = `event-description-${eventDescriptionSequence}`;
    eventDescriptionSequence += 1;
    button.type = "button";
    button.className = "event-button";
    button.dataset.eventId = event.id;
    button.dataset.depth = String(depth);
    button.textContent = `${event.id} — ${event.rule_type} — ${event.completion}`;
    button.setAttribute("aria-describedby", descriptionId);
    description.id = descriptionId;
    description.className = "visually-hidden event-description";
    description.hidden = true;
    description.textContent = eventDescription(event, depth, false);
    button.addEventListener("click", (inputEvent) => {
      activateEvent(event.id, inputEvent);
    });
    eventButtons.set(event.id, button);
    eventRows.set(event.id, item);
    eventDescriptions.set(event.id, description);
    item.append(button, description);
    const children = childrenByParent.get(event.id) || [];
    if (children.length > 0) {
      const childList = document.createElement("ol");
      appendEventBranch(event.id, childList, depth + 1);
      item.append(childList);
    }
    list.append(item);
  }
}

function renderRun(run) {
  const span = document.createElement("span");
  span.className = "captured-run";
  span.textContent = run.text;
  span.dataset.styleId = run.style_id === null ? "" : run.style_id;
  if (run.occurrence_ids.length > 0) {
    span.dataset.occurrenceIds = run.occurrence_ids.join(" ");
  }
  const styleClass = classesByStyle.get(run.style_id);
  if (styleClass !== undefined) {
    span.classList.add(styleClass);
  }
  return span;
}

function interactiveOccurrenceForRun(run) {
  const interactive = run.occurrence_ids
    .map((occurrenceId) => occurrenceById.get(occurrenceId))
    .filter(
      (occurrence) =>
        occurrence.role === "definition" || occurrence.role === "reference",
    );
  if (interactive.length > 1) {
    throw new Error("a render run cannot contain overlapping SSA occurrences");
  }
  return interactive.length === 0 ? null : interactive[0];
}

function occurrenceBindings(column, presentationOccurrence) {
  const ordinal = occurrenceOrdinalById.get(presentationOccurrence.id);
  if (ordinal === undefined) {
    throw new Error(
      `missing retained occurrence ordinal: ${presentationOccurrence.id}`,
    );
  }
  const bindings = [];
  for (const role of column.roles) {
    if (role.kind !== "snapshot") {
      throw new Error("an absent column cannot contain a rendered occurrence");
    }
    const snapshot = snapshotById.get(role.snapshotId);
    const occurrenceId = snapshot.occurrence_ids[ordinal];
    const occurrence = occurrenceById.get(occurrenceId);
    if (
      occurrence === undefined ||
      occurrence.entity_id !== presentationOccurrence.entity_id ||
      occurrence.role !== presentationOccurrence.role ||
      occurrence.start !== presentationOccurrence.start ||
      occurrence.end !== presentationOccurrence.end
    ) {
      throw new Error("shared snapshot occurrence order is inconsistent");
    }
    bindings.push(
      Object.freeze({
        role,
        roleName: roleName(role),
        occurrence,
      }),
    );
  }
  return Object.freeze(bindings);
}

function snapshotEntityKey(snapshotId, entityId) {
  return JSON.stringify([snapshotId, entityId]);
}

function renderedValueSignature(value) {
  if (value === null) {
    return null;
  }
  return [value.qualified_type, value.text, value.path];
}

function metadataInventory(snapshotId, entityId) {
  const cacheKey = snapshotEntityKey(snapshotId, entityId);
  const cached = metadataInventoryBySnapshotAndEntity.get(cacheKey);
  if (cached !== undefined) {
    return cached;
  }

  const snapshot = snapshotById.get(snapshotId);
  const entity = entityById.get(entityId);
  if (snapshot === undefined || entity === undefined || entity.kind !== "ssa") {
    throw new Error("an SSA metadata inventory requires retained snapshot and entity");
  }
  const records = [];
  for (const metadataId of snapshot.metadata_ids) {
    const record = metadataById.get(metadataId);
    if (record === undefined || record.snapshot_id !== snapshot.id) {
      throw new Error(`missing canonical metadata record: ${metadataId}`);
    }
    if (record.owner_entity_id === entity.id) {
      records.push(record);
    }
  }
  const frozenRecords = Object.freeze(records);
  const signature = JSON.stringify([
    entity.id,
    entity.qualified_type,
    entity.defining_owner_id,
    snapshot.analysis_supplied,
    frozenRecords.map((record) => [
      record.owner_entity_id,
      record.namespace,
      record.key,
      record.presence,
      renderedValueSignature(record.value),
    ]),
  ]);
  const typeRecords = frozenRecords.filter(
    (record) =>
      record.namespace === "ssa" &&
      record.key === "type" &&
      record.presence === "present" &&
      record.value !== null,
  );
  const inventory = Object.freeze({
    snapshot,
    entity,
    records: frozenRecords,
    signature,
    typeRecord: typeRecords.length === 1 ? typeRecords[0] : null,
  });
  metadataInventoryBySnapshotAndEntity.set(cacheKey, inventory);
  return inventory;
}

function occurrenceMetadata(bindings, entityId) {
  const inventories = Object.freeze(
    bindings.map((binding) => {
      if (binding.occurrence.snapshot_id !== binding.role.snapshotId) {
        throw new Error("logical occurrence binding has the wrong snapshot");
      }
      return metadataInventory(binding.role.snapshotId, entityId);
    }),
  );
  const signature = inventories[0].signature;
  if (!inventories.every((inventory) => inventory.signature === signature)) {
    throw new Error("shared occurrence metadata inventories are inconsistent");
  }
  return inventories;
}

function definitionSuffix(presentationOccurrence, inventories) {
  if (presentationOccurrence.role !== "definition") {
    return null;
  }
  const typeRecords = inventories.map((inventory) => inventory.typeRecord);
  if (
    typeRecords[0] === null ||
    !typeRecords.every(
      (record) =>
        record !== null && record.value.text === typeRecords[0].value.text,
    )
  ) {
    return null;
  }
  const suffix = document.createElement("span");
  suffix.className = "ssa-metadata-suffix";
  suffix.textContent = ` ⟦${typeRecords[0].value.text}⟧`;
  suffix.setAttribute("aria-hidden", "true");
  return suffix;
}

function appendOccurrenceRecord(columnState, element, bindings) {
  const presentationOccurrence = bindings[0].occurrence;
  const inventories = occurrenceMetadata(
    bindings,
    presentationOccurrence.entity_id,
  );
  const labels = bindings.map((binding) =>
    occurrenceTextById.get(binding.occurrence.id),
  );
  if (
    labels[0] === undefined ||
    !labels.every((label) => label === labels[0])
  ) {
    throw new Error("a logical occurrence requires one exact captured label");
  }
  const suffixElement = definitionSuffix(presentationOccurrence, inventories);
  const descriptionElement = document.createElement("span");
  const controlOrdinal = occurrenceControlSequence;
  occurrenceControlSequence += 1;
  const descriptionId = `ssa-occurrence-description-${controlOrdinal}`;
  const overlayId = `ssa-metadata-overlay-${controlOrdinal}`;
  element.type = "button";
  element.className = "ssa-occurrence";
  element.setAttribute("aria-label", labels[0]);
  element.setAttribute("aria-describedby", descriptionId);
  element.setAttribute("aria-controls", overlayId);
  element.setAttribute("aria-expanded", "false");
  element.dataset.columnIndex = String(columnState.index);
  element.dataset.entityId = presentationOccurrence.entity_id;
  element.dataset.occurrenceId = presentationOccurrence.id;
  element.dataset.occurrenceIds = bindings
    .map((binding) => binding.occurrence.id)
    .join(" ");
  element.dataset.occurrenceRole = presentationOccurrence.role;
  element.dataset.roleOccurrenceIds = bindings
    .map((binding) => `${binding.roleName}=${binding.occurrence.id}`)
    .join("|");
  descriptionElement.id = descriptionId;
  descriptionElement.className =
    "visually-hidden ssa-occurrence-description";
  descriptionElement.hidden = true;

  const record = Object.freeze({
    element,
    columnIndex: columnState.index,
    columnKey: columnState.column.key,
    entityId: presentationOccurrence.entity_id,
    bindings,
    inventories,
    suffixElement,
    descriptionElement,
    label: labels[0],
    overlayId,
  });
  occurrenceRecordByElement.set(element, record);
  const byEntity =
    columnState.occurrencesByEntity.get(record.entityId) || [];
  byEntity.push(record);
  columnState.occurrencesByEntity.set(record.entityId, byEntity);
  columnState.occurrences.push(record);
  element.addEventListener("pointerenter", (inputEvent) => {
    enterPointerProvenance(record, inputEvent);
  });
  element.addEventListener("pointerleave", (inputEvent) => {
    leavePointerProvenance(record, inputEvent);
  });
  return record;
}

function renderCode(column, columnState) {
  const [presentationRole] = column.roles;
  const projected = projectedSnapshotById.get(presentationRole.snapshotId);
  const code = document.createElement("div");
  code.className = "trace-code";
  let activeOccurrenceId = null;
  let activeWrapper = null;
  for (const run of projected.render_runs) {
    const interactiveOccurrence = interactiveOccurrenceForRun(run);
    if (interactiveOccurrence === null) {
      activeOccurrenceId = null;
      activeWrapper = null;
      code.append(renderRun(run));
      continue;
    }
    if (activeOccurrenceId !== interactiveOccurrence.id) {
      activeOccurrenceId = interactiveOccurrence.id;
      activeWrapper = document.createElement("button");
      const record = appendOccurrenceRecord(
        columnState,
        activeWrapper,
        occurrenceBindings(column, interactiveOccurrence),
      );
      code.append(activeWrapper);
      if (record.suffixElement !== null) {
        code.append(record.suffixElement);
      }
      code.append(record.descriptionElement);
    }
    activeWrapper.append(renderRun(run));
  }
  return code;
}

function columnHeading(column) {
  if (column.roles.length === 2) {
    return `Shared by exact equality: ${roleName(column.roles[0])} | ${roleName(column.roles[1])}`;
  }
  const [role] = column.roles;
  if (role.kind === "absent") {
    return `${roleName(role)} — absent (event incomplete).`;
  }
  return roleName(role);
}

function renderColumn(column, index) {
  const section = document.createElement("section");
  const columnId = `ssa-column-${columnSequence}`;
  const headingId = `ssa-column-heading-${columnSequence}`;
  columnSequence += 1;
  const columnState = {
    column,
    element: section,
    index,
    occurrences: [],
    occurrencesByEntity: new Map(),
  };
  section.id = columnId;
  section.className = "state-column";
  section.setAttribute("aria-labelledby", headingId);
  section.dataset.columnKey = column.key;
  section.dataset.roleCount = String(column.roles.length);
  section.dataset.roles = column.roles.map(roleName).join("|");
  section.dataset.snapshotIds = column.roles
    .filter((role) => role.snapshotId !== null)
    .map((role) => role.snapshotId)
    .join("|");
  if (column.roles.length === 2) {
    section.classList.add("shared-state-column");
  }

  const heading = document.createElement("h2");
  heading.id = headingId;
  heading.textContent = columnHeading(column);
  section.append(heading);
  const [presentationRole] = column.roles;
  if (presentationRole.kind === "absent") {
    section.classList.add("absent-state-column");
    const message = document.createElement("p");
    message.textContent = "Absent after state; the event is incomplete.";
    section.append(message);
  } else {
    section.append(renderCode(column, columnState));
  }
  return columnState;
}

let renderedColumnState = Object.freeze([]);
let renderedEdgeState = Object.freeze([]);
const provenanceTargets = new Set();
let pointerProvenanceCandidate = null;
let keyboardProvenanceCandidate = null;
let provenancePreviewOwner = null;
let provenanceCandidateClock = 0;
let pendingTabFocusToken = null;
let provenanceReconcilePending = false;
let pointerProvenanceArmed = true;
let suppressProgrammaticFocus = false;
let activeMetadataOccurrence = null;
let activeMetadataOverlay = null;

function currentOccurrenceRecord(record) {
  const currentColumn = renderedColumnState[record.columnIndex];
  return (
    record.element.isConnected &&
    occurrenceRecordByElement.get(record.element) === record &&
    currentColumn !== undefined &&
    currentColumn.column.key === record.columnKey &&
    currentColumn.occurrences.includes(record) &&
    record.bindings.length === currentColumn.column.roles.length &&
    record.bindings.every(
      (binding, index) =>
        binding.roleName === roleName(currentColumn.column.roles[index]),
    )
  );
}

function clearProvenanceMarks() {
  for (const target of provenanceTargets) {
    delete target.dataset.provenanceRelated;
    delete target.dataset.provenanceIdentity;
    delete target.dataset.provenanceRelationIds;
  }
  provenanceTargets.clear();
}

function discardProvenanceCandidates() {
  pointerProvenanceCandidate = null;
  keyboardProvenanceCandidate = null;
  provenancePreviewOwner = null;
  pendingTabFocusToken = null;
  pointerProvenanceArmed = false;
  clearProvenanceMarks();
}

function bindingForRole(record, role) {
  const expectedRoleName = roleName(role);
  return record.bindings.find(
    (binding) => binding.roleName === expectedRoleName,
  );
}

function relationEvidence(edge, sourceEntityId, targetEntityId, sourceIsLeft) {
  if (edge.kind !== "event") {
    return [];
  }
  const applicable = applicableRelationsByEvent.get(edge.eventId) || [];
  const endpointRelations = sourceIsLeft
    ? relationsBySource.get(sourceEntityId) || []
    : relationsByDestination.get(sourceEntityId) || [];
  return endpointRelations.filter(
    (relation) =>
      applicable.includes(relation) &&
      (sourceIsLeft
        ? relation.destination_entity_id === targetEntityId
        : relation.source_entity_id === targetEntityId),
  );
}

function projectNeighbor(
  sourceRecord,
  neighborIndex,
  edge,
  sourceIsLeft,
  side,
) {
  if (
    neighborIndex < 0 ||
    neighborIndex >= renderedColumnState.length
  ) {
    return Object.freeze({
      side,
      status: "none",
      roleName: null,
      roleNames: Object.freeze([]),
      matches: Object.freeze([]),
    });
  }

  const neighbor = renderedColumnState[neighborIndex];
  const neighborRoleNames = Object.freeze(
    neighbor.column.roles.map((role) => roleName(role)),
  );
  const targetRole = sourceIsLeft ? edge.rightRole : edge.leftRole;
  const targetRoleName = roleName(targetRole);
  if (targetRole.kind === "absent") {
    return Object.freeze({
      side,
      status: "absent",
      roleName: targetRoleName,
      roleNames: neighborRoleNames,
      matches: Object.freeze([]),
    });
  }

  const matches = [];
  if (edge.kind !== "barrier" && edge.kind !== "disconnected") {
    const sourceRole = sourceIsLeft ? edge.leftRole : edge.rightRole;
    const sourceBinding = bindingForRole(sourceRecord, sourceRole);
    if (sourceBinding === undefined) {
      throw new Error("rendered source lacks its facing logical occurrence");
    }
    for (
      let targetOrdinal = 0;
      targetOrdinal < neighbor.occurrences.length;
      targetOrdinal += 1
    ) {
      const targetRecord = neighbor.occurrences[targetOrdinal];
      const targetBinding = bindingForRole(targetRecord, targetRole);
      if (targetBinding === undefined) {
        throw new Error("rendered target lacks its facing logical occurrence");
      }
      const identity =
        sourceBinding.occurrence.entity_id ===
        targetBinding.occurrence.entity_id;
      const relations = relationEvidence(
        edge,
        sourceBinding.occurrence.entity_id,
        targetBinding.occurrence.entity_id,
        sourceIsLeft,
      );
      if (!identity && relations.length === 0) {
        continue;
      }
      const entity = entityById.get(targetBinding.occurrence.entity_id);
      if (entity === undefined) {
        throw new Error("provenance target lacks its canonical entity");
      }
      const renderedLabel = occurrenceTextById.get(
        targetBinding.occurrence.id,
      );
      if (renderedLabel === undefined) {
        throw new Error("provenance target lacks its projected label");
      }
      matches.push(
        Object.freeze({
          record: targetRecord,
          entityId: entity.id,
          definingOwnerId: entity.defining_owner_id,
          ordinal: targetOrdinal + 1,
          renderedLabel,
          identity,
          relations: Object.freeze(relations.slice()),
        }),
      );
    }
  }
  return Object.freeze({
    side,
    status: "present",
    roleName: targetRoleName,
    roleNames: neighborRoleNames,
    matches: Object.freeze(matches),
  });
}

function projectImmediateNeighbors(sourceRecord) {
  if (!currentOccurrenceRecord(sourceRecord)) {
    throw new Error("cannot project neighbors for a stale occurrence");
  }
  const cached = neighborProjectionByRecord.get(sourceRecord);
  if (cached !== undefined) {
    return cached;
  }
  const left =
    sourceRecord.columnIndex === 0
      ? projectNeighbor(sourceRecord, -1, null, false, "Left")
      : projectNeighbor(
          sourceRecord,
          sourceRecord.columnIndex - 1,
          renderedEdgeState[sourceRecord.columnIndex - 1],
          false,
          "Left",
        );
  const right =
    sourceRecord.columnIndex + 1 === renderedColumnState.length
      ? projectNeighbor(
          sourceRecord,
          renderedColumnState.length,
          null,
          true,
          "Right",
        )
      : projectNeighbor(
          sourceRecord,
          sourceRecord.columnIndex + 1,
          renderedEdgeState[sourceRecord.columnIndex],
          true,
          "Right",
        );
  const result = Object.freeze({left, right});
  neighborProjectionByRecord.set(sourceRecord, result);
  return result;
}

function neighborDescription(neighbor) {
  if (neighbor.status === "none") {
    return `${neighbor.side} neighbor: none.`;
  }
  if (neighbor.status === "absent") {
    return (
      `${neighbor.side} neighbor ${neighbor.roleName}; column roles ` +
      `${neighbor.roleNames.join(" | ")}: absent SSA state.`
    );
  }
  let description =
    `${neighbor.side} neighbor ${neighbor.roleName}; column roles ` +
    `${neighbor.roleNames.join(" | ")}: present; ` +
    `matches ${neighbor.matches.length}.`;
  for (const match of neighbor.matches) {
    const owner =
      match.definingOwnerId === null ? "absent" : match.definingOwnerId;
    const evidence = [];
    if (match.identity) {
      evidence.push("identity");
    }
    if (match.relations.length > 0) {
      evidence.push(
        `relations ${match.relations.map((relation) => relation.id).join(", ")}`,
      );
    }
    description +=
      ` Neighbor occurrence ordinal ${match.ordinal}: entity ${match.entityId}; ` +
      `defining owner ${owner}; label ${JSON.stringify(match.renderedLabel)}; ` +
      `evidence ${evidence.join(" and ")}.`;
  }
  return description;
}

function refreshOccurrenceDescriptions() {
  for (const columnState of renderedColumnState) {
    for (const record of columnState.occurrences) {
      const entity = entityById.get(record.entityId);
      if (entity === undefined) {
        throw new Error("rendered occurrence lacks its canonical entity");
      }
      const owner =
        entity.defining_owner_id === null
          ? "absent"
          : entity.defining_owner_id;
      const role =
        record.bindings[0].occurrence.role === "definition"
          ? "Definition"
          : "Reference";
      const roles = record.bindings
        .map((binding) => binding.roleName)
        .join(" | ");
      const neighbors = projectImmediateNeighbors(record);
      record.descriptionElement.textContent =
        `${role} occurrence; entity ${record.entityId}; defining owner ${owner}; ` +
        `state roles ${roles}. ${neighborDescription(neighbors.left)} ` +
        neighborDescription(neighbors.right);
    }
  }
}

function markProvenanceTarget(match) {
  const target = match.record.element;
  target.dataset.provenanceRelated = "true";
  target.dataset.provenanceIdentity = match.identity ? "true" : "false";
  target.dataset.provenanceRelationIds = match.relations
    .map((relation) => relation.id)
    .join(" ");
  provenanceTargets.add(target);
}

function provenanceCandidate(record) {
  provenanceCandidateClock += 1;
  return Object.freeze({
    record,
    enteredAt: provenanceCandidateClock,
  });
}

function reconcileProvenanceCandidates() {
  provenanceReconcilePending = false;
  if (
    pointerProvenanceCandidate !== null &&
    !currentOccurrenceRecord(pointerProvenanceCandidate.record)
  ) {
    pointerProvenanceCandidate = null;
  }
  if (
    keyboardProvenanceCandidate !== null &&
    !currentOccurrenceRecord(keyboardProvenanceCandidate.record)
  ) {
    keyboardProvenanceCandidate = null;
  }
  const candidates = [
    pointerProvenanceCandidate,
    keyboardProvenanceCandidate,
  ].filter((candidate) => candidate !== null);
  candidates.sort((left, right) => right.enteredAt - left.enteredAt);
  const nextOwner = candidates.length === 0 ? null : candidates[0];
  if (nextOwner === provenancePreviewOwner) {
    return;
  }
  clearProvenanceMarks();
  provenancePreviewOwner = nextOwner;
  if (nextOwner === null) {
    return;
  }
  const projection = projectImmediateNeighbors(nextOwner.record);
  for (const neighbor of [projection.left, projection.right]) {
    for (const match of neighbor.matches) {
      markProvenanceTarget(match);
    }
  }
}

function scheduleProvenanceReconcile() {
  if (provenanceReconcilePending) {
    return;
  }
  provenanceReconcilePending = true;
  queueMicrotask(reconcileProvenanceCandidates);
}

function enterPointerProvenance(record, inputEvent) {
  if (
    !inputEvent.isTrusted ||
    !pointerProvenanceArmed ||
    !currentOccurrenceRecord(record)
  ) {
    return;
  }
  if (pointerProvenanceCandidate?.record !== record) {
    pointerProvenanceCandidate = provenanceCandidate(record);
  }
  reconcileProvenanceCandidates();
}

function handlePointerProvenanceMove(inputEvent) {
  if (!inputEvent.isTrusted) {
    return;
  }
  pointerProvenanceArmed = true;
  const target = inputEvent.target;
  if (!(target instanceof Element)) {
    return;
  }
  const occurrenceElement = target.closest(".ssa-occurrence");
  if (occurrenceElement === null) {
    return;
  }
  const record = occurrenceRecordByElement.get(occurrenceElement);
  if (
    record !== undefined &&
    currentOccurrenceRecord(record) &&
    pointerProvenanceCandidate?.record !== record
  ) {
    pointerProvenanceCandidate = provenanceCandidate(record);
    reconcileProvenanceCandidates();
  }
}

function leavePointerProvenance(record, inputEvent) {
  if (
    inputEvent.isTrusted &&
    pointerProvenanceCandidate?.record === record
  ) {
    pointerProvenanceCandidate = null;
    reconcileProvenanceCandidates();
  }
}

function promoteKeyboardProvenance(record) {
  if (!currentOccurrenceRecord(record)) {
    return;
  }
  if (keyboardProvenanceCandidate?.record !== record) {
    keyboardProvenanceCandidate = provenanceCandidate(record);
  }
  reconcileProvenanceCandidates();
}

function handleProvenanceKeyDown(inputEvent) {
  if (!inputEvent.isTrusted) {
    return;
  }
  if (
    inputEvent.key === "Tab" &&
    !inputEvent.altKey &&
    !inputEvent.ctrlKey &&
    !inputEvent.metaKey
  ) {
    const token = Object.freeze({});
    pendingTabFocusToken = token;
    setTimeout(() => {
      if (pendingTabFocusToken === token) {
        pendingTabFocusToken = null;
      }
    }, 0);
    return;
  }
  if (inputEvent.key !== "Enter" && inputEvent.key !== " ") {
    return;
  }
  const target = inputEvent.target;
  if (!(target instanceof Element)) {
    return;
  }
  const occurrenceElement = target.closest(".ssa-occurrence");
  if (
    occurrenceElement === null ||
    occurrenceElement !== document.activeElement
  ) {
    return;
  }
  const record = occurrenceRecordByElement.get(occurrenceElement);
  if (record !== undefined) {
    promoteKeyboardProvenance(record);
  }
}

function handleProvenanceFocusIn(inputEvent) {
  const token = pendingTabFocusToken;
  pendingTabFocusToken = null;
  if (token === null || suppressProgrammaticFocus) {
    return;
  }
  const target = inputEvent.target;
  if (!(target instanceof Element)) {
    return;
  }
  const occurrenceElement = target.closest(".ssa-occurrence");
  if (occurrenceElement === null) {
    return;
  }
  const record = occurrenceRecordByElement.get(occurrenceElement);
  if (record !== undefined) {
    promoteKeyboardProvenance(record);
  }
}

function handleProvenanceFocusOut(inputEvent) {
  const target = inputEvent.target;
  if (
    keyboardProvenanceCandidate !== null &&
    target === keyboardProvenanceCandidate.record.element
  ) {
    keyboardProvenanceCandidate = null;
    scheduleProvenanceReconcile();
  }
}

function reduceMetadataOccurrence(current, input) {
  if (input.kind === "activate") {
    if (
      current !== null &&
      current.record === input.candidate.record &&
      current.columnKey === input.candidate.columnKey
    ) {
      return null;
    }
    return input.candidate;
  }
  if (input.kind === "dismiss") {
    return null;
  }
  return current;
}

function appendMetadataField(list, field, label, value, exact = false) {
  const row = document.createElement("div");
  row.className = "ssa-metadata-field";
  row.dataset.field = field;
  const term = document.createElement("dt");
  term.textContent = label;
  const definition = document.createElement("dd");
  if (exact) {
    const exactValue = document.createElement("span");
    exactValue.className = "ssa-metadata-exact-value";
    exactValue.textContent = value;
    definition.append(exactValue);
  } else {
    definition.textContent = value;
  }
  row.append(term, definition);
  list.append(row);
}

function appendRenderedMetadataValue(container, value) {
  const fields = document.createElement("dl");
  fields.className = "ssa-metadata-value";
  appendMetadataField(
    fields,
    "qualified-type",
    "Qualified type",
    value.qualified_type,
  );
  appendMetadataField(fields, "text", "Exact text", value.text, true);
  appendMetadataField(fields, "path", "Representation path", value.path);
  container.append(fields);
}

function renderMetadataRecord(record, ordinal) {
  const item = document.createElement("section");
  item.className = "ssa-metadata-record";
  item.dataset.recordOrdinal = String(ordinal);
  const heading = document.createElement("h5");
  heading.textContent = `Metadata entry ${ordinal + 1}`;
  const fields = document.createElement("dl");
  fields.className = "ssa-metadata-record-fields";
  appendMetadataField(fields, "namespace", "Namespace", record.namespace, true);
  appendMetadataField(fields, "key", "Key", record.key, true);
  appendMetadataField(fields, "presence", "Presence", record.presence);
  item.append(heading, fields);

  const valueHeading = document.createElement("h6");
  valueHeading.textContent = "Retained representation";
  item.append(valueHeading);
  if (record.value === null) {
    const absent = document.createElement("p");
    absent.className = "ssa-metadata-absent";
    absent.textContent = "Absent";
    item.append(absent);
  } else {
    appendRenderedMetadataValue(item, record.value);
  }
  return item;
}

function renderMetadataOverlay(candidate) {
  const overlay = document.createElement("section");
  const headingId = `ssa-metadata-heading-${overlayHeadingSequence}`;
  overlayHeadingSequence += 1;
  overlay.id = candidate.record.overlayId;
  overlay.className = "ssa-metadata-overlay";
  overlay.tabIndex = 0;
  overlay.setAttribute("role", "region");
  overlay.setAttribute("aria-labelledby", headingId);
  overlay.dataset.anchorOccurrenceIds = candidate.record.bindings
    .map((binding) => binding.occurrence.id)
    .join(" ");
  overlay.dataset.columnKey = candidate.columnKey;
  overlay.dataset.measuring = "true";

  const heading = document.createElement("h3");
  const inventory = candidate.record.inventories[0];
  const definingOwner =
    inventory.entity.defining_owner_id === null
      ? "absent"
      : inventory.entity.defining_owner_id;
  const roles = candidate.record.bindings
    .map((binding) => binding.roleName)
    .join(" | ");
  heading.id = headingId;
  heading.textContent =
    `SSA metadata; occurrence label ${JSON.stringify(candidate.record.label)}; ` +
    `entity ${inventory.entity.id}; defining owner ${definingOwner}; ` +
    `state roles ${roles}.`;
  overlay.append(heading);

  const bindingHeading = document.createElement("h4");
  bindingHeading.textContent = "Logical bindings";
  const bindings = document.createElement("ol");
  bindings.className = "ssa-metadata-bindings";
  for (const [ordinal, binding] of candidate.record.bindings.entries()) {
    const group = document.createElement("li");
    const fields = document.createElement("dl");
    group.className = "ssa-metadata-binding";
    group.dataset.bindingOrdinal = String(ordinal);
    appendMetadataField(fields, "role", "State role", binding.roleName);
    appendMetadataField(
      fields,
      "snapshot-id",
      "Snapshot ID",
      binding.occurrence.snapshot_id,
    );
    appendMetadataField(
      fields,
      "occurrence-id",
      "Occurrence ID",
      binding.occurrence.id,
    );
    group.append(fields);
    bindings.append(group);
  }
  overlay.append(bindingHeading, bindings);

  const inventorySection = document.createElement("section");
  inventorySection.className = "ssa-metadata-inventory";
  inventorySection.dataset.entityId = inventory.entity.id;
  const inventoryHeading = document.createElement("h4");
  inventoryHeading.textContent = "Snapshot-owned inventory";
  const identity = document.createElement("dl");
  identity.className = "ssa-metadata-identity";
  appendMetadataField(
    identity,
    "entity-id",
    "SSA entity ID",
    inventory.entity.id,
  );
  appendMetadataField(
    identity,
    "defining-owner-id",
    "Defining owner ID",
    inventory.entity.defining_owner_id === null
      ? "Absent"
      : inventory.entity.defining_owner_id,
  );
  inventorySection.append(inventoryHeading, identity);
  for (const [ordinal, record] of inventory.records.entries()) {
    inventorySection.append(renderMetadataRecord(record, ordinal));
  }
  overlay.append(inventorySection);
  return overlay;
}

function finitePixelValue(value) {
  if (!Number.isFinite(value)) {
    throw new Error("overlay geometry is not finite");
  }
  const rounded = Math.round(value * 1000) / 1000;
  return `${Object.is(rounded, -0) ? 0 : rounded}px`;
}

function placeMetadataOverlay(overlay, anchor) {
  const inlineMargin = 8;
  const gap = 8;
  overlay.style.setProperty("--overlay-inline-start", "0px");
  overlay.style.setProperty("--overlay-block-start", "0px");

  const viewportWidth = document.documentElement.clientWidth;
  const viewportHeight = document.documentElement.clientHeight;
  const anchorBox = anchor.getBoundingClientRect();
  const overlayBox = overlay.getBoundingClientRect();
  const dimensions = [
    viewportWidth,
    viewportHeight,
    anchorBox.top,
    anchorBox.right,
    anchorBox.bottom,
    anchorBox.left,
    overlayBox.width,
    overlayBox.height,
  ];
  if (!dimensions.every(Number.isFinite)) {
    overlay.remove();
    return false;
  }

  const above = anchorBox.top - gap - overlayBox.height;
  const blockStart =
    above >= 0 ? above : anchorBox.bottom + gap;
  const maximumInlineStart =
    viewportWidth - inlineMargin - overlayBox.width;
  const inlineStart = Math.min(
    Math.max(anchorBox.left, inlineMargin),
    Math.max(inlineMargin, maximumInlineStart),
  );
  if (
    blockStart < 0 ||
    blockStart + overlayBox.height > viewportHeight ||
    inlineStart < inlineMargin ||
    inlineStart + overlayBox.width > viewportWidth - inlineMargin
  ) {
    overlay.remove();
    return false;
  }

  overlay.style.setProperty(
    "--overlay-inline-start",
    finitePixelValue(inlineStart),
  );
  overlay.style.setProperty(
    "--overlay-block-start",
    finitePixelValue(blockStart),
  );
  delete overlay.dataset.measuring;
  return true;
}

function focusAndReveal(target) {
  suppressProgrammaticFocus = true;
  pendingTabFocusToken = null;
  target.focus({preventScroll: true});
  target.scrollIntoView({
    block: "nearest",
    inline: "nearest",
  });
  setTimeout(() => {
    suppressProgrammaticFocus = false;
  }, 0);
}

function closeMetadataOverlay() {
  const closingOccurrence = activeMetadataOccurrence;
  const closingOverlay = activeMetadataOverlay;
  const focusedRegion =
    closingOverlay !== null &&
    closingOverlay.contains(document.activeElement);
  if (closingOccurrence !== null) {
    delete closingOccurrence.record.element.dataset.metadataActive;
    closingOccurrence.record.element.setAttribute(
      "aria-expanded",
      "false",
    );
  }
  activeMetadataOccurrence = null;
  activeMetadataOverlay = null;
  if (closingOverlay !== null) {
    closingOverlay.remove();
  }
  if (
    focusedRegion &&
    closingOccurrence !== null &&
    currentOccurrenceRecord(closingOccurrence.record)
  ) {
    focusAndReveal(closingOccurrence.record.element);
  }
}

function commitMetadataOccurrence(next) {
  if (next === activeMetadataOccurrence) {
    return;
  }
  closeMetadataOverlay();
  if (next === null || !currentOccurrenceRecord(next.record)) {
    return;
  }
  const overlay = renderMetadataOverlay(next);
  next.record.descriptionElement.after(overlay);
  if (!placeMetadataOverlay(overlay, next.record.element)) {
    return;
  }
  next.record.element.dataset.metadataActive = "true";
  next.record.element.setAttribute("aria-expanded", "true");
  activeMetadataOccurrence = next;
  activeMetadataOverlay = overlay;
}

function metadataCandidate(record) {
  return Object.freeze({
    record,
    columnKey: record.columnKey,
  });
}

function activateMetadataOccurrence(record) {
  if (!currentOccurrenceRecord(record)) {
    return;
  }
  commitMetadataOccurrence(
    reduceMetadataOccurrence(activeMetadataOccurrence, {
      kind: "activate",
      candidate: metadataCandidate(record),
    }),
  );
}

function dismissMetadataOccurrence() {
  commitMetadataOccurrence(
    reduceMetadataOccurrence(activeMetadataOccurrence, {kind: "dismiss"}),
  );
}

function handleMetadataClick(inputEvent) {
  const target = inputEvent.target;
  if (!(target instanceof Element)) {
    dismissMetadataOccurrence();
    return;
  }
  const occurrenceElement = target.closest(".ssa-occurrence");
  if (occurrenceElement !== null) {
    const record = occurrenceRecordByElement.get(occurrenceElement);
    if (record !== undefined && currentOccurrenceRecord(record)) {
      activateMetadataOccurrence(record);
      return;
    }
  }
  if (
    activeMetadataOverlay !== null &&
    activeMetadataOverlay.contains(target)
  ) {
    return;
  }
  dismissMetadataOccurrence();
}

function handleMetadataScroll(inputEvent) {
  const target = inputEvent.target;
  if (
    activeMetadataOverlay !== null &&
    target instanceof Node &&
    activeMetadataOverlay.contains(target)
  ) {
    return;
  }
  dismissMetadataOccurrence();
}

function handleMetadataKey(inputEvent) {
  if (inputEvent.key === "Escape") {
    dismissMetadataOccurrence();
  }
}

function addIdentifier(target, identifier) {
  if (identifier !== null && !target.includes(identifier)) {
    target.push(identifier);
  }
}

function inventoryForEvent(event) {
  const inventory = {
    event_id: event.id,
    before_snapshot_id: event.before_snapshot_id,
    after_snapshot_id: event.after_snapshot_id,
    configuration_ids: [],
    style_ids: [],
    entity_ids: [],
    snapshot_ids: [],
    occurrence_ids: [],
    metadata_ids: [],
    stack_ids: [],
    operation_ids: [],
    relation_ids: [],
    effect_ids: [],
  };

  addIdentifier(inventory.snapshot_ids, event.before_snapshot_id);
  addIdentifier(inventory.snapshot_ids, event.after_snapshot_id);
  addIdentifier(inventory.entity_ids, event.root_entity_id);
  addIdentifier(inventory.stack_ids, event.invocation_stack_id);

  for (const snapshotId of inventory.snapshot_ids) {
    const snapshot = snapshotById.get(snapshotId);
    addIdentifier(inventory.configuration_ids, snapshot.configuration_id);
    addIdentifier(inventory.entity_ids, snapshot.root_entity_id);
    for (const span of snapshot.style_spans) {
      addIdentifier(inventory.style_ids, span.style_id);
    }
    for (const entityId of snapshot.entity_ids) {
      addIdentifier(inventory.entity_ids, entityId);
    }
    for (const occurrenceId of snapshot.occurrence_ids) {
      addIdentifier(inventory.occurrence_ids, occurrenceId);
    }
    for (const metadataId of snapshot.metadata_ids) {
      addIdentifier(inventory.metadata_ids, metadataId);
    }
  }

  for (const operation of operationsByEvent.get(event.id) || []) {
    addIdentifier(inventory.operation_ids, operation.id);
    addIdentifier(inventory.stack_ids, operation.invocation_stack_id);
    for (const entityId of operation.source_entity_ids) {
      addIdentifier(inventory.entity_ids, entityId);
    }
    for (const entityId of operation.destination_entity_ids) {
      addIdentifier(inventory.entity_ids, entityId);
    }
    for (const relation of relationsByOperation.get(operation.id) || []) {
      addIdentifier(inventory.relation_ids, relation.id);
      addIdentifier(inventory.entity_ids, relation.source_entity_id);
      addIdentifier(inventory.entity_ids, relation.destination_entity_id);
    }
    for (const effect of effectsByOperation.get(operation.id) || []) {
      addIdentifier(inventory.effect_ids, effect.id);
      addIdentifier(inventory.entity_ids, effect.affected_entity_id);
    }
  }

  for (let index = 0; index < inventory.entity_ids.length; index += 1) {
    const entity = entityById.get(inventory.entity_ids[index]);
    if (entity.defining_owner_id !== null) {
      addIdentifier(inventory.entity_ids, entity.defining_owner_id);
    }
  }
  return Object.freeze(inventory);
}

function canonicalRecords(records, identifiers) {
  const selected = new Set(identifiers);
  return records.filter((record) => selected.has(record.id));
}

function selectedFacts(frontier) {
  const inventories = frontier.map((eventId) =>
    inventoryForEvent(eventById.get(eventId)),
  );
  const identifiers = {
    configurations: [],
    styles: [],
    entities: [],
    snapshots: [],
    occurrences: [],
    metadata: [],
    stacks: [],
    events: frontier.slice(),
    operations: [],
    relations: [],
    effects: [],
  };
  for (const inventory of inventories) {
    for (const [domain, inventoryField] of [
      ["configurations", "configuration_ids"],
      ["styles", "style_ids"],
      ["entities", "entity_ids"],
      ["snapshots", "snapshot_ids"],
      ["occurrences", "occurrence_ids"],
      ["metadata", "metadata_ids"],
      ["stacks", "stack_ids"],
      ["operations", "operation_ids"],
      ["relations", "relation_ids"],
      ["effects", "effect_ids"],
    ]) {
      for (const identifier of inventory[inventoryField]) {
        addIdentifier(identifiers[domain], identifier);
      }
    }
  }
  return {
    selected_event_ids: frontier.slice(),
    inventories,
    canonical: {
      configurations: canonicalRecords(
        trace.configurations,
        identifiers.configurations,
      ),
      styles: canonicalRecords(trace.styles, identifiers.styles),
      entities: canonicalRecords(trace.entities, identifiers.entities),
      snapshots: canonicalRecords(trace.snapshots, identifiers.snapshots),
      occurrences: canonicalRecords(
        trace.occurrences,
        identifiers.occurrences,
      ),
      metadata: canonicalRecords(trace.metadata, identifiers.metadata),
      stacks: canonicalRecords(trace.stacks, identifiers.stacks),
      events: canonicalRecords(trace.events, identifiers.events),
      operations: canonicalRecords(trace.operations, identifiers.operations),
      relations: canonicalRecords(trace.relations, identifiers.relations),
      effects: canonicalRecords(trace.effects, identifiers.effects),
    },
  };
}

function renderFacts(state) {
  if (state.frontier.length === 0) {
    facts.textContent = "";
    facts.hidden = true;
    factsEmpty.hidden = false;
    return;
  }
  facts.textContent = JSON.stringify(selectedFacts(state.frontier), null, 2);
  facts.hidden = false;
  factsEmpty.hidden = true;
}

function renderSelection(state) {
  dismissMetadataOccurrence();
  discardProvenanceCandidates();
  const visible = new Set(visibleEventIds(state));
  let hiddenCount = 0;
  for (const eventId of eventPreorder) {
    const event = eventById.get(eventId);
    const row = eventRows.get(eventId);
    const button = eventButtons.get(eventId);
    const description = eventDescriptions.get(eventId);
    const isVisible = visible.has(eventId);
    row.hidden = !isVisible;
    if (!isVisible) {
      hiddenCount += 1;
    }
    if (state.frontier.includes(eventId)) {
      button.setAttribute("aria-current", "true");
    } else {
      button.removeAttribute("aria-current");
    }
    if (state.anchor === eventId) {
      button.dataset.rangeAnchor = "true";
    } else {
      delete button.dataset.rangeAnchor;
    }
    description.textContent = eventDescription(
      event,
      Number(button.dataset.depth),
      state.frontier.includes(eventId),
    );
  }
  eventTree.dataset.frontier = state.frontier.join(" ");
  eventTree.dataset.anchor = state.anchor === null ? "" : state.anchor;

  const reducedColumns = reduceColumns(state.frontier);
  renderedColumnState = Object.freeze(
    reducedColumns.map((column, index) => renderColumn(column, index)),
  );
  renderedEdgeState = Object.freeze(
    reducedColumns
      .slice(0, -1)
      .map((column, index) =>
        reduceAdjacentEdge(column, reducedColumns[index + 1]),
      ),
  );
  columns.replaceChildren(
    ...renderedColumnState.map((columnState) => columnState.element),
  );
  refreshOccurrenceDescriptions();
  emptyWorkspace.hidden = state.frontier.length !== 0;
  renderFacts(state);

  if (state.frontier.length === 0) {
    selectionStatus.textContent = `Selected: 0; hidden: ${hiddenCount}.`;
  } else if (state.frontier.length === 1) {
    selectionStatus.textContent = `Selected: 1; event: ${state.frontier[0]}; hidden: ${hiddenCount}.`;
  } else {
    selectionStatus.textContent = `Selected: ${state.frontier.length}; first: ${state.frontier[0]}; last: ${state.frontier[state.frontier.length - 1]}; hidden: ${hiddenCount}.`;
  }
}

let selectionState = freezeSelection([], null);

function focusEventTargetBeforeRender(eventId, nextState) {
  const nextVisible = visibleEventIds(nextState);
  if (nextVisible.includes(eventId)) {
    eventButtons.get(eventId).focus({preventScroll: true});
    return;
  }
  const survivingTargetAncestors = nextState.frontier.filter((candidateId) =>
    isStrictDescendant(eventId, candidateId),
  );
  if (survivingTargetAncestors.length !== 1) {
    throw new Error("a swallowed target must have one surviving ancestor");
  }
  eventButtons
    .get(survivingTargetAncestors[0])
    .focus({preventScroll: true});
}

function activateEvent(eventId, inputEvent) {
  const visibleBefore = visibleEventIds(selectionState).slice();
  const nextState = reduceSelection(
    selectionState,
    {
      kind: "activate",
      targetId: eventId,
      shiftKey: inputEvent.shiftKey,
      ctrlKey: inputEvent.ctrlKey,
      metaKey: inputEvent.metaKey,
    },
    visibleBefore,
  );
  if (nextState === selectionState) {
    return;
  }
  focusEventTargetBeforeRender(eventId, nextState);
  selectionState = nextState;
  renderSelection(selectionState);
}

function clearCurrentSelection() {
  clearSelection.focus({preventScroll: true});
  selectionState = reduceSelection(
    selectionState,
    {kind: "clear"},
    visibleEventIds(selectionState),
  );
  renderSelection(selectionState);
  clearSelection.focus({preventScroll: true});
}

function followSkipLink(inputEvent) {
  inputEvent.preventDefault();
  focusAndReveal(ssaWorkspace);
}

function clearPendingTabOnPointer() {
  pendingTabFocusToken = null;
}

appendEventBranch(null, eventTree, 0);
clearSelection.addEventListener("click", clearCurrentSelection);
skipLink.addEventListener("click", followSkipLink);
document.addEventListener("click", handleMetadataClick, true);
document.addEventListener("keydown", handleProvenanceKeyDown, true);
document.addEventListener("keydown", handleMetadataKey);
document.addEventListener("focusin", handleProvenanceFocusIn, true);
document.addEventListener("focusout", handleProvenanceFocusOut, true);
document.addEventListener("pointerdown", clearPendingTabOnPointer, true);
document.addEventListener("pointermove", handlePointerProvenanceMove, true);
document.addEventListener("scroll", handleMetadataScroll, true);
window.addEventListener("resize", dismissMetadataOccurrence);
if (
  window.visualViewport !== null &&
  window.visualViewport !== undefined
) {
  window.visualViewport.addEventListener("resize", dismissMetadataOccurrence);
  window.visualViewport.addEventListener("scroll", dismissMetadataOccurrence);
}
renderSelection(selectionState);
document.documentElement.setAttribute("data-krt-ready", "true");
