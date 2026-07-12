import json
import urllib.error

from backend.services import ai_summary_service


def test_generate_diff_summary_falls_back_without_key(monkeypatch):
    monkeypatch.setattr(ai_summary_service, "OPENAI_API_KEY", "")

    summary = ai_summary_service.generate_diff_summary(
        [{"type": "insert", "left": "", "right": "New paragraph"}],
        "Fallback summary.",
    )

    assert summary == "Fallback summary."


def test_extract_output_text_reads_responses_output():
    data = {
        "output": [
            {
                "content": [
                    {
                        "type": "output_text",
                        "text": "Clarified the project motivation.",
                    }
                ]
            }
        ]
    }

    assert ai_summary_service.extract_output_text(data) == "Clarified the project motivation."


def test_build_summary_prompt_includes_context_and_version_details():
    chunks = [
        {"type": "equal", "left": "The collaboration section currently says ", "right": ""},
        {"type": "replace", "left": "users edit separately", "right": "users edit together in real time"},
        {"type": "equal", "left": ". Changes are synchronized through OT.", "right": ""},
    ]

    prompt = ai_summary_service.build_summary_prompt(
        chunks,
        document_title="NotGoogleDocs proposal",
        from_note="Initial collaboration wording",
        to_note="Clarify real-time editing",
    )

    assert "Document title: NotGoogleDocs proposal" in prompt
    assert "Later version note: Clarify real-time editing" in prompt
    assert "Context before: The collaboration section currently says" in prompt
    assert "Added: users edit together in real time" in prompt
    assert "Context after: . Changes are synchronized through OT." in prompt


def test_long_diff_keeps_changes_from_across_the_document():
    chunks = []
    for index in range(30):
        marker = ""
        padding_length = 2000
        if index == 0:
            marker = "BEGIN_MARKER "
            padding_length = 3000
        elif index == 15:
            marker = "MIDDLE_MARKER "
            padding_length = 3000
        elif index == 29:
            marker = "END_MARKER "
            padding_length = 3000

        chunks.extend(
            [
                {"type": "equal", "left": f"Section {index}. ", "right": f"Section {index}. "},
                {
                    "type": "replace",
                    "left": f"old {index} " + ("x" * padding_length),
                    "right": marker + f"new {index} " + ("y" * padding_length),
                },
            ]
        )

    prompt = ai_summary_service.build_summary_prompt(chunks, "Long document")

    assert len(prompt) <= ai_summary_service.MAX_DIFF_CHARS
    assert prompt.endswith("</changes>")
    assert "BEGIN_MARKER" in prompt
    assert "MIDDLE_MARKER" in prompt
    assert "END_MARKER" in prompt
    assert "representative changes" in prompt


def test_request_openai_summary_posts_to_responses_api(monkeypatch):
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, _exc_type, _exc, _traceback):
            return False

        def read(self):
            return json.dumps({"output_text": "Expanded the implementation plan."}).encode("utf-8")

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["headers"] = request.headers
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(ai_summary_service, "OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(ai_summary_service, "OPENAI_MODEL", "test-model")
    monkeypatch.setattr(ai_summary_service.urllib.request, "urlopen", fake_urlopen)

    summary = ai_summary_service.request_openai_summary("Added a testing section.")

    assert summary == "Expanded the implementation plan."
    assert captured["payload"]["model"] == "test-model"
    assert captured["payload"]["store"] is False
    assert captured["timeout"] == 8


def test_describe_http_error_includes_api_message():
    error_body = json.dumps({"error": {"message": "You exceeded your current quota."}})
    error = urllib.error.HTTPError(
        url="https://api.openai.com/v1/responses",
        code=429,
        msg="Too Many Requests",
        hdrs={},
        fp=FakeErrorBody(error_body),
    )

    message = ai_summary_service.describe_http_error(error)

    assert message == "HTTP 429: Too Many Requests - You exceeded your current quota."


class FakeErrorBody:
    def __init__(self, body):
        self.body = body

    def read(self):
        return self.body.encode("utf-8")

    def close(self):
        pass
