import unittest

from text_upload import decode_text_upload


class TextUploadTests(unittest.TestCase):
    def test_decodes_utf8_text(self):
        self.assertEqual(decode_text_upload("Client: Priya Shah".encode()), "Client: Priya Shah")

    def test_removes_utf8_byte_order_mark(self):
        self.assertEqual(decode_text_upload(b"\xef\xbb\xbfClient: Priya"), "Client: Priya")

    def test_decodes_utf16_text(self):
        source = "Client: Priya Shah\nIncome: INR 25 lakh"
        self.assertEqual(decode_text_upload(source.encode("utf-16")), source)

    def test_decodes_windows_text(self):
        source = "Client: Andr\xe9"
        self.assertEqual(decode_text_upload(source.encode("cp1252")), source)


if __name__ == "__main__":
    unittest.main()
