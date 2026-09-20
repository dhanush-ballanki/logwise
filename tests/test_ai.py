import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from logwise.ai import (
    _extract_sse_content,
    _post_chat_completions,
    _split_reason_fixes,
    ai_analyze_err,
)

from .helpers import clear_managed_env


def sse_body(chunks):
    return "".join(f"data: {json.dumps(c)}\n\n" for c in chunks) + "data: [DONE]\n\n"


def chunk(text):
    return {"choices": [{"index": 0, "delta": {"content": text}, "finish_reason": None}]}


class StubHandler(BaseHTTPRequestHandler):
    mode = "json"  # json | sse | error | garbage
    seen = []

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        StubHandler.seen.append(json.loads(self.rfile.read(length) or b"{}"))
        if StubHandler.mode == "error":
            self.send_response(403)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error": "bad key"}')
            return
        if StubHandler.mode == "garbage":
            payload, ctype = b"<html>nope</html>", "text/html"
        elif StubHandler.mode == "sse":
            payload = sse_body([chunk("He"), chunk("llo")]).encode()
            ctype = "text/event-stream"
        else:
            payload = json.dumps(
                {"choices": [{"message": {"content": "Reason: X\nFixes:\n1. Y"}}]}
            ).encode()
            ctype = "application/json"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass


class StubServer:
    def __enter__(self):
        self.server = HTTPServer(("127.0.0.1", 0), StubHandler)
        StubHandler.seen = []
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address[:2]
        return f"http://{host}:{port}"

    def __exit__(self, *args):
        self.server.shutdown()
        self.thread.join()


class TestSplitReasonFixes(unittest.TestCase):
    def test_strict_format(self):
        r, f = _split_reason_fixes("Reason: bad cmd\nFixes:\n1. Fix it")
        self.assertEqual((r, f), ("bad cmd", "1. Fix it"))

    def test_bold_headers(self):
        r, f = _split_reason_fixes("**Reason:** gone.\n\n**Fix Steps:**\n1. Check.\n2. Make.")
        self.assertEqual(r, "gone.")
        self.assertIn("1. Check.", f)
        self.assertNotIn("Fix Steps", f)

    def test_no_markers(self):
        r, f = _split_reason_fixes("Just some text.")
        self.assertEqual((r, f), ("Just some text.", "No fixes suggested."))


class TestExtractSSE(unittest.TestCase):
    def test_assembles_chunks(self):
        body = sse_body(
            [
                chunk("a"),
                {
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"reasoning_content": "skip-me"},
                            "finish_reason": None,
                        }
                    ]
                },
                chunk("b"),
            ]
        )
        self.assertEqual(_extract_sse_content(body), "ab")

    def test_empty_stream(self):
        self.assertEqual(_extract_sse_content("data: [DONE]\n\n"), "")


class TestPostChatCompletions(unittest.TestCase):
    def setUp(self):
        clear_managed_env(self)

    def test_json_response(self):
        with StubServer() as base:
            StubHandler.mode = "json"
            text = _post_chat_completions(base, "k", "m", "hi")
        self.assertIn("Reason: X", text)
        sent = StubHandler.seen[-1]
        self.assertEqual(sent["model"], "m")
        self.assertFalse(sent["stream"])

    def test_auth_header_optional(self):
        with StubServer() as base:
            StubHandler.mode = "json"
            _post_chat_completions(base, None, "m", "hi")
        self.assertEqual(len(StubHandler.seen), 1)

    def test_sse_response(self):
        with StubServer() as base:
            StubHandler.mode = "sse"
            self.assertEqual(_post_chat_completions(base, None, "m", "hi"), "Hello")

    def test_http_error_surfaces_status(self):
        with StubServer() as base:
            StubHandler.mode = "error"
            with self.assertRaises(RuntimeError) as ctx:
                _post_chat_completions(base, "k", "m", "hi")
        self.assertIn("403", str(ctx.exception))

    def test_garbage_body_reports_preview(self):
        with StubServer() as base:
            StubHandler.mode = "garbage"
            with self.assertRaises(RuntimeError) as ctx:
                _post_chat_completions(base, None, "m", "hi")
        self.assertIn("Non-JSON", str(ctx.exception))

    def test_unreachable_host(self):
        with self.assertRaises(RuntimeError) as ctx:
            _post_chat_completions("http://127.0.0.1:1", None, "m", "hi")
        self.assertIn("Cannot reach", str(ctx.exception))


class TestAiAnalyzeErr(unittest.TestCase):
    def setUp(self):
        clear_managed_env(self)

    def test_missing_key_error(self):
        result = ai_analyze_err("c", "e", 1, provider="openai")
        self.assertIn("OPENAI_API_KEY", result["error"])

    def test_unknown_provider(self):
        self.assertIn("Unknown provider", ai_analyze_err("c", "e", 1, provider="x")["error"])

    def test_success_via_stub(self):
        import os

        with StubServer() as base:
            StubHandler.mode = "json"
            os.environ["LOGWISE_BASE_URL"] = base
            os.environ["LOGWISE_API_KEY"] = "k"
            result = ai_analyze_err("c", "e", 1, provider="openai", model="stub-model")
        self.assertEqual(result["provider"], "openai")
        self.assertEqual(result["model"], "stub-model")
        self.assertIn("reason", result)
        self.assertIn("fixes", result)


if __name__ == "__main__":
    unittest.main()
