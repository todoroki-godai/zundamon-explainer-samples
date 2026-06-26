#!/usr/bin/env python3
"""AIに渡すスキル（手順書）を入れる前に点検する関所。

配下のすべての SKILL.md を走査し、危険なパターンを正規表現で検出します。
各スキルごとに ❌/✅ + リスクスコア + ヒットした該当行を表示します。
追加インストール不要（標準ライブラリのみ）。

    python scan.py <dir>

例:
    python scan.py skills/
"""
import re
import sys
from pathlib import Path


# ─── 検出パターン定義 ────────────────────────────────────────────────────────
# (カテゴリ, 説明, 正規表現パターン, リスク重み)
PATTERNS: list[tuple[str, str, str, int]] = [
    (
        "秘匿パス読み出し",
        "SSH 秘密鍵を参照している",
        r"~/\.ssh|\.ssh/id_rsa|id_rsa",
        30,
    ),
    (
        "秘匿ファイル読み出し",
        "環境変数ファイル (.env) を参照している",
        r"\.env\b",
        25,
    ),
    (
        "パイプ実行",
        "curl/wget の出力を直接 bash/sh に渡している（ダウンロード即実行）",
        r"curl\s[^\n]*\|\s*bash|curl\s[^\n]*\|\s*sh|wget\s[^\n]*\|\s*bash|wget\s[^\n]*\|\s*sh",
        40,
    ),
    (
        "外部送信",
        "標準入力やファイルを外部URLへ POST している",
        r"curl\s[^\n]*-d\s*@|curl\s[^\n]*--data\s",
        35,
    ),
    (
        "動的評価",
        "eval/exec を使っている（任意コード実行）",
        r"\beval\b|\bexec\b",
        30,
    ),
    (
        "自動承認",
        "セキュリティ審査の免除・自動承認を指示している",
        r"security.exempt|自動承認|確認なしで実行|審査を免除",
        40,
    ),
    (
        "不審な外部通信",
        "不審なドメイン（.invalid / localhost以外の動的URL）への通信",
        r"https?://[a-zA-Z0-9._-]+\.invalid/",
        20,
    ),
]

MAX_SCORE = sum(w for _, _, _, w in PATTERNS)  # 理論上の最大スコア


def scan_file(path: Path) -> tuple[list[tuple[str, str, str, int, list[str]]], int]:
    """1ファイルを走査し、ヒット情報とリスクスコアを返す。

    Returns:
        hits: [(カテゴリ, 説明, パターン, 重み, [ヒット行テキスト, ...])]
        score: リスクスコア（0〜100）
    """
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as e:
        return [], 0

    lines = text.splitlines()
    hits = []
    raw_score = 0

    for category, desc, pattern, weight in PATTERNS:
        matched_lines: list[str] = []
        rx = re.compile(pattern, re.IGNORECASE)
        for lineno, line in enumerate(lines, 1):
            if rx.search(line):
                # 長い行は切り詰めて表示
                snippet = line.strip()
                if len(snippet) > 80:
                    snippet = snippet[:77] + "..."
                matched_lines.append(f"  行{lineno:4d}: {snippet}")
        if matched_lines:
            hits.append((category, desc, pattern, weight, matched_lines))
            raw_score += weight

    # 0〜100 に正規化（複数パターンが重なっても 100 上限）
    score = min(100, int(raw_score * 100 / MAX_SCORE))
    return hits, score


def main() -> int:
    if len(sys.argv) < 2:
        print(f"使い方: python {Path(__file__).name} <スキルディレクトリ>")
        print(f"例:     python {Path(__file__).name} skills/")
        return 1

    target_dir = Path(sys.argv[1])
    if not target_dir.exists():
        print(f"エラー: '{target_dir}' が見つかりません。")
        return 1

    skill_files = sorted(target_dir.rglob("SKILL.md"))
    if not skill_files:
        print(f"'{target_dir}' 配下に SKILL.md が見つかりませんでした。")
        return 1

    print(f"\n点検対象: {target_dir}  （SKILL.md を {len(skill_files)} 件発見）")
    print("=" * 60)

    any_danger = False

    for skill_path in skill_files:
        skill_name = skill_path.parent.name
        hits, score = scan_file(skill_path)
        safe = len(hits) == 0
        mark = "✅" if safe else "❌"

        print(f"\n{mark} {skill_name}  [リスクスコア: {score}/100]")
        print(f"   ファイル: {skill_path}")

        if hits:
            any_danger = True
            for category, desc, _pattern, weight, matched_lines in hits:
                print(f"\n   ⚠  [{category}] {desc}（重み +{weight}）")
                for line_text in matched_lines:
                    print(f"     {line_text}")
        else:
            print("   危険なパターンは検出されませんでした。")

    print("\n" + "=" * 60)
    if any_danger:
        print("結果: ❌ 危険なパターンが見つかりました。入れる前に中身を確認してください。")
        return 1
    else:
        print("結果: ✅ 検出されたパターンはありませんでした。")
        return 0


if __name__ == "__main__":
    sys.exit(main())
