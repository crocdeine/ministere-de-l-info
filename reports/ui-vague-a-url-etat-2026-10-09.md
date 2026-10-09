# Vague A, lot A2 : état de la vue dans l'URL (2026-10-09)

## Résumé exécutif
- Hachage `#/elections?scrutin=2022_pres_t2&commune=80021` : identifiants techniques seulement.
- `web/src/etat-url.ts` (lecture/écriture pures, 5 tests vitest) ; branché dans `PageElections.tsx`.
- Scrutin : `replaceState` ; commune choisie : `pushState` ; `hashchange`/`popstate` relisent l'URL.
- Valeurs invalides (scrutin absent du manifeste, `commune=1001`) : ignorées, message discret.
- Bouton « Copier le lien de cette vue » (`location.href`).
- E2E `npm run e2e:url` (`web/perf/url.mjs`) : lien, rechargement, retour/avance, valeurs
  invalides ; OK en WebKit et Chromium (headless-shell), échantillon Amiens.
- Fumée `npm run mesure` OK avec et sans mouvement réduit, aucune erreur de console ;
  tsc, vitest (19), build, budget tenus.
- Limites : pas de zoom ni de centre dans l'URL ; pas de schéma d'URL macOS (lot ultérieur) ;
  non vérifié dans la `.app` (Tauri non recompilé), où le lien copié est en `tauri://localhost`.

## Piège rencontré
`popstate` et `hashchange` se déclenchent tous deux au retour arrière ; le second lit une URL déjà
réécrite par l'effet état -> URL. Les messages d'avertissement ne sont donc remplacés que s'il y en
a de nouveaux.
