#!/usr/bin/env python3
"""AIの「完了しました」を“証拠”で確かめる関所。

done.json に書いた完了条件を1つずつ機械チェックし、
1つでも欠けたら「未完了（＝終わったフリ）」と判定する。
追加インストール不要（標準ライブラリのみ）。

    python verify.py
"""
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> int:
    spec = json.loads((HERE / "done.json").read_text(encoding="utf-8"))
    target = HERE / spec["target"]
    src = target.read_text(encoding="utf-8")

    checks = []  # (ラベル, 合否, 理由)

    # ① 宣言したテストが緑か（落ちたら未完了）
    r = subprocess.run(
        [sys.executable, "-m", "unittest", "-q", spec["tests"]],
        cwd=HERE, capture_output=True, text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},  # pyc 鮮度バグ回避＋repo を綺麗に保つ
    )
    checks.append(("テストが緑", r.returncode == 0,
                   "" if r.returncode == 0 else f"{spec['tests']} が落ちた"))

    # ② 必須の関数が定義されているか（消されてないか）
    for name in spec["must_implement"]:
        ok = f"def {name}(" in src
        checks.append((f"必須の関数 {name}() がある", ok,
                       "" if ok else f"{name} が見当たらない"))

    # ③ 「終わったフリ」を示す禁止ワードが残っていないか
    for word in spec["forbidden"]:
        absent = word not in src
        checks.append((f'禁止ワード "{word}" が無い', absent,
                       "" if absent else f'{target.name} に "{word}" が残ってる'))

    passed = all(ok for _, ok, _ in checks)

    print("✅ 完了：証拠がそろいました\n" if passed
          else "❌ 未完了：AIの「完了」は“フリ”でした\n")
    for label, ok, why in checks:
        mark = "✅" if ok else "❌"
        tail = "" if ok else f"  → {why}"
        print(f"  {mark} {label}{tail}")
    print(f"\n判定: {'PASS' if passed else 'FAIL（1つでも欠けたら“完了”とは認めない）'}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
