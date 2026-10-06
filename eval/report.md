# Eval report

## MAE vs human

| dimension | MAE | n |
|---|---|---|
| content | - | 0 |
| structure | - | 0 |
| clarity | - | 0 |
| pacing | - | 0 |
| filler_words | - | 0 |
| total | - | 0 |

## Rules

| file | rule | result |
|---|---|---|
| answer.webm | no_emotion_words | PASS |
| answer.webm | every_item_has_evidence | PASS |
| answer_noisy.webm | clarity_null_when_noisy | PASS |
| answer_noisy.webm | no_emotion_words | PASS |
| answer_noisy.webm | every_item_has_evidence | PASS |

## Latency (total_ms)

| file | total_ms |
|---|---|
| answer.webm | 30903 |
| answer_noisy.webm | 25171 |
