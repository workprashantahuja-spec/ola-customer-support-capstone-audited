"""Small correctness checks for the two text-splitting strategies."""

import unittest

from rag_index import Document, fixed_spans, make_chunks, sentence_spans


class ChunkingTests(unittest.TestCase):
    def test_fixed_windows_cover_all_characters_with_exact_overlap(self):
        text = "abcdefghijklmnopqrstuvwxyz"
        spans = fixed_spans(text, size=10, overlap=3)
        self.assertEqual(spans[0][0], 0)
        self.assertEqual(spans[-1][1], len(text))
        reconstructed = text[spans[0][0]:spans[0][1]]
        for previous, current in zip(spans, spans[1:]):
            self.assertEqual(previous[1] - current[0], 3)
            reconstructed += text[previous[1]:current[1]]
        self.assertEqual(reconstructed, text)
        self.assertTrue(all(end - start <= 10 for start, end in spans))

    def test_fixed_short_empty_and_invalid_parameters(self):
        self.assertEqual(fixed_spans(""), [])
        self.assertEqual(fixed_spans("tiny"), [(0, 4)])
        for size, overlap in [(0, 0), (5, 5), (5, -1)]:
            with self.assertRaises(ValueError):
                fixed_spans("text", size, overlap)

    def test_sentences_remain_complete_and_preserve_the_final_sentence(self):
        text = "First sentence. Second sentence! Third question? Fourth sentence. Last sentence."
        chunks = [text[start:end] for start, end in sentence_spans(text, 2)]
        self.assertEqual(chunks, ["First sentence. Second sentence!",
                                  "Third question? Fourth sentence.", "Last sentence."])
        self.assertEqual(" ".join(chunks), text)
        self.assertEqual(sentence_spans(""), [])

    def test_parent_document_and_offsets_are_preserved(self):
        doc = Document("example.md", "Example policy", "First. Second. Third.", "test-hash")
        for strategy in ("fixed", "sentence"):
            chunks = make_chunks([doc], strategy)
            self.assertEqual(chunks, make_chunks([doc], strategy))
            self.assertEqual(len({chunk.chunk_id for chunk in chunks}), len(chunks))
            for chunk in chunks:
                self.assertEqual(chunk.doc_id, doc.doc_id)
                self.assertEqual(chunk.body, doc.body[chunk.start_char:chunk.end_char])
                self.assertEqual(chunk.metadata["source"], "knowledge_base/example.md")


if __name__ == "__main__":
    unittest.main()
