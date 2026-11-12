-- One row per region x timestamp x energy source, clean rows only. Feeds
-- fct_energy_production. Only the 6 sources that have a matching row in
-- the energy_sources seed are unpivoted (pompage, stockage_batterie,
-- destockage_batterie and ech_physiques are storage/exchange, not
-- production by source, so they're left out of this fact on purpose).
--
-- A null value here is NOT a quality problem to quarantine -- int_eco2mix_
-- checked already only lets reject_reason is null rows through. It's a
-- region that simply has no plant of that type: found while backfilling
-- (step 10), 5 of the 12 regions (Ile-de-France, Bretagne, Pays de la
-- Loire, Bourgogne-Franche-Comte, PACA) have zero nuclear capacity and
-- report null nucleaire for their entire history, not a tracking gap.
-- A "production" fact with no production to report isn't a fact; omit it
-- rather than store a meaningless null, same logic a star schema uses for
-- any not-applicable dimension combination.
with clean as (
    select *
    from {{ ref('int_eco2mix_checked') }}
    where reject_reason is null
),

unpivoted as (
    select code_insee_region, date_heure, 'thermique' as energy_source, thermique_mw as production_mw from clean
    union all
    select code_insee_region, date_heure, 'nucleaire' as energy_source, nucleaire_mw as production_mw from clean
    union all
    select code_insee_region, date_heure, 'eolien' as energy_source, eolien_mw as production_mw from clean
    union all
    select code_insee_region, date_heure, 'solaire' as energy_source, solaire_mw as production_mw from clean
    union all
    select code_insee_region, date_heure, 'hydraulique' as energy_source, hydraulique_mw as production_mw from clean
    union all
    select code_insee_region, date_heure, 'bioenergies' as energy_source, bioenergies_mw as production_mw from clean
)

select *
from unpivoted
where production_mw is not null
