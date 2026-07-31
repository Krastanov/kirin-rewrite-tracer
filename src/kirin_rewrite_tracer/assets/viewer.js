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
const projectedSnapshotById = new Map();
const classesByStyle = new Map();
const eventButtons = new Map();
const eventRows = new Map();

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

function appendEventBranch(parentId, list, depth) {
  for (const event of childrenByParent.get(parentId) || []) {
    const item = document.createElement("li");
    item.dataset.eventId = event.id;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "event-button";
    button.dataset.eventId = event.id;
    button.dataset.depth = String(depth);
    button.textContent = `${event.id} — ${event.rule_type} — ${event.completion}`;
    button.addEventListener("click", (inputEvent) => {
      activateEvent(event.id, inputEvent);
    });
    eventButtons.set(event.id, button);
    eventRows.set(event.id, item);
    item.append(button);
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
  span.textContent = run.text;
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

function appendOccurrenceRecord(columnState, element, bindings) {
  const presentationOccurrence = bindings[0].occurrence;
  element.className = "ssa-occurrence";
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

  const record = Object.freeze({
    element,
    columnIndex: columnState.index,
    entityId: presentationOccurrence.entity_id,
    bindings,
  });
  const byEntity =
    columnState.occurrencesByEntity.get(record.entityId) || [];
  byEntity.push(record);
  columnState.occurrencesByEntity.set(record.entityId, byEntity);
  columnState.occurrences.push(record);
  element.addEventListener("pointerenter", () => {
    previewProvenance(record);
  });
  element.addEventListener("pointerleave", () => {
    endPointerProvenance(record);
  });
  return record;
}

function renderCode(column, columnState) {
  const [presentationRole] = column.roles;
  const projected = projectedSnapshotById.get(presentationRole.snapshotId);
  const code = document.createElement("code");
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
      activeWrapper = document.createElement("span");
      appendOccurrenceRecord(
        columnState,
        activeWrapper,
        occurrenceBindings(column, interactiveOccurrence),
      );
      code.append(activeWrapper);
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
  const columnState = {
    column,
    element: section,
    index,
    occurrences: [],
    occurrencesByEntity: new Map(),
  };
  section.className = "state-column";
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
let activePointerOccurrence = null;
const provenanceTargets = new Set();

function clearProvenancePreview() {
  activePointerOccurrence = null;
  for (const target of provenanceTargets) {
    delete target.dataset.provenanceRelated;
    delete target.dataset.provenanceIdentity;
    delete target.dataset.provenanceRelationIds;
  }
  provenanceTargets.clear();
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

function markProvenanceTarget(target, identity, relations) {
  target.dataset.provenanceRelated = "true";
  target.dataset.provenanceIdentity = identity ? "true" : "false";
  target.dataset.provenanceRelationIds = relations
    .map((relation) => relation.id)
    .join(" ");
  provenanceTargets.add(target);
}

function previewNeighbor(sourceRecord, neighborIndex, edge, sourceIsLeft) {
  if (edge.kind === "barrier" || edge.kind === "disconnected") {
    return;
  }
  const sourceRole = sourceIsLeft ? edge.leftRole : edge.rightRole;
  const targetRole = sourceIsLeft ? edge.rightRole : edge.leftRole;
  const sourceBinding = bindingForRole(sourceRecord, sourceRole);
  if (sourceBinding === undefined) {
    throw new Error("rendered source lacks its facing logical occurrence");
  }

  const neighbor = renderedColumnState[neighborIndex];
  for (const targetRecord of neighbor.occurrences) {
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
    if (identity || relations.length > 0) {
      markProvenanceTarget(targetRecord.element, identity, relations);
    }
  }
}

function previewProvenance(sourceRecord) {
  const currentColumn = renderedColumnState[sourceRecord.columnIndex];
  if (
    !sourceRecord.element.isConnected ||
    currentColumn === undefined ||
    !currentColumn.occurrences.includes(sourceRecord)
  ) {
    return;
  }
  clearProvenancePreview();
  activePointerOccurrence = sourceRecord;
  if (sourceRecord.columnIndex > 0) {
    previewNeighbor(
      sourceRecord,
      sourceRecord.columnIndex - 1,
      renderedEdgeState[sourceRecord.columnIndex - 1],
      false,
    );
  }
  if (sourceRecord.columnIndex + 1 < renderedColumnState.length) {
    previewNeighbor(
      sourceRecord,
      sourceRecord.columnIndex + 1,
      renderedEdgeState[sourceRecord.columnIndex],
      true,
    );
  }
}

function endPointerProvenance(sourceRecord) {
  if (activePointerOccurrence === sourceRecord) {
    clearProvenancePreview();
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
  clearProvenancePreview();
  const visible = new Set(visibleEventIds(state));
  let hiddenCount = 0;
  for (const eventId of eventPreorder) {
    const row = eventRows.get(eventId);
    const button = eventButtons.get(eventId);
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
  selectionState = nextState;
  renderSelection(selectionState);

  const targetRow = eventRows.get(eventId);
  if (targetRow.hidden) {
    const survivingTargetAncestors = selectionState.frontier.filter((candidateId) =>
      isStrictDescendant(eventId, candidateId),
    );
    if (survivingTargetAncestors.length === 1) {
      eventButtons.get(survivingTargetAncestors[0]).focus();
    }
  }
}

function clearCurrentSelection() {
  selectionState = reduceSelection(
    selectionState,
    {kind: "clear"},
    visibleEventIds(selectionState),
  );
  renderSelection(selectionState);
  clearSelection.focus({preventScroll: true});
}

appendEventBranch(null, eventTree, 0);
clearSelection.addEventListener("click", clearCurrentSelection);
renderSelection(selectionState);
document.documentElement.setAttribute("data-krt-ready", "true");
