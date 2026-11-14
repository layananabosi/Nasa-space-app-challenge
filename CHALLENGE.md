# The challenge

**NASA Space Apps Challenge 2026** · Nov 14–15, 2026 · theme: *The Next Frontier*
**Challenge:** Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars
[Challenge page](https://www.spaceappschallenge.org/2026/challenges/permanent-moon-base-locations-and-mars/)

## What NASA asks

> Selecting future landing sites and lunar base locations depends on many factors, including topography, geology, environment, and available resources. Places on Earth that have analogous characteristics to the Moon or Mars – the Atacama Desert, Haughton Crater, Death Valley – allow mission teams to test equipment and methods before they fly; however, such terrestrial analog sites are not entirely well characterized. Your challenge is to use open Earth, Moon, and Mars data from NASA and other space agencies to identify and characterize new terrestrial analogs for future bases or landing sites, drawing on deserts, polar regions, volcanic and arid terrains, caves, and other environments that share conditions with the lunar or Martian surface.

## How AnaloGraph answers each part

| The challenge asks to... | We do it by... |
| --- | --- |
| use open Earth and Mars data from NASA and other agencies | Copernicus DEM (ESA), MODIS (NASA), TerraClimate, ESA WorldCover, MOLA (NASA), SWIM (NASA) |
| **identify** new terrestrial analogs | scoring 23 Earth sites, including 7 new candidates (Negev, Dead Sea, Wadi Rum, Namib, Uyuni), against 6 Mars targets |
| **characterize** them | per-site sub-scores, "why" and "weakest match", Gap Index, and environmental gaps |
| for future bases or landing sites | four mission profiles: ice drilling, landing and rover traverse, habitat, astrobiology |
| deserts, polar regions, volcanic terrains... | candidates span hot and cold deserts, polar permafrost, volcanic fields and salt flats |

**Scope decision:** Mars only. The same pipeline works for the Moon by swapping the target layers (LOLA, Diviner), which we name as a next step.

## Resources NASA lists for this challenge

**Earth:** [NASA Earthdata Search](https://search.earthdata.nasa.gov/), [NASA Worldview](https://worldview.earthdata.nasa.gov/)
**Moon and Mars:** [NASA Planetary Data System](https://pds.nasa.gov/), [LRO data](https://pds-geosciences.wustl.edu/missions/lro/), [LRO Diviner](https://pds-geosciences.wustl.edu/missions/lro/diviner.htm)
**CSA:** [RADARSAT Constellation Mission](https://donnees-data.asc-csa.gc.ca/en/dataset/rcm), [RADARSAT-1](https://donnees-data.asc-csa.gc.ca/en/dataset/radarsat1), [SAR Python tutorial](https://github.com/asc-csa/Synthetic_Aperture_Radar_Tutorial)
**ESA:** [Copernicus Data Space Ecosystem](https://dataspace.copernicus.eu/), [ESA Open Science Catalog](https://opensciencedata.esa.int/)
**JAXA:** [G-Portal](https://gportal.jaxa.jp/gpr/index/index)

## Judging criteria

Impact · Creativity · Validity · Relevance · Presentation

## Submission requirements (check the official Project Submission Guide)

- [ ] Demo: **max 7 slides** including the title slide, in English, at a public link (Google Drive or GitHub)
- [ ] Slides show the team name, team members, the chosen challenge, and how space-agency open data made the project possible
- [ ] Final Project link: this public GitHub repository
- [ ] Every resource cited (data, libraries, tools); uncited projects can lose nominations
- [ ] Project page in English, terms checkbox ticked
- [ ] All links checked in a private browser window before submitting
- [ ] Final submission Sunday 20:00–23:59; aim to submit by 22:00
