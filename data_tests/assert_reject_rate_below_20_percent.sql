-- Stop the chain if more than 20% of eco2mix rows were rejected (TP3
-- pattern). A data test passes when it returns no rows.
--
-- Caveat (ADR 0002 addendum): the freshest ~7 hours of the real-time
-- dataset always arrive with every measurement null, which briefly pushes
-- the reject rate up right after loading a very recent, still-incomplete
-- day. 20% is wide enough to absorb that normal trailing-edge gap (one
-- partial day measured 9.8% of the whole table) while still catching a
-- real upstream problem (e.g. a renamed column making every row fail).
select
    count(*) filter (where reject_reason is not null) as n_rejected,
    count(*) as n_total
from {{ ref('int_eco2mix_checked') }}
having count(*) filter (where reject_reason is not null) > 0.20 * count(*)
