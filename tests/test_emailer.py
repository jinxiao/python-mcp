from python_mcp import EmailClient as PublicEmailClient
from python_mcp.emailer import EmailClient


def test_build_message_contains_headers_and_body() -> None:
    client = EmailClient()

    message = client.build_message(
        sender="from@example.com",
        recipients=["to@example.com"],
        subject="Hello",
        body="Plain body",
    )

    assert "From: from@example.com" in message
    assert "To: to@example.com" in message
    assert "Subject: Hello" in message
    assert "Plain body" in message


def test_public_sdk_import_supports_application_workflow() -> None:
    client = PublicEmailClient(default_sender="from@example.com")

    result = client.send_email(
        recipients=["to@example.com"],
        subject="Hello",
        body="Plain body",
    )

    assert result.dry_run is True
    assert result.sender == "from@example.com"
    assert result.metadata == {"smtp_host": None, "sent": False}


def test_send_email_defaults_to_dry_run() -> None:
    client = EmailClient(default_sender="from@example.com")

    result = client.send_email(
        recipients=["to@example.com"],
        subject="Hello",
        body="Plain body",
    )

    assert result.dry_run is True
    assert result.metadata["sent"] is False
