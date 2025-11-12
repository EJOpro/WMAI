import unittest
from datetime import datetime

try:
    from .text_splitter import TextSplitter
except ImportError:  # pragma: no cover
    from text_splitter import TextSplitter  # type: ignore


class TextSplitterDeterminismTests(unittest.TestCase):
    def setUp(self) -> None:
        self.splitter = TextSplitter()
        self.fixed_datetime = datetime(2025, 1, 1, 12, 0, 0)

    def _assert_deterministic(self, text: str, expected_sentences: int) -> None:
        first = self.splitter.split_text(text, created_at=self.fixed_datetime)
        second = self.splitter.split_text(text, created_at=self.fixed_datetime)

        self.assertEqual(first, second, "동일한 입력에 대해 분할 결과가 달라졌습니다.")
        self.assertEqual(len(first), expected_sentences)

    def test_basic_punctuation_split(self):
        text = "안녕! 반가워요. 오늘은 좋은 날인가요?"
        self._assert_deterministic(text, expected_sentences=3)

    def test_whitespace_normalization(self):
        text = "서비스가    너무 별로예요...   탈퇴를 고민 중입니다!"
        self._assert_deterministic(text, expected_sentences=2)

    def test_sentence_without_terminal_punctuation(self):
        text = "이 서비스는 진짜 별로야 계속 이렇게 나올거냐"
        results = self.splitter.split_text(text, created_at=self.fixed_datetime)
        self.assertEqual(results, self.splitter.split_text(text, created_at=self.fixed_datetime))
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0]["sentence"].endswith("."), "마침표 보정이 누락되었습니다.")


if __name__ == "__main__":
    unittest.main()

