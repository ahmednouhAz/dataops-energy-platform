-- One row per region x timestamp x energy source, clean rows only. Feeds
-- fct_energy_production. Only the 6 sources that have a matching row in
-- the energy_sources seed are unpivoted (pompage, stockage_batterie,
-- destockage_batterie and ech_physiques are storage/exchange, not
-- production by source, so they're left out of this fact on purpose).
with clean as (
    select *
    from {{ ref('int_eco2mix_checked') }}
    where reject_reason is null
)

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
