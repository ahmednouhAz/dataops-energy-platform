# Business questions

The dashboard must answer these three questions, reading only from the marts.

1. **Renewable share** — What share of electricity production is renewable
   (wind, solar, hydro, bioenergy), per region, hour by hour, and how does it evolve month by month?
2. **Temperature and consumption** — Does electricity consumption follow temperature?
   How much does consumption rise per degree of cold, per region?
3. **Peaks and exchanges** — When are the consumption peaks in each region, and which
   regions depend on imports from the rest of the grid (`ech_physiques`) at those times?

## Sources
| Source | What | Refresh | Key needed |
|---|---|---|---|
| eCO2mix regional (RTE / ODRÉ API) | consumption and production by source, per region, every 30 min | daily | no |
| Open-Meteo archive API | hourly temperature, wind and sunshine per region | daily | no |