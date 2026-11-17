# Validation through different models

*Tip by Ellert van der Vecht, pushed to the `TipsAndTricks` repo on 10 March 2026. Moved here on 15 November 2026 so tips live in one place.*

## Opus vs Sonnet

Within Claude there are multiple models available and they have their own strengths.

As a good practice, ask a different model to review what the first model made. When you let Opus write code, ask Sonnet to do the code review, or the other way round. This does not always give a better result, but it will find something the first model did not find.

It is up to you whether you let the reviewing model apply its changes.

## See also

- The plan `plans/hackathon-2/ellert-van-der-vecht-multi-model-validation.md` works this idea out as an agent.
