
from app.core.turkish import turkish_lower, turkish_sort_key


class TestTurkishLower:
    def test_capital_dotted_i_becomes_plain_i(self):
        assert turkish_lower("İBRAHİM") == "ibrahim"

    def test_capital_dotless_i_becomes_dotless(self):
        assert turkish_lower("IŞIK") == "ışık"

    def test_other_turkish_letters(self):
        assert turkish_lower("ÇĞÖŞÜ") == "çğöşü"


class TestTurkishSortKey:
    def test_special_letters_are_not_pushed_after_z(self):
        names = ["Zorlu", "Şimşek", "Yaman", "Çiftçi", "Öztaş", "Ünal", "Sarı", "Tekin"]
        assert sorted(names, key=turkish_sort_key) == [
            "Çiftçi", "Öztaş", "Sarı", "Şimşek", "Tekin", "Ünal", "Yaman", "Zorlu",
        ]

    def test_dotless_i_sorts_before_dotted_i(self):
        assert sorted(["İpek", "Işık"], key=turkish_sort_key) == ["Işık", "İpek"]

    def test_c_and_c_cedilla_are_adjacent(self):
        assert sorted(["Demir", "Çelik", "Can"], key=turkish_sort_key) == ["Can", "Çelik", "Demir"]

    def test_non_letters_sort_before_letters_and_keep_their_order(self):
        assert sorted(["Ali Kaya", "Ali-Kaya", "Alia"], key=turkish_sort_key) == [
            "Ali Kaya", "Ali-Kaya", "Alia",
        ]

    def test_prefix_sorts_before_longer_string(self):
        assert sorted(["Şahin", "Şah"], key=turkish_sort_key) == ["Şah", "Şahin"]

    def test_case_insensitive(self):
        assert turkish_sort_key("ŞİMŞEK") == turkish_sort_key("şimşek")
