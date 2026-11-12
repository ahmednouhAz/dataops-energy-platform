-- Staging: give each measurement column its real numeric type.
-- No row is removed here (TP3 staging rule) -- that happens in intermediate
-- (step 5). try_cast returns NULL instead of crashing, same as try_strptime.
--
-- tco_*/tch_* (coverage and load-factor ratios) are deliberately left out:
-- they exist in raw but nothing downstream uses them yet. Add them here if
-- a future business question needs them.
select
    code_insee_region,
    libelle_region,
    nature,
    date_heure,
    try_cast(consommation as double) as consommation_mw,
    try_cast(thermique as double) as thermique_mw,
    try_cast(nucleaire as double) as nucleaire_mw,
    try_cast(eolien as double) as eolien_mw,
    try_cast(eolien_terrestre as double) as eolien_terrestre_mw,
    try_cast(eolien_offshore as double) as eolien_offshore_mw,
    try_cast(solaire as double) as solaire_mw,
    try_cast(hydraulique as double) as hydraulique_mw,
    try_cast(pompage as double) as pompage_mw,
    try_cast(bioenergies as double) as bioenergies_mw,
    try_cast(ech_physiques as double) as ech_physiques_mw,
    try_cast(stockage_batterie as double) as stockage_batterie_mw,
    try_cast(destockage_batterie as double) as destockage_batterie_mw,
    _dlt_load_id,
    _dlt_id
from {{ source('raw', 'eco2mix_regional') }}
