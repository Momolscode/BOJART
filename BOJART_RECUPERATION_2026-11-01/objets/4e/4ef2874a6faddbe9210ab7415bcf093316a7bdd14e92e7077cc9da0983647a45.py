#!/usr/bin/env python3
"""Normalize an already-authorized owner-insights response; never fetch or publish."""
import argparse
import json
import math
from pathlib import Path


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value if math.isfinite(value) and value >= 0 else None


def normalize(payload):
    for _ in range(4):
        if 'status' in payload:
            break
        payload = payload.get('structuredContent', {})
    if payload.get('status') != 'available' or payload.get('accessLevel') != 'owner':
        raise ValueError('Authorized owner-insights are not available; no metrics fabricated')
    rows = []
    for r in payload.get('reels', []):
        duration = number(r.get('durationSeconds'))
        ms = number(r.get('avgWatchTimeMs'))
        seconds = None if ms is None else ms / 1000
        portion = None if seconds is None or not duration else 100 * seconds / duration
        rows.append({
            'reel_id': r.get('reelId'), 'permalink': r.get('permalink'),
            'duration_s': duration, 'mean_watch_time_s': seconds,
            'mean_watch_ratio_pct': portion,
            'provider_avg_watched_pct': number(r.get('avgWatchedPct')),
            'completion_rate': None,
            'plays': number(r.get('playCount')), 'shares': number(r.get('shares')),
            'saves': number(r.get('saves')), 'skip_rate_as_returned': number(r.get('skipRate')),
            'skip_rate_unit_verified': False,
            'traffic_paid_vs_organic': None,
        })
    return {
        'scope': 'authorized owner-insights response supplied locally',
        'window': payload.get('window'), 'is_truncated': payload.get('isTruncated'),
        'next_cursor': payload.get('recentMediaNextCursor'), 'reels': rows,
        'definitions': {
            'mean_watch_ratio_pct': '100 * mean watch seconds / video duration; may exceed 100; not completion',
            'completion_rate': 'unknown: no explicit completion numerator/denominator supplied',
            'missing': 'null; numeric zero remains zero',
            'skip_rate': 'value retained without guessing fraction vs percentage or time threshold',
        },
        'causal_retention_effect_proven': False,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('input', type=Path)
    ap.add_argument('--out', required=True, type=Path)
    a = ap.parse_args()
    if a.out.exists():
        ap.error('Output already exists')
    result = normalize(json.loads(a.input.read_text()))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps({'rows': len(result['reels']), 'audience_effect_proven': False}))


if __name__ == '__main__':
    main()
