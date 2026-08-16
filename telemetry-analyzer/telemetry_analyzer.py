#!/usr/bin/env python3
"""CLI: python telemetry_analyzer.py file.csv [--outdir DIR]"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from analyzer.loading import load_csv, compute_time_deltas
from analyzer.filtering import build_filtered_dataframe
from analyzer.events import detect_events, events_to_dataframe
from analyzer.curves import detect_curves, curves_to_dataframe
from analyzer.report.assemble import assemble_report_html


def main():
    parser = argparse.ArgumentParser(description='Analizza un CSV di telemetria TELAMETRIA.')
    parser.add_argument('csv_path', help='Percorso al CSV esportato dalla PWA')
    parser.add_argument('--outdir', default=None, help='Cartella di output (default: stessa del CSV)')
    args = parser.parse_args()

    outdir = args.outdir or os.path.dirname(os.path.abspath(args.csv_path)) or '.'
    os.makedirs(outdir, exist_ok=True)

    print(f'Carico {args.csv_path}...')
    df = compute_time_deltas(load_csv(args.csv_path))

    print('Filtro i segnali (Hampel, cross-sensor, confidence)...')
    filtered_df = build_filtered_dataframe(df)

    print('Rilevo eventi...')
    events = detect_events(filtered_df)

    print('Rilevo curve...')
    curves = detect_curves(filtered_df, events)

    filtered_csv_path = os.path.join(outdir, 'filtered_telemetry.csv')
    events_csv_path = os.path.join(outdir, 'events.csv')
    curves_csv_path = os.path.join(outdir, 'curves.csv')
    report_path = os.path.join(outdir, 'report.html')

    filtered_df.to_csv(filtered_csv_path, index=False)
    events_to_dataframe(events).to_csv(events_csv_path, index=False)
    curves_to_dataframe(curves).to_csv(curves_csv_path, index=False)

    print('Genero il report HTML...')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(assemble_report_html(filtered_df, events, curves))

    print(f'Fatto. Output in {outdir}:')
    for path in (report_path, filtered_csv_path, events_csv_path, curves_csv_path):
        print(f'  - {path}')


if __name__ == '__main__':
    main()
