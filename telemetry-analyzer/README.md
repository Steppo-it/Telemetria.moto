# telemetry-analyzer

Tool locale per analizzare i CSV di telemetria esportati dalla PWA TELAMETRIA.

## Setup

    pip install -r requirements.txt

## Uso

    python telemetry_analyzer.py percorso/al/file.csv

Genera nella stessa cartella del CSV: `report.html`, `filtered_telemetry.csv`,
`events.csv`, `curves.csv`.

Vedi `docs/superpowers/specs/2026-08-16-telemetry-analyzer-design.md` (nel
repo principale) per la logica di filtraggio/confidence completa.
