# Decision workflow redesign

Status: isolated prototype on `codex/decision-workflow-redesign`. The public data, scoring and census calculations are unchanged.

## Product promise

The application should help a leasing user move through one understandable decision journey:

**Explore the market → screen opportunities → compare locations → shortlist → prepare a brief.**

The meeting transcript is one input to this design. It is combined with the existing application behaviour, the available data, the Bailey Nelson decision use cases and established interaction-design guidance.

## Interaction principles

1. **Show the next useful action first.** Keep frequent tasks visible and disclose specialist controls when requested.
2. **Prefer recognition over recall.** Use plain labels, short explanations and visible selection states rather than relying on a user remembering terminology.
3. **Keep the map contextual.** The active workspace controls what the map represents; details and nearby context appear after a location is selected.
4. **Preserve analytical depth.** Secondary evidence, sources, data health and technical corrections remain available within two levels of disclosure.
5. **Reward progress, not activity.** Use readiness, evidence completion and workflow progress as feedback. Avoid points, leaderboards or decorative badges that could imply analytical certainty.
6. **Separate facts from judgements.** Raw values, derived comparisons, screening scores and private Bailey inputs must remain visibly distinct.

These choices follow progressive-disclosure guidance, task-based navigation patterns and research warning that dense dashboards can create avoidable cognitive load. The restrained progress model also follows gamification research that favours meaningful goals and immediate feedback over unrelated rewards.

## Information architecture

### Primary workspaces

- **Stores:** explore retailers and open a store's market context.
- **Places:** inspect centres and high-street corridors, their tenants and leasing intelligence.
- **Opportunities:** screen Bailey-free places using transparent, filterable evidence.
- **Compare:** compare stores, places, opportunities and manually added sites through one location model.

### Supporting intelligence

- **Trends:** network change and source freshness.
- **Data Health:** coverage, provenance, uncertainty and known limitations.
- **Tour and glossary:** help that remains available without competing with the core workflow.

### Contextual actions

- Map layers, add site and quick distance remain immediately available.
- Save, share, print brief and export are grouped under **Actions**.
- Location-specific actions also appear inside the selected location drawer.

## Compare workspace target

The current manual-candidate table and two-store distance tool should become one **Compare locations** workflow.

1. Search stores, centres, corridors, ranked opportunities or manual sites.
2. Add up to six locations for direct comparison.
3. Resolve a store to its accepted centre or corridor when appropriate, while retaining the store identity.
4. Compare raw facts and relative signals across:
   - demographics and growth;
   - Bailey coverage and possible cannibalisation;
   - optical validation;
   - key co-tenancy categories;
   - property and leasing context;
   - evidence completeness and freshness.
5. For a cohort of five to ten Bailey stores, show shared patterns, ranges and exceptions rather than an unhelpful average alone.
6. Keep the public lookalike rank, comparison similarity and any future private performance fit as separate concepts.

## Professional progress feedback

The interface can feel more engaging without turning commercial evidence into a game:

- show the stages **Discover, Validate, Compare, Shortlist, Brief**;
- show how much evidence is available for a selected location;
- identify the next evidence gap or useful action;
- confirm selections and saved shortlist changes immediately;
- celebrate a completed, sufficiently evidenced brief—not a high score.

## Delivery sequence

1. **Shell prototype:** calmer primary navigation, grouped supporting views, contextual actions and progressively disclosed retailer filters.
2. **Unified compare:** searchable location selection, comparison tray and normalised comparison dashboard.
3. **Decision cards:** concise opportunity and place summaries with expandable evidence.
4. **Shortlist workspace:** selected locations, readiness state and brief/export flow.
5. **Guided first run:** a short, dismissible task-based introduction for new users.
6. **Validation:** test real leasing tasks with representative users, measure task completion and refine labels and defaults.

## Guardrails

- Do not change census totals, place membership or scores as part of a visual redesign.
- Do not hide material uncertainty or missing evidence.
- Do not mix private Bailey data into the public static application.
- Do not publish this prototype until it passes the repository's full data, test and privacy checks and receives explicit approval.

## Design references

- Nielsen Norman Group, *Progressive Disclosure*: https://www.nngroup.com/articles/progressive-disclosure/
- GOV.UK Design System, *Help users to navigate a service*: https://design-system.service.gov.uk/patterns/step-by-step-navigation/
- GOV.UK Design System, *Task list*: https://design-system.service.gov.uk/components/task-list/
- Cheng et al., systematic review of gamification and behaviour change: https://pmc.ncbi.nlm.nih.gov/articles/PMC5376078/
- Valtolina et al., usability heuristics for gamified systems: https://www.mdpi.com/2076-3417/12/16/8188
