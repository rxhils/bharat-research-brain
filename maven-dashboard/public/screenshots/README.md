# Screenshot slots — /how-it-works explainer

Drop phone screenshots here (PNG, ~390×844). Filenames are matched exactly;
until a file exists, the explainer shows a tasteful labelled placeholder.

| Filename                  | Layer            | Screen                                          | Status       |
| ------------------------- | ---------------- | ----------------------------------------------- | ------------ |
| `market-mode.png`         | 1 · Market Mode  | "Ask AI" — *What are the markets telling you?*   | provided     |
| `portfolio-mode.png`      | 2 · Portfolio    | "Ask AI" — *What is your portfolio telling you?* | provided     |
| `portfolios-stable.png`   | 2 · Portfolio    | Models ranked — Stable (Core / Quality)          | provided     |
| `portfolios-balanced.png` | 2 · Portfolio    | Models ranked — Balanced (Growth/Momentum/Income)| provided     |
| `portfolios-bold.png`     | 2 · Portfolio    | Models ranked — Bold (Quant / Value / Contrarian)| provided     |
| `focus.png`               | 3 · Focus        | Thematic baskets screen                          | add later    |
| `broker-connect.png`      | 4 · Broker       | Connect screen (read-only)                        | add later    |
| `broker-sync.png`         | 4 · Broker       | Holdings synced & compared                        | add later    |

Slot→layer mapping lives in `components/explainer.tsx` (the `LAYERS` array).
