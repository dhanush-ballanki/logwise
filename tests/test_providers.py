import os
import unittest

from logwise.providers import (
    PROVIDERS,
    key_hint,
    resolve_api_key,
    resolve_base_url,
    resolve_model,
    resolve_provider,
)

from .helpers import clear_managed_env


class TestProviders(unittest.TestCase):
    def setUp(self):
        clear_managed_env(self)

    def test_default_is_gemini(self):
        name, cfg = resolve_provider(None)
        self.assertEqual(name, "gemini")
        self.assertEqual(cfg, PROVIDERS["gemini"])

    def test_flag_case_insensitive(self):
        name, _ = resolve_provider("OpenAI")
        self.assertEqual(name, "openai")

    def test_env_fallback(self):
        os.environ["LOGWISE_PROVIDER"] = "groq"
        self.assertEqual(resolve_provider(None)[0], "groq")

    def test_unknown_raises_with_choices(self):
        with self.assertRaises(ValueError) as ctx:
            resolve_provider("bogus")
        self.assertIn("ollama", str(ctx.exception))

    def test_model_precedence(self):
        cfg = PROVIDERS["openai"]
        self.assertEqual(resolve_model(cfg, "flag-model"), "flag-model")
        os.environ["LOGWISE_MODEL"] = "env-model"
        self.assertEqual(resolve_model(cfg, None), "env-model")
        del os.environ["LOGWISE_MODEL"]
        self.assertEqual(resolve_model(cfg, None), "gpt-4o-mini")

    def test_base_url_override(self):
        cfg = PROVIDERS["openai"]
        os.environ["LOGWISE_BASE_URL"] = "http://x:1/v1/"
        self.assertEqual(resolve_base_url(cfg), "http://x:1/v1")

    def test_api_key_generic_beats_specific(self):
        cfg = PROVIDERS["openai"]
        os.environ["OPENAI_API_KEY"] = "specific"
        os.environ["LOGWISE_API_KEY"] = "generic"
        self.assertEqual(resolve_api_key("openai", cfg), "generic")

    def test_api_key_missing_returns_none(self):
        self.assertIsNone(resolve_api_key("openai", PROVIDERS["openai"]))

    def test_ollama_keyless(self):
        cfg = PROVIDERS["ollama"]
        self.assertIsNone(cfg["key_env"])
        self.assertIsNone(resolve_api_key("ollama", cfg))
        self.assertIn("no API key", key_hint("ollama", cfg))

    def test_key_hint_names_env(self):
        self.assertIn("GEMINI_API_KEY", key_hint("gemini", PROVIDERS["gemini"]))


if __name__ == "__main__":
    unittest.main()
