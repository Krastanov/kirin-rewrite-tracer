# Provenance Graph and Deletion Storage

- **Context need:** Explanation
- **Open when:** Designing, implementing, or reviewing canonical provenance DTOs,
  forward or reverse navigation, deletion attribution, indexes, or persistence.
- **Do not open when:** Working only on mutation interception, rendered owner capture,
  rewrite-frame classification, or presentation over an already indexed graph.
- **Related specification IDs:** STK-003, STK-004, SYS-012, SYS-014, SYS-015, SYS-016,
  SYS-017
- **Review when:** Canonical relation direction, selected deletion APIs, provenance
  persistence, or index behavior changes.

The normative behavior lives in the
[provenance requirements](../v-model/02-system-requirements/provenance-navigation.md).
The base representation keeps one authoritative copy of every exact fact while making
both directions cheap to query.

## Direction and deletion options

| Representation | Advantage | Limitation | Judgment |
| --- | --- | --- | --- |
| Predecessor pointer on each later entity | Tiny for one-to-one lineage. | Deletion has no later entity; one-to-many and many-to-one are awkward. | Reject. |
| Independent forward and backward metadata | Direct lookup either way. | Duplicates assertions and creates synchronization and migration failure modes. | Reject. |
| Tombstone destination for deletion | Makes deletion look like an edge. | Invents an SSA entity and confuses a call with permanent object death. | Reject. |
| One directed relation or unary effect plus derived indexes | Handles arbitrary cardinality and deletion without duplicate truth. | Queries need small rebuildable indexes. | **Selected.** |

A mutation relation has one canonical direction: operation source → operation
destination. Either object may already exist before the call. The relation is a
first-class trace fact, not metadata stored only on the destination object. Index it by
both endpoints so “what came from this?” and “what produced this?” return the same
relation ID. Identity is smaller still: the same live object has one trace entity ID
across snapshots, and every occurrence points to it.

Deletion is a unary effect of an operation, not a backward edge with a missing
destination:

```text
EntityEffect[
  id, kind=statement_delete_completed,
  mutation_operation_id, affected_entity_id
]
```

The effect leads to its operation, the operation to its owning rewrite event, and both
operation and event to invocation stacks. That chain attributes a supported deletion
without inventing an output entity. Snapshot disappearance says only that an entity is
no longer beneath the captured root; it does not establish deletion or its cause.

`Statement.delete` detaches first and can later fail while deleting results. Its wrapper
therefore retains an incomplete operation shell but no completed deletion effect unless
the call returns normally. Exact attribution of the intermediate detach would require
another seam. Kirin also permits reinsertion of the same statement object, so the effect
is a historical operation occurrence, never a permanent entity property.

## Recommended factored storage

The exact frozen records live in
[`_model.py`](../../src/kirin_rewrite_tracer/_model.py) under CMP-001/CMP-007. The
implemented ownership shape is:

```text
TraceEntity[id, kind, qualified_type, defining_owner_id]
Snapshot[..., entity_ids, occurrence_ids, ...]
EntityOccurrence[id, snapshot_id, entity_id, role, start, end]

MutationOperation[
  id, sequence, owner_event_id, parent_operation_id, api,
  outcome, source_entity_ids, destination_entity_ids, invocation_stack_id
]
ProvenanceRelation[
  id, basis, source_entity_id, destination_entity_id, mutation_operation_id
]
EntityEffect[
  id, kind, affected_entity_id, mutation_operation_id
]
```

Relation `basis` is `statement_replaced_by`, `ssa_uses_retargeted_to`,
`statement_copied_to`, `result_copied_to`, `region_cloned_to`, `block_cloned_to`, or
`block_argument_cloned_to`. Identity is one entity ID; joining that ID's occurrences
across an event yields an identity projection, not a stored `ProvenanceRelation` or
invented mutation. One operation may justify several relations, and transient endpoints
need not occur in either snapshot.

Store each relation and effect once. Build `relations_by_source`,
`relations_by_destination`, `effects_by_entity`, `effects_by_operation`,
`operations_by_event`, and `occurrences_by_entity_and_snapshot` as disposable indexes.
They are not canonical facts, and rebuilding them in memory must preserve query results.

Keep capture, storage, and presentation separate:

1. The pinned adapter owns wrappers, entity registration, and rendered owner intervals.
2. Project DTOs validate exact relations, effects, and structured stacks.
3. Exporters may group or collapse data without changing the canonical trace.

## Anchors

- [`Statement.delete`](https://github.com/QuEraComputing/kirin/blob/7cdc2e02ab7ef0b3f80aaa88f930ff34015d240a/src/kirin/ir/nodes/stmt.py#L388-L400)
  and [delete-then-reinsert test](https://github.com/QuEraComputing/kirin/blob/7cdc2e02ab7ef0b3f80aaa88f930ff34015d240a/test/ir/test_stmt.py#L18-L27)
- [DCE deletion](https://github.com/QuEraComputing/kirin/blob/7cdc2e02ab7ef0b3f80aaa88f930ff34015d240a/src/kirin/rewrite/dce.py#L10-L19)
