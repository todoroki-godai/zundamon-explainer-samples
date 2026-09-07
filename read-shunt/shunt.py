#!/usr/bin/env python3
"""PreToolUse hook: 大きなファイルの直接読み込みを止め、安いワーカーモデルの要約へ回す。

Spotify の記事（Portal by Spotify cut my Claude Code token usage by 90%）の
check-file-size / check-bash-read を、手元の Claude Code で再現したもの。
"""
import json, os, re, shlex, sys, time

MIN_LINES = int(os.environ.get("SHUNT_MIN_LINES", "350"))
BIN = os.environ.get("SHUNT_BIN", "bulk-reader")
READ_CMDS = {"cat", "head", "tail", "less", "more"}


def too_big(path):
    try:
        with open(path, "rb") as f:
            n = sum(1 for _ in f)
    except OSError:
        return None
    return n if n > MIN_LINES else None


def log(event, **kw):
    """hook が呼ばれたこと自体を記録する。呼ばれていないのか、呼ばれて素通ししたのかを区別するため。"""
    f = os.environ.get("SHUNT_HOOK_LOG")
    if not f:
        return
    try:
        with open(f, "a") as fp:
            fp.write(json.dumps({"t": time.strftime("%H:%M:%S"), "event": event, **kw}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def deny(path, n):
    log("blocked", path=path, lines=n)
    print(
        f"{path} は {n} 行あり、直接読むと文脈を大量に消費します（上限 {MIN_LINES} 行）。\n"
        f"代わりに Bash で次を実行し、要約だけを受け取ってください:\n"
        f"  {BIN} {shlex.quote(path)} \"<知りたいことを具体的に>\"\n"
        f"知りたいことは具体的に書くほど良い要約が返ります。",
        file=sys.stderr)
    sys.exit(2)


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    log("called", tool=data.get("tool_name"))
    try:
        tool = data.get("tool_name")
        ti = data.get("tool_input", {})
        if tool == "Read":
            p = ti.get("file_path", "")
            # 部分読み（offset/limit 指定）は通す＝行番号が要る作業を殺さないため
            if p and not ti.get("limit"):
                n = too_big(p)
                if n:
                    deny(p, n)
        elif tool == "Bash":
            cmd = ti.get("command", "")
            for seg in re.split(r"&&|\|\||[;|\n]", cmd):
                toks = shlex.split(seg, posix=True) if seg.strip() else []
                if not toks or os.path.basename(toks[0]) not in READ_CMDS:
                    continue
                for t in toks[1:]:
                    if t.startswith("-"):
                        continue
                    n = too_big(t)
                    if n:
                        deny(t, n)
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)  # fail-open


if __name__ == "__main__":
    main()
