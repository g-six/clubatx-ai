"""Separate the exact Veo report URL from its observed raw MP4 Match Video target."""
import argparse
import json
import re
from urllib.parse import urlsplit


def _https_url(value):
    if not isinstance(value, str) or not value or any(c.isspace() for c in value):
        raise ValueError("A URL must be a nonempty string without whitespace")
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as error:
        raise ValueError("Invalid HTTPS URL") from error
    if parsed.scheme != "https" or not parsed.hostname or parsed.username is not None or parsed.password is not None:
        raise ValueError("A verified HTTPS URL without embedded credentials is required")
    return parsed


def match_video_link(report_url, observed_mp4_url):
    report = _https_url(report_url)
    if report.hostname != "app.veo.co":
        raise ValueError("The source report URL must use app.veo.co")
    identity = re.match(r"^/matches/([^/]+)(?:/|$)", report.path)
    if not identity:
        raise ValueError("The source report must identify a Veo match")
    media = _https_url(observed_mp4_url)
    if media.hostname == "app.veo.co" or not media.path.lower().endswith(".mp4"):
        raise ValueError("Match Video must use the observed raw MP4, not a Veo page, HLS playlist, or blob URL")
    raw = observed_mp4_url.split("#", 1)[0]
    return {"fixture_video_url": raw, "source": {"provider": "veo", "match_id": identity.group(1), "report_url": report_url, "raw_video_url": raw}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report_url")
    parser.add_argument("observed_mp4_url")
    args = parser.parse_args()
    print(json.dumps(match_video_link(args.report_url, args.observed_mp4_url), indent=2))
