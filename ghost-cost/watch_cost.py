#!/usr/bin/env python3
"""亡霊コストの見張り番（サンプル）。

「金額の大小」でなく「先月の同じ日と比べた“増え方”」と「新顔の課金」を見つける。
請求データはすべてダミー（sample_billing.jsonl）。実際はここをクラウドの請求APIに差し替える。

使い方:
    python watch_cost.py [--today YYYY-MM-DD] [--surge 1.5]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

DATA = Path(__file__).parent / "sample_billing.jsonl"


def load_rows() -> list[dict]:
    rows = []
    for line in DATA.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def cumulative_by_service(rows: list[dict], year: int, month: int, upto_day: int) -> dict[str, float]:
    """指定した年月の、1日〜upto_day までのサービス別の累計コスト。"""
    total: dict[str, float] = defaultdict(float)
    for r in rows:
        d = date.fromisoformat(r["date"])
        if d.year == year and d.month == month and d.day <= upto_day:
            total[r["service"]] += float(r["usd"])
    return dict(total)


def prev_month(y: int, m: int) -> tuple[int, int]:
    return (y - 1, 12) if m == 1 else (y, m - 1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--today", default="2026-06-10", help="点検する日付（既定: 2026-06-10）")
    ap.add_argument("--surge", type=float, default=2.0, help="この倍率を超えたら急増とみなす")
    args = ap.parse_args()

    today = date.fromisoformat(args.today)
    rows = load_rows()

    this_m = cumulative_by_service(rows, today.year, today.month, today.day)
    py, pm = prev_month(today.year, today.month)
    last_m = cumulative_by_service(rows, py, pm, today.day)

    surges, newcomers, normal = [], [], []
    for service in sorted(set(this_m) | set(last_m)):
        now = this_m.get(service, 0.0)
        before = last_m.get(service, 0.0)
        if before == 0.0 and now > 0.0:
            newcomers.append((service, before, now))           # 新顔（先月ゼロ→今月課金）
        elif before > 0.0 and now >= before * args.surge:
            surges.append((service, before, now, now / before))  # 急増
        else:
            normal.append(service)

    print(f"🐶 見張り番レポート（{today} / 先月同日と比較）")
    for s, b, n, ratio in surges:
        print(f"  ⚠ 急増   {s:<12} 先月 ${b:.2f} → 今月 ${n:.2f}（{ratio:.1f}倍）")
    for s, b, n in newcomers:
        print(f"  🆕 新顔   {s:<12} 先月 ${b:.2f} → 今月 ${n:.2f}（先月は無かった課金）")
    if normal:
        print(f"  ✅ 異常なし {' / '.join(normal)}")

    suspects = [s for s, *_ in surges] + [s for s, *_ in newcomers]
    if not suspects:
        print("\n亡霊は見つかりませんでした。平和です 😌")
        return

    # ── 安全弁：勝手に消さない。AIが「消していい？」と聞き、人が承認したものだけ消す ──
    print(f"\nあやしい課金が {len(suspects)} 件: {', '.join(suspects)}")
    print("これ、消していい？（承認したものだけ消します）")
    if not sys.stdin.isatty():
        print("  → 非対話実行なので、ここでは消さずに終了します（実行は人の承認待ち）。")
        return
    for s in suspects:
        ans = input(f"  「{s}」を消す？ [y/N] ").strip().lower()
        print(f"    → {'削除しました（のテイ）' if ans == 'y' else '残しました'}: {s}")


if __name__ == "__main__":
    main()
