# Moved To Archive

## 2026-06-14

- `logs/` -> `archive/logs/root/`
- `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/logs/` -> `archive/logs/h001_runtime/`

## Notes

- Raw logs are preserved locally but ignored by Git.
- No Python source module was archived in this pass because many historical manifest and reproducibility records still reference those modules.
- Generated Python bytecode cache was removed with a Docker root container after permission cleanup.
