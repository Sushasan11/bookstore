"""Developer tool: send sample emails through a local SMTP trap.

Sends one order confirmation and one restock alert to visually verify
that CID-embedded logos, Open Library cover images, and template
rendering all work end-to-end.

Usage:
    python backend/scripts/test_email.py
    python backend/scripts/test_email.py --smtp-port 1025 --to dev@test.com

Prerequisites:
    Make sure a local SMTP trap is running, e.g.:
        docker run -d -p 1025:1025 -p 8025:8025 mailhog/mailhog
    Then open http://localhost:8025 to inspect incoming emails.
"""

import argparse
import re
import smtplib
import sys
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup — allow running from repo root or from backend/
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _SCRIPT_DIR.parent
sys.path.insert(0, str(_BACKEND_DIR))

TEMPLATE_DIR = _BACKEND_DIR / "app" / "email" / "templates"
STATIC_DIR = _BACKEND_DIR / "app" / "email" / "static"

# ---------------------------------------------------------------------------
# Minimal Jinja2 rendering (mirrors EmailService internals, no FastAPI needed)
# ---------------------------------------------------------------------------
try:
    from jinja2 import Environment, FileSystemLoader
except ImportError as exc:
    sys.exit(f"jinja2 not installed: {exc}")


def _make_jinja_env() -> Environment:
    return Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=True)


def _render_html(template_name: str, context: dict) -> str:
    env = _make_jinja_env()
    return env.get_template(template_name).render(**context)


def _strip_html(html: str) -> str:
    """Auto-generate plain-text fallback by stripping HTML tags."""
    text = re.sub(
        r'</(?:h[1-6]|p|div|li|tr|td|th|section|article|header|footer|main|nav|aside|blockquote|pre)>',
        ' ', html, flags=re.IGNORECASE,
    )
    text = re.sub(r'<[^>]+>', '', text)
    return re.sub(r'\s+', ' ', text).strip()


# ---------------------------------------------------------------------------
# MIME builder — multipart/related wrapping multipart/alternative + CID logo
# ---------------------------------------------------------------------------

def _build_mime(
    to: str,
    from_addr: str,
    subject: str,
    html_body: str,
) -> MIMEMultipart:
    plain_text = _strip_html(html_body)

    msg = MIMEMultipart("related")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to

    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(plain_text, "plain", "utf-8"))
    alt.attach(MIMEText(html_body, "html", "utf-8"))
    msg.attach(alt)

    logo_path = STATIC_DIR / "logo-white.png"
    if logo_path.exists():
        with open(logo_path, "rb") as f:
            logo = MIMEImage(f.read(), _subtype="png")
        logo.add_header("Content-ID", "<bookstore-logo>")
        logo.add_header("Content-Disposition", "inline", filename="logo.png")
        msg.attach(logo)
    else:
        print(f"  [warn] Logo not found at {logo_path} — CID embed skipped")

    return msg


# ---------------------------------------------------------------------------
# SMTP send — no auth, no TLS (SMTP traps don't need it)
# ---------------------------------------------------------------------------

def _send(msg: MIMEMultipart, smtp_host: str, smtp_port: int, to: str) -> None:
    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.send_message(msg)
    print(f"  Sent to {to}")


# ---------------------------------------------------------------------------
# Sample email definitions
# ---------------------------------------------------------------------------

def send_order_confirmation(smtp_host: str, smtp_port: int, to: str) -> None:
    print("[1/2] Sending order confirmation email...")
    context = {
        "customer_name": "Jane",
        "order_id": 42,
        "items": [
            {
                "title": "Effective Python",
                "author": "Brett Slatkin",
                "quantity": 1,
                "unit_price": "39.99",
                "cover_image_url": None,
                "isbn": "9780134853987",
            },
            {
                "title": "Clean Code",
                "author": "Robert C. Martin",
                "quantity": 2,
                "unit_price": "29.99",
                "cover_image_url": None,
                "isbn": "9780132350884",
            },
        ],
        "total_price": "99.97",
    }
    html = _render_html("order_confirmation.html", context)
    msg = _build_mime(
        to=to,
        from_addr="BookStore <noreply@bookstore.com>",
        subject="Order Confirmed — BookStore #42",
        html_body=html,
    )
    _send(msg, smtp_host, smtp_port, to)
    print("  Sent order confirmation to", to)


def send_restock_alert(smtp_host: str, smtp_port: int, to: str) -> None:
    print("[2/2] Sending restock alert email...")
    context = {
        "book_title": "Designing Data-Intensive Applications",
        "book_id": 7,
        "isbn": "9781449373320",
        "cover_image_url": None,  # Forces Open Library fallback
        "store_url": "http://localhost:3000",
    }
    html = _render_html("restock_alert.html", context)
    msg = _build_mime(
        to=to,
        from_addr="BookStore <noreply@bookstore.com>",
        subject="'Designing Data-Intensive Applications' is back in stock",
        html_body=html,
    )
    _send(msg, smtp_host, smtp_port, to)
    print("  Sent restock alert to", to)


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Send sample emails to a local SMTP trap for visual verification.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Prerequisites:\n"
            "  Make sure a local SMTP trap is running, e.g.:\n"
            "    docker run -d -p 1025:1025 -p 8025:8025 mailhog/mailhog\n"
            "  Then open http://localhost:8025 to inspect incoming emails."
        ),
    )
    parser.add_argument("--smtp-host", default="localhost", help="SMTP server host (default: localhost)")
    parser.add_argument("--smtp-port", type=int, default=1025, help="SMTP server port (default: 1025)")
    parser.add_argument("--to", default="test@example.com", help="Recipient email address (default: test@example.com)")
    args = parser.parse_args()

    print()
    print("BookStore Email Test Script")
    print("=" * 40)
    print(f"  SMTP trap:  {args.smtp_host}:{args.smtp_port}")
    print(f"  Recipient:  {args.to}")
    print(f"  Templates:  {TEMPLATE_DIR}")
    print()
    print("Make sure a local SMTP trap is running:")
    print("  docker run -d -p 1025:1025 -p 8025:8025 mailhog/mailhog")
    print("Then open http://localhost:8025 to view emails.")
    print()

    try:
        send_order_confirmation(args.smtp_host, args.smtp_port, args.to)
        send_restock_alert(args.smtp_host, args.smtp_port, args.to)
    except ConnectionRefusedError:
        print()
        print("[error] Connection refused — is your SMTP trap running?")
        print(f"  Could not connect to {args.smtp_host}:{args.smtp_port}")
        print("  Start one with: docker run -d -p 1025:1025 -p 8025:8025 mailhog/mailhog")
        sys.exit(1)
    except Exception as exc:
        print(f"\n[error] Failed to send email: {exc}")
        sys.exit(1)

    print()
    print("Done. Open http://localhost:8025 to inspect both emails.")


if __name__ == "__main__":
    main()
