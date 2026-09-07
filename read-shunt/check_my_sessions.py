#!/usr/bin/env python3
"""自分の Claude Code は、大きなファイルを丸ごと読んでいるか？——を数える。

動画の結論①「仕組みを入れる前に、自分のAIが本当に丸ごと読んでいるか見る」を実行する道具。
**AIは1回も呼ばない**（手元に残っている作業ログを読むだけ）。APIキーもお金もかからない。

    python3 check_my_sessions.py          # 直近200セッションを集計
    python3 check_my_sessions.py 50       # 直近50セッションだけ

読むのは ~/.claude/projects/**/*.jsonl（Claude Code が自動で残している作業の記録）。
中身はどこにも送らない。集計した数だけを画面に出す。

読み方の判定:
  丸ごと読み = Read ツールで範囲（offset / limit）を指定しなかった呼び出し
  大きい     = 返ってきた中身が 14,000 文字以上（≒350行。横取りの既定の閾値に対応）
"""
import collections
import json
import pathlib
import sys

BASE = pathlib.Path.home() / ".claude/projects"
BIG_CHARS = 14000


def kind(name: str) -> str:
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext in ("png", "jpg", "jpeg", "gif", "webp", "svg"):
        return "画像"
    if ext == "pdf":
        return "PDF"
    if ext in ("py", "js", "ts", "tsx", "jsx", "go", "rs", "java", "rb", "php", "sh", "sql", "c", "cpp"):
        return "コード"
    if ext in ("md", "txt", "log", "rst"):
        return "文書・ログ"
    if ext in ("json", "yaml", "yml", "toml", "csv", "xml"):
        return "データ・設定"
    return f"その他({ext or '拡張子なし'})"


def scan(path: pathlib.Path):
    pending, reads = {}, []
    uses = collections.Counter()
    tok = collections.Counter()
    turns = 0
    for line in path.open(errors="ignore"):
        try:
            d = json.loads(line)
        except Exception:
            continue
        msg = d.get("message") or {}
        if d.get("type") == "assistant":
            turns += 1
            u = msg.get("usage") or {}
            tok["新規"] += u.get("input_tokens", 0)
            tok["初回読み込み"] += u.get("cache_creation_input_tokens", 0)
            tok["送り直し"] += u.get("cache_read_input_tokens", 0)
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        for b in content:
            if not isinstance(b, dict):
                continue
            if b.get("type") == "tool_use":
                uses[b.get("name")] += 1
                if b.get("name") == "Read":
                    inp = b.get("input") or {}
                    pending[b.get("id")] = (inp.get("file_path", ""),
                                            bool(inp.get("limit") or inp.get("offset")))
            elif b.get("type") == "tool_result" and b.get("tool_use_id") in pending:
                path_, partial = pending.pop(b["tool_use_id"])
                cont = b.get("content")
                text = cont if isinstance(cont, str) else json.dumps(cont, ensure_ascii=False)
                reads.append((path_, partial, len(text)))
    return turns, uses, tok, reads


def main() -> None:
    if not BASE.is_dir():
        print(f"作業ログが見つかりません: {BASE}")
        print("Claude Code をまだ使っていないか、保存先が違う可能性があります。")
        return
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    files = sorted(BASE.glob("*/*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]

    n = 0
    uses = collections.Counter()
    tok = collections.Counter()
    n_read = n_full = 0
    big_by_kind_n = collections.Counter()
    big_by_kind_c = collections.Counter()
    sess_with_big = 0
    for f in files:
        try:
            turns, u, t, reads = scan(f)
        except Exception:
            continue
        if turns == 0:
            continue
        n += 1
        uses.update(u)
        tok.update(t)
        has_big = False
        for path_, partial, chars in reads:
            n_read += 1
            if partial:
                continue
            n_full += 1
            if chars >= BIG_CHARS:
                k = kind(path_.split("/")[-1])
                big_by_kind_n[k] += 1
                big_by_kind_c[k] += chars
                has_big = True
        sess_with_big += has_big

    if n == 0:
        print("集計できるセッションがありませんでした。")
        return

    print(f"対象: 直近 {n} セッション\n")
    print("■ どの道具をどれだけ使っているか")
    for k, v in uses.most_common(6):
        print(f"    {k:12s} {v:8,d} 回")

    print(f"\n■ ファイルの読み方")
    print(f"    Read の呼び出し               {n_read:8,d} 回")
    if n_read:
        print(f"    うち丸ごと読み                {n_full:8,d} 回  ({n_full/n_read*100:.1f}%)")
    n_big = sum(big_by_kind_n.values())
    print(f"    うち大きいもの({BIG_CHARS:,}字以上) {n_big:8,d} 回")
    print(f"    それが1回でもあったセッション {sess_with_big:8,d} / {n}")

    if n_big:
        print(f"\n■ 大きく読んでいたものの正体")
        total_c = sum(big_by_kind_c.values())
        for k, c in big_by_kind_c.most_common():
            print(f"    {k:14s} {big_by_kind_n[k]:5,d}回 {c:12,d}字  {c/total_c*100:5.1f}%")

    total_in = sum(tok.values())
    if total_in:
        print(f"\n■ 入力の内訳（合計 {total_in:,} トークン）")
        for k in ("新規", "初回読み込み", "送り直し"):
            print(f"    {k:14s} {tok[k]:14,d}  {tok[k]/total_in*100:5.1f}%")

    print("\n" + "─" * 60)
    code_c = big_by_kind_c.get("コード", 0)
    if n_big == 0:
        print("判定: 大きなファイルの丸ごと読みは見つかりませんでした。")
        print("      → 読み込みを横取りする仕組みを入れても、止める対象がありません。")
    elif code_c / max(sum(big_by_kind_c.values()), 1) < 0.3:
        print("判定: 大きく読んでいるのは主にコード以外（画像・PDFなど）でした。")
        print("      → これらは要約モデルに回せないことが多く、横取りの効き目は限られます。")
    else:
        print("判定: 大きなコードファイルを丸ごと読んでいます。")
        print("      → 横取りの仕組みが効く可能性があります。shunt.py を試す価値があります。")
    if total_in and tok["送り直し"] / total_in > 0.7:
        print(f"補足: 入力の {tok['送り直し']/total_in*100:.0f}% は「前のやりとりの送り直し」です。")
        print("      読み込みを削るより、会話を短く区切るほうが効きます。")


if __name__ == "__main__":
    main()
