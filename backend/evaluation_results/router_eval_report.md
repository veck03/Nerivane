# Router Evaluation

Dataset: `D:\Projects\Nerivane\data\evaluation\eval_dataset.json`

## Summary

- Total questions: 20
- Router-scored questions: 16
- Correct routes: 15
- Strict route accuracy (failed calls count as incorrect): 93.8%
- Valid route outputs: 16/16
- Router call failures: 0
- Accuracy among valid outputs: 93.8%
- Route coverage: 100.0%
- Answerable questions: 16
- Unanswerable questions: 4
- Abstention cases excluded from route accuracy: 4

Expected route counts:

| PAPER | DATA | BOTH | NONE |
| ---: | ---: | ---: | ---: |
| 12 | 4 | 0 | 0 |

> The dataset has no BOTH examples, so this run does not measure BOTH-route accuracy.

## Incorrect predictions

| ID | Expected | Predicted | Question / error |
| --- | --- | --- | --- |
| Q016 | DATA | both | What is the difference between the maximum and minimum recorded ocean temperatures? |

## Router call failures

No router calls failed.

## Abstention cases

These rows are not sent to `route_query()`: the runtime router chooses a source (`paper`, `data`, `both`, or `none`), while abstention is an end-to-end answerability behavior.

| ID | Answerable | Question |
| --- | --- | --- |
| Q017 | False | What will the exact global average ocean temperature be in 2035? |
| Q018 | False | Which specific research vessel collected every observation in our ocean dataset? |
| Q019 | False | What is the exact causal contribution of Pacific subtropical high variability to global mean sea level rise, according to our papers? |
| Q020 | False | What will the temperature be at latitude 10, longitude 60, at a depth of 500 meters on 2030-01-01? |
