"""お題：足し算・引き算ができる電卓。

AIが「完了しました！」と報告した状態 —— だが subtract は中身がない。
これが“終わったフリ”（完了詐欺）。verify.py を回すと“未完了”だと分かる。
"""


def add(a, b):
    return a + b


def subtract(a, b):
    raise NotImplementedError  # TODO: あとで実装
