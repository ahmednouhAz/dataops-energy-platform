-- Demonstrates macros/mask_pii.sql on literal example values -- not
-- applied to any real column, because nothing in this warehouse is
-- personal data (contracts/*.yaml's pii_note). Proves the masking
-- mechanism actually works, with a dbt unit test
-- (governance.yml) pinning the exact expected output for a known input,
-- same TP1 style as every other rule in this project: hand-written
-- input, known expected answer.
with example as (
    select
        '1234567890' as example_id,
        'alice@example.com' as example_email
)
select
    example_id,
    {{ mask_pii('example_id', visible_chars=4) }} as example_id_masked,
    example_email,
    {{ mask_pii('example_email') }} as example_email_hashed
from example
