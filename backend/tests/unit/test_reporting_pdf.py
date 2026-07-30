
import re
import zlib

from app.services.reporting import render_pdf

TURKISH_CHARS = "ĞğIıİiŞşÇçÖöÜü"

HEADERS = ["Tesis Adı", "Şef", "Açıklama"]
ROWS = [
    {"Tesis Adı": "29. Tesis", "Şef": "Işıl Şimşek", "Açıklama": "Fire oranı düşük, çığır açan iyileşme"},
    {"Tesis Adı": "ĞĞĞ", "Şef": "ÜÇÜNCÜ", "Açıklama": "ĞğIıİiŞşÇçÖöÜü"},
]


def _tounicode_codepoints(pdf: bytes) -> set[int]:
    found: set[int] = set()
    for match in re.finditer(rb"stream\r?\n(.*?)endstream", pdf, re.S):
        raw = match.group(1)
        try:
            data = zlib.decompress(raw)
        except zlib.error:
            data = raw
        if b"beginbfchar" not in data and b"beginbfrange" not in data:
            continue
        for pair in re.finditer(rb"<([0-9A-Fa-f]{2,4})>\s*<([0-9A-Fa-f]{4})>", data):
            found.add(int(pair.group(2), 16))
    return found


class TestPdfTurkishCharacters:
    def test_output_is_a_pdf(self):
        pdf = render_pdf("Şirket Raporu", "Dönem: 2026", HEADERS, ROWS)
        assert pdf.startswith(b"%PDF-")

    def test_embeds_a_truetype_font(self):
        pdf = render_pdf("Şirket Raporu", "Dönem: 2026", HEADERS, ROWS)
        assert b"/FontFile2" in pdf, "Gömülü TrueType font yok — Türkçe karakterler bozulur."

    def test_all_turkish_letters_are_present_in_the_font_subset(self):
        pdf = render_pdf("Şirket Genel Performans Raporu", "Dönem: 2026", HEADERS, ROWS)
        mapped = _tounicode_codepoints(pdf)
        missing = [ch for ch in TURKISH_CHARS if ord(ch) not in mapped]
        assert not missing, f"PDF'te eksik Türkçe karakterler: {missing}"

    def test_font_registration_is_idempotent(self):
        first = render_pdf("Şirket Raporu", "Dönem: 2026", HEADERS, ROWS)
        second = render_pdf("Şirket Raporu", "Dönem: 2026", HEADERS, ROWS)
        assert first.startswith(b"%PDF-") and second.startswith(b"%PDF-")

    def test_handles_empty_row_set(self):
        pdf = render_pdf("Boş Rapor", "Dönem: 2026", HEADERS, [])
        assert pdf.startswith(b"%PDF-")
