from __future__ import unicode_literals

from collections import OrderedDict as od


def parse_schema_arg(schema):
    """Split a comma-separated --schema/--exclude_schema value into a list
    of trimmed, non-empty schema names. Returns None for a falsy input."""
    if not schema:
        return None
    parts = [s.strip() for s in schema.split(",")]
    return [p for p in parts if p]


def filter_inspector_schemas(inspector, schemas=None, exclude=None):
    """Filter an already-built (unfiltered) inspector down to only the given
    schemas, or to exclude the given schemas. Needed for the multi-schema
    case (2+ comma-separated names), since schemainspect's own
    `filter_schema`/`one_schema` only accepts a single schema name and
    compares it for exact equality -- passing it a raw "a,b" string silently
    matches nothing.

    Mutates and returns `inspector`. Reuses schemainspect's own PROPS list
    (the same one `DBInspector.filter_schema` iterates over) so this stays
    in sync with whatever object types schemainspect tracks, rather than
    maintaining a second, driftable copy of that list here.
    """
    if not schemas and not exclude:
        return inspector
    if not hasattr(inspector, "filter_schema"):
        return inspector

    from schemainspect.pg.obj import PROPS

    schema_set = set(schemas) if schemas else None
    exclude_set = set(exclude) if exclude else None
    for prop in PROPS.split():
        att = getattr(inspector, prop, {})
        if schema_set:
            filtered = {
                k: v
                for k, v in att.items()
                if hasattr(v, "schema") and v.schema in schema_set
            }
        else:
            filtered = {
                k: v
                for k, v in att.items()
                if hasattr(v, "schema") and v.schema not in exclude_set
            }
        setattr(inspector, prop, filtered)
    return inspector


def differences(a, b, add_dependencies_for_modifications=True):
    a_keys = set(a.keys())
    b_keys = set(b.keys())
    keys_added = set(b_keys) - set(a_keys)
    keys_removed = set(a_keys) - set(b_keys)
    keys_common = set(a_keys) & set(b_keys)
    added = od((k, b[k]) for k in sorted(keys_added))
    removed = od((k, a[k]) for k in sorted(keys_removed))
    modified = od((k, b[k]) for k in sorted(keys_common) if a[k] != b[k])
    unmodified = od((k, b[k]) for k in sorted(keys_common) if a[k] == b[k])
    return added, removed, modified, unmodified
