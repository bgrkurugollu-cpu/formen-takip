import random

from app.services.synthetic.reference_data import (
    EMAIL_DOMAIN,
    _make_email,
    _make_phone_number,
    _normalize_email_local_part,
)


class TestNormalizeEmailLocalPart:
    def test_turkish_characters_are_transliterated(self):
        assert _normalize_email_local_part("Çağlar") == "caglar"
        assert _normalize_email_local_part("Öztürk") == "ozturk"
        assert _normalize_email_local_part("Şükrü") == "sukru"
        assert _normalize_email_local_part("İpek") == "ipek"
        assert _normalize_email_local_part("Işık") == "isik"

    def test_non_alphanumeric_characters_are_stripped(self):
        assert _normalize_email_local_part("Ali'nin") == "alinin"


class TestMakeEmail:
    def test_builds_first_dot_last_at_example_domain(self):
        used: set[str] = set()
        assert _make_email("Ali", "Yılmaz", used) == f"ali.yilmaz@{EMAIL_DOMAIN}"

    def test_duplicate_name_gets_numeric_suffix(self):
        used: set[str] = set()
        first = _make_email("Ali", "Yılmaz", used)
        second = _make_email("Ali", "Yılmaz", used)
        third = _make_email("Ali", "Yılmaz", used)
        assert first == f"ali.yilmaz@{EMAIL_DOMAIN}"
        assert second == f"ali.yilmaz2@{EMAIL_DOMAIN}"
        assert third == f"ali.yilmaz3@{EMAIL_DOMAIN}"
        assert len({first, second, third}) == 3

    def test_does_not_use_a_real_company_domain(self):
        used: set[str] = set()
        email = _make_email("Mehmet", "Demir", used)
        assert email.endswith("@example.com")


class TestMakePhoneNumber:
    def test_format_is_normalized_turkish_mobile(self):
        used: set[str] = set()
        phone = _make_phone_number(random.Random(1), used)
        assert phone.startswith("+905")
        assert len(phone) == 13
        assert phone[1:].isdigit()

    def test_generated_numbers_are_distinct(self):
        rng = random.Random(7)
        used: set[str] = set()
        numbers = {_make_phone_number(rng, used) for _ in range(200)}
        assert len(numbers) == 200
