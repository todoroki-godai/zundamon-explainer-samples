import unittest

from calc import add, subtract


class TestCalc(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(2, 3), 5)

    def test_subtract(self):
        # 「完了しました」と言うなら、ここが通るはず。
        # ★テストは複数ケースで。1件だけだと、AIがその数値に合わせる“近道”
        #   （例: return 2）を覚えて通り抜ける——これがまさに reward hacking。
        self.assertEqual(subtract(5, 3), 2)
        self.assertEqual(subtract(10, 4), 6)
        self.assertEqual(subtract(0, 5), -5)


if __name__ == "__main__":
    unittest.main()
