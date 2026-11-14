{% macro mask_pii(column_name, visible_chars=0) %}
{#
    Masking for a column that WOULD carry personal data, if this
    project's actual sources ever did -- they don't (see
    contracts/*.yaml's `pii_note`: eco2mix and weather rows are
    region-level aggregates, never an individual). Written anyway,
    with a real demo + unit test (models/governance/), because
    CLAUDE.md's governance step asks to show the mechanism exists even
    when nothing in the warehouse needs it today -- a future source
    added to this project might.

    Two techniques, picked by whether visible_chars > 0:
      - visible_chars = 0 (default): full pseudonymization, a SHA-256
        hash of the value. The same input always hashes to the same
        output, so joins/grouping on the masked column still work, but
        the original value can't be recovered from the hash.
      - visible_chars > 0: partial redaction, keeping only the last N
        characters visible (e.g. "******7890" for a 10-digit id) --
        useful when a human still needs to recognize *which* record
        something is without seeing the full value.
#}
    {% if visible_chars > 0 %}
        concat(
            repeat('*', greatest(length({{ column_name }}) - {{ visible_chars }}, 0)),
            right({{ column_name }}, {{ visible_chars }})
        )
    {% else %}
        sha256({{ column_name }})
    {% endif %}
{% endmacro %}
