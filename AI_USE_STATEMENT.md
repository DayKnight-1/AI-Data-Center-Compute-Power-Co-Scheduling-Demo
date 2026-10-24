# AI Use Statement

## Tools Used

- **`Deepseek`** — used during `design / coding / writing / debugging`.

## What AI Helped Produce

-  Scaffolding for the Streamlit layout and Plotly chart syntax.
-  Draft of the CSS used to hide the Streamlit "Deploy" button.
-  Suggestions for how to structure the local-search perturbations.
-  Boilerplate for the `Task` / `Schedule` dataclasses.


## How I Checked / Revised AI Output

- **Every AI-generated snippet was run before being merged.** No code was committed without observing it in the browser.
- **Sanity checks:** wI verified that smart scheduling always beats baseline on cost, that missed tasks are non-negative, and that the Gantt chart never overlaps two tasks on the same GPU pool beyond capacity.
- **Logic review:** for the lower-bound function, I hand-checked that the relaxed bound is always ≤ the smart-scheduling cost (otherwise it would be an invalid bound).
- **Refinement:** AI drafts were edited for correctness (e.g., the original lower-bound draft double-counted battery gain — I caught this and rewrote it).
- **Writing:** AI-drafted text was rewritten to reflect my actual design choices; where AI suggested features I did not build (e.g., MILP optimum), I removed them from the description.

