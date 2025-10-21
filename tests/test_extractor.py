"""
Тесты для Email Extractor
"""

import tempfile
import os

import pytest

from src.email_extractor import EmailExtractor
from src.utils import is_valid_email, validate_emails, normalize_url


class TestEmailValidation:
    """Тесты для валидации email-адресов"""

    def test_valid_emails(self):
        """Тест валидных email-адресов"""
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "user+tag@example.org",
            "user123@test-domain.com"
        ]

        for email in valid_emails:
            assert is_valid_email(email), f"Email {email} должен быть валидным"

    def test_invalid_emails(self):
        """Тест невалидных email-адресов"""
        invalid_emails = [
            "invalid-email",
            "@example.com",
            "test@",
            "test@.com",
            "test..test@example.com",
            ""
        ]

        for email in invalid_emails:
            assert not is_valid_email(email), f"Email {email} должен быть невалидным"

    def test_validate_emails_list(self):
        """Тест фильтрации списка email-адресов"""
        emails = [
            "valid@example.com",
            "invalid-email",
            "another@test.org",
            "@invalid.com"
        ]

        valid_emails = validate_emails(emails)
        assert len(valid_emails) == 2
        assert "valid@example.com" in valid_emails
        assert "another@test.org" in valid_emails


class TestURLNormalization:
    """Тесты для нормализации URL"""

    def test_normalize_url_with_protocol(self):
        """Тест URL с протоколом"""
        url = "https://example.com"
        assert normalize_url(url) == "https://example.com"

    def test_normalize_url_without_protocol(self):
        """Тест URL без протокола"""
        url = "example.com"
        assert normalize_url(url) == "https://example.com"

    def test_normalize_empty_url(self):
        """Тест пустого URL"""
        assert normalize_url("") == ""
        assert normalize_url(None) is None


class TestEmailExtractor:
    """Тесты для основного класса EmailExtractor"""

    def test_init_with_config(self):
        """Тест инициализации с конфигурацией"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.yaml")
            with open(config_path, 'w', encoding="utf-8") as f:
                f.write("""
extraction:
  delay_between_requests: 1
  max_retries: 1
  timeout: 5
database:
  path: "test.db"
logging:
  level: "DEBUG"
""")

            extractor = EmailExtractor(config_path)
            assert extractor.config is not None
            assert extractor.db is not None

    def test_process_single_url_invalid(self):
        """Тест обработки невалидного URL"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.yaml")
            with open(config_path, 'w', encoding="utf-8") as f:
                f.write("""
extraction:
  delay_between_requests: 1
  max_retries: 1
  timeout: 5
database:
  path: "test.db"
logging:
  level: "ERROR"
""")

            extractor = EmailExtractor(config_path)
            emails = extractor.process_single_url("invalid-url")
            assert emails == []


if __name__ == "__main__":
    pytest.main([__file__])
