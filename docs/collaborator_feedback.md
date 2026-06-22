# Collaborator Feedback

## Scientific objective

The purpose is high-recall peak candidate detection followed by cross-scan correlation analysis.

The project analyzes high-pressure powder diffraction X-ray scans for UOTe. The goal is not to perfectly classify peaks in a single scan by eye. The goal is to detect many plausible peak candidates, then use correlation across scans/frames/pressures to decide which candidate peaks are reproducible and scientifically meaningful.

## Important collaborator feedback

Original collaborator/user quote captured in this thread:

> plot ideally all of them, if they are fake, they wont appear in many scans, but we dont know which peaks to look at, thats the point of the correlatioon plot

Interpretation:

- We should not pre-filter too aggressively by human expectations.
- Random false peaks/noise should usually not recur across many scans.
- The correlation plot is useful exactly because we do not know in advance which 2theta positions matter.
- However, the most recent exhaustive detector creates too many false candidate peaks on sloped backgrounds, tails, plateaus, and noisy regions.

## Disagreement / tension

There is a real tension between:

- high recall: mark every plausible tiny peak, including small shoulders;
- precision: avoid marking every slope wiggle, tail, baseline undulation, and noise fluctuation.

The user does not want a very conservative detector because it missed visible small peaks. The user also does not want the newest exhaustive detector because it marks many visually unnecessary points.

The next solution should not be "just lower thresholds again". It should use candidate generation plus peak-shape scoring, cross-scan recurrence, and/or a matched-filter/multi-scale approach.

