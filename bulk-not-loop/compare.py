#!/usr/bin/env python3
"""“1枚ずつ目で見る”ループ版 vs “まとめて片づける”一括版の対比（AI呼び出しなし）。

動画の要点を手元で確かめる教材です。**本物のAI/LLMは一切呼びません**（APIキー不要・
追加インストール不要・標準ライブラリのみ）。やっているのは「処理回数」と「概算トークン」の
“そろばん”だけ。数字はすべて分かりやすいダミーで、実プロダクトの値ではありません。

見せたいこと:
  ・ループ版＝全部の書類を“1枚ずつ目で見て”読む。重い処理が「件数ぶん」積み上がり、
    一度に扱える量（＝コンテキストの上限）を超えて途中で止まる。
  ・一括版＝まずキーワードでざっくり仕分け → 文字で読める書類は“そのまま抽出”（軽い）→
    画像の書類だけ“目で見る”（重い）→ しかも1件ずつ独立処理なので上限に達しない。
    重い処理がごく僅かになり、最後まで片づく。

使い方:
  python compare.py            # 既定 1,300 件で比較
  python compare.py --count 500
"""
from __future__ import annotations

import argparse

# --- ざっくり概算のダミー値（分かりやすさ優先。実測値ではありません） -------------
CONTEXT_LIMIT = 200_000        # AIが一度に扱える量の目安（ダミー）。ここを超えると詰まる
VISION_TOKENS = 1_500          # 画像1枚を“目で見て”読むのに食う概算（重い）
TEXT_TOKENS = 80               # 電子の書類から文字を“そのまま抜き出す”概算（軽い）
KEYWORD_TOKENS = 5             # キーワードでの仕分け判定1件の概算（ごく軽い）
IMAGE_RATIO = 0.15             # 書類のうち“画像（写真）”の割合（残りは電子＝文字が取れる）


def make_documents(n: int) -> list[dict]:
    """ダミー書類を n 件つくる。7 件に1件くらいを“画像”にして、残りは電子扱い。

    値はすべてダミー。実在の会社・用途・データとは無関係です。
    """
    docs = []
    for i in range(n):
        is_image = (i % int(round(1 / IMAGE_RATIO))) == 0  # ≒15% を画像に
        docs.append({
            "id": i,
            "group": f"グループ{chr(ord('A') + i % 4)}",  # 中立な分類（用途は問わない）
            "kind": "画像" if is_image else "電子",
        })
    return docs


def run_loop(docs: list[dict]) -> dict:
    """ループ版: 全部を“1枚ずつ目で見て”読み、1つの文脈に積み上げていく。"""
    used = 0
    processed = 0
    stopped_at = None
    for d in docs:
        used += VISION_TOKENS          # 電子でも画像でも“目で見て”読む（重い）
        if used > CONTEXT_LIMIT:
            stopped_at = processed     # 上限を超えた → ここで停止
            break
        processed += 1
    return {
        "processed": processed,
        "stopped_at": stopped_at,
        "heavy_ops": len(docs),        # 本来こなす必要がある“重い読み取り”の総数
        "tokens_needed": len(docs) * VISION_TOKENS,
    }


def run_batch(docs: list[dict]) -> dict:
    """一括版: キーワード仕分け → 電子は文字抽出（軽い）→ 画像だけ目で見る（重い）。

    1件ずつ独立した小さな処理なので、1つの文脈に積み上がらず上限に達しない。
    """
    keyword_tokens = len(docs) * KEYWORD_TOKENS
    text_docs = [d for d in docs if d["kind"] == "電子"]
    image_docs = [d for d in docs if d["kind"] == "画像"]

    text_tokens = len(text_docs) * TEXT_TOKENS
    image_tokens = len(image_docs) * VISION_TOKENS  # 重いのはここだけ

    per_task_peak = VISION_TOKENS  # 1件あたりの最大（独立処理なので積み上がらない）
    return {
        "processed": len(docs),
        "heavy_ops": len(image_docs),
        "text_ops": len(text_docs),
        "tokens_total": keyword_tokens + text_tokens + image_tokens,
        "per_task_peak": per_task_peak,
        "fits": per_task_peak <= CONTEXT_LIMIT,
    }


def _fmt(n: int) -> str:
    return f"{n:,}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=1300, help="書類の件数（既定 1,300）")
    n = ap.parse_args().count

    docs = make_documents(n)
    n_image = sum(1 for d in docs if d["kind"] == "画像")
    loop = run_loop(docs)
    batch = run_batch(docs)

    bar = "=" * 60
    print(f"書類 {_fmt(n)} 件（うち画像 {_fmt(n_image)} 件／電子 {_fmt(n - n_image)} 件）")
    print(f"AIが一度に扱える量の目安（コンテキスト上限・ダミー）: {_fmt(CONTEXT_LIMIT)} トークン")
    print(bar)

    print("\n【ループ版】全部を“1枚ずつ目で見て”読む")
    print(f"  必要な“重い読み取り”: {_fmt(loop['heavy_ops'])} 回")
    print(f"  それに必要な概算トークン: {_fmt(loop['tokens_needed'])}"
          f"（上限の約 {loop['tokens_needed'] // CONTEXT_LIMIT} 倍）")
    if loop["stopped_at"] is not None:
        print(f"  → {_fmt(loop['stopped_at'])} 件目あたりで上限に達して ❌ 停止（残りは手つかず）")

    print("\n【一括版】キーワード仕分け → 電子は文字抽出 → 画像だけ目で見る")
    print(f"  文字でそのまま読めた（軽い）: {_fmt(batch['text_ops'])} 件")
    print(f"  “目で見た”（重い）: {_fmt(batch['heavy_ops'])} 件だけ")
    print(f"  1件あたりの最大トークン: {_fmt(batch['per_task_peak'])}"
          f"（独立処理なので積み上がらない → 上限に達しない）")
    print(f"  → 全 {_fmt(batch['processed'])} 件、✅ 最後まで完走")

    print("\n" + bar)
    reduce = 100 - round(batch["heavy_ops"] / loop["heavy_ops"] * 100)
    print(f"重い処理は {_fmt(loop['heavy_ops'])} 回 → {_fmt(batch['heavy_ops'])} 回（約 {reduce}% 削減）")
    print("台数を増やしたのではなく、“やり方”を変えただけ。")


if __name__ == "__main__":
    main()
