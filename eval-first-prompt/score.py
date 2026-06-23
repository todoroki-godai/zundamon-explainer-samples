#!/usr/bin/env python3
"""ものさし：プロンプトの分類結果を採点する（LLMは呼ばない・ただの突き合わせ）。

使い方:
    1. prompt.txt で cases.jsonl を分類し、outputs/predictions.jsonl に
       {"id": 1, "label": "解決済み"} の形式で1行ずつ保存する（Claude Code に頼むのが楽）。
    2. python score.py

正答率と「外したケース」を表示する。これを見て prompt.txt を直す → また測る、を繰り返す。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
CASES = HERE / "cases.jsonl"
PREDS = HERE / "outputs" / "predictions.jsonl"
SAMPLE = HERE / "outputs" / "predictions.sample.jsonl"  # 初見でも動かせるお試し予測（わざと雑）


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def main() -> None:
    cases = {c["id"]: c for c in load_jsonl(CASES)}

    if PREDS.exists():
        target, is_sample = PREDS, False
    elif SAMPLE.exists():
        target, is_sample = SAMPLE, True   # 自分の予測がまだ無ければ、お試し予測を採点
    else:
        print(f"予測ファイルがありません: {PREDS}")
        print("→ prompt.txt で cases.jsonl を分類し、上の形式で保存してください")
        print('  （Claude Code に「prompt.txt のルールで cases.jsonl を分類して')
        print('    outputs/predictions.jsonl に出して」と頼むのが早いです）')
        sys.exit(1)

    if is_sample:
        print("※ お試し予測（predictions.sample.jsonl）を採点中。")
        print("  自分の予測を outputs/predictions.jsonl に置くと、そちらに差し替わります。\n")

    preds = {p["id"]: p["label"] for p in load_jsonl(target)}

    correct, misses = 0, []
    for cid, case in cases.items():
        got = preds.get(cid)
        if got == case["label"]:
            correct += 1
        else:
            misses.append((cid, case["text"], case["label"], got))

    total = len(cases)
    print(f"正答率: {correct}/{total} = {correct / total:.0%}")
    if misses:
        print("\n外したケース:")
        for cid, text, want, got in misses:
            print(f"  #{cid} 「{text}」")
            print(f"      正解={want!r} / 予測={got!r}")
        print("\n→ この外れ方を見て prompt.txt を直し、もう一度分類して score.py を回す")
    else:
        print("全問正解！このプロンプトで安定して分類できています 🎉")


if __name__ == "__main__":
    main()
