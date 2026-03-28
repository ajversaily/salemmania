pip install Flask
import re
import os
import json
import time
import hmac
import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from typing import Optional
from enum import Enum
from flask import Flask, request, jsonify, abort


# ═══════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════

class Config:
    SECRET_KEY           = os.environ.get("SM_SECRET_KEY",       secrets.token_hex(32))
    FORMSPREE_SECRET     = os.environ.get("SM_FORMSPREE_SECRET",  "")
    ADMIN_TOKEN          = os.environ.get("SM_ADMIN_TOKEN",       secrets.token_hex(16))
    RATE_LIMIT_HOUR      = int(os.environ.get("SM_RATE_HOUR",     "3"))
    RATE_LIMIT_DAY       = int(os.environ.get("SM_RATE_DAY",      "5"))
    ALLOWED_ORIGINS      = ["https://salemmania.org", "https://www.salemmania.org",
                            "http://localhost", "http://127.0.0.1"]
    LOG_FILE             = "salem_mania_security.log"
    ANALYTICS_FILE       = "salem_mania_analytics.json"


# ═══════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(Config.LOG_FILE),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("salem_mania")


# ═══════════════════════════════════════════════════════════════
# SECURITY EVENTS
# ═══════════════════════════════════════════════════════════════

class EventType(Enum):
    PITCH_VALID        = "pitch_valid"
    PITCH_INVALID      = "pitch_invalid"
    PITCH_DUPLICATE    = "pitch_duplicate"
    PITCH_RATE_LIMITED = "pitch_rate_limited"
    HONEYPOT_TRIGGERED = "honeypot_triggered"
    CSRF_FAIL          = "csrf_fail"
    WEBHOOK_OK         = "webhook_ok"
    WEBHOOK_FAIL       = "webhook_fail"
    SUBSCRIBE_OK       = "subscribe_ok"
    SUBSCRIBE_DUP      = "subscribe_duplicate"
    PAGEVIEW           = "pageview"
    ADMIN_ACCESS       = "admin_access"
    BLOCKED_IP         = "blocked_ip"


@dataclass
class SecurityEvent:
    event_type: str
    timestamp:  str = field(default_factory=lambda: datetime.now().isoformat())
    ip:         str = ""
    detail:     str = ""
    meta:       dict = field(default_factory=dict)


class SecurityLogger:
    def __init__(self):
        self._events: list[SecurityEvent] = []

    def record(self, event_type: EventType, ip: str = "", detail: str = "", **meta):
        ev = SecurityEvent(
            event_type=event_type.value,
            ip=ip,
            detail=detail,
            meta=meta
        )
        self._events.append(ev)
        log.info(f"[{ev.event_type}] ip={ip} {detail} {json.dumps(meta) if meta else ''}")
        return ev

    def events_by_type(self, event_type: EventType) -> list[SecurityEvent]:
        return [e for e in self._events if e.event_type == event_type.value]

    def recent(self, hours: int = 24) -> list[SecurityEvent]:
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        return [e for e in self._events if e.timestamp >= cutoff]

    def threat_summary(self) -> dict:
        recent = self.recent(24)
        return {
            "honeypot_hits":      sum(1 for e in recent if e.event_type == EventType.HONEYPOT_TRIGGERED.value),
            "rate_limited":       sum(1 for e in recent if e.event_type == EventType.PITCH_RATE_LIMITED.value),
            "csrf_failures":      sum(1 for e in recent if e.event_type == EventType.CSRF_FAIL.value),
            "invalid_submissions":sum(1 for e in recent if e.event_type == EventType.PITCH_INVALID.value),
            "webhook_failures":   sum(1 for e in recent if e.event_type == EventType.WEBHOOK_FAIL.value),
            "blocked_ips":        sum(1 for e in recent if e.event_type == EventType.BLOCKED_IP.value),
        }


security_log = SecurityLogger()



    THRESHOLD = 5           # events within window before block
    WINDOW_SECONDS = 3600   # 1 hour window
    BLOCK_DURATION = 86400  # block for 24 hours

    def __init__(self):
        self._strikes:  dict[str, list[float]] = defaultdict(list)
        self._blocked:  dict[str, float] = {}       # ip → block_expiry

    def strike(self, ip: str) -> bool:
        """Add a strike. Returns True if IP is now blocked."""
        now = time.time()
        cutoff = now - self.WINDOW_SECONDS
        self._strikes[ip] = [t for t in self._strikes[ip] if t > cutoff]
        self._strikes[ip].append(now)

        if len(self._strikes[ip]) >= self.THRESHOLD:
            self._blocked[ip] = now + self.BLOCK_DURATION
            security_log.record(EventType.BLOCKED_IP, ip=ip,
                               detail=f"Auto-blocked after {len(self._strikes[ip])} strikes")
            return True
        return False

    def is_blocked(self, ip: str) -> bool:
        if ip in self._blocked:
            if time.time() < self._blocked[ip]:
                return True
            else:
                del self._blocked[ip]  # expired
        return False

    def unblock(self, ip: str) -> None:
        self._blocked.pop(ip, None)
        self._strikes.pop(ip, None)

    def status(self) -> dict:
        now = time.time()
        active = {ip: datetime.fromtimestamp(exp).isoformat()
                  for ip, exp in self._blocked.items() if exp > now}
        return {"blocked_ips": active, "count": len(active)}


blocklist = IPBlocklist()


# ═══════════════════════════════════════════════════════════════
# CSRF PROTECTION
# ═══════════════════════════════════════════════════════════════

class CSRFProtection:
    """
    Double-submit cookie pattern for CSRF.
    Tokens expire after 1 hour.
    """
    TOKEN_TTL = 3600

    def __init__(self):
        self._tokens: dict[str, float] = {}

    def generate(self) -> str:
        token = secrets.token_urlsafe(32)
        self._tokens[token] = time.time() + self.TOKEN_TTL
        return token

    def verify(self, token: str) -> bool:
        if not token:
            return False
        expiry = self._tokens.get(token)
        if expiry is None:
            return False
        if time.time() > expiry:
            del self._tokens[token]
            return False
        # One-time use
        del self._tokens[token]
        return True

    def cleanup(self):
        now = time.time()
        self._tokens = {t: exp for t, exp in self._tokens.items() if exp > now}


csrf = CSRFProtection()


# ═══════════════════════════════════════════════════════════════
# RATE LIMITER
# ═══════════════════════════════════════════════════════════════

class RateLimiter:
    def __init__(self, max_hour=3, max_day=5):
        self.max_hour = max_hour
        self.max_day  = max_day
        self._log: dict[str, list[float]] = defaultdict(list)

    def check(self, identifier: str) -> dict:
        now   = time.time()
        cutoff_hour = now - 3600
        cutoff_day  = now - 86400

        ts = self._log[identifier]
        self._log[identifier] = [t for t in ts if t > cutoff_day]
        ts = self._log[identifier]

        in_hour = sum(1 for t in ts if t > cutoff_hour)
        in_day  = len(ts)

        if in_hour >= self.max_hour:
            return {"allowed": False,
                    "reason": f"Too many submissions — max {self.max_hour}/hour. Try again later."}
        if in_day >= self.max_day:
            return {"allowed": False,
                    "reason": f"Daily submission limit reached ({self.max_day}/day)."}

        self._log[identifier].append(now)
        return {"allowed": True, "reason": ""}

    def remaining(self, identifier: str) -> dict:
        now = time.time()
        ts  = self._log.get(identifier, [])
        return {
            "hour_remaining": max(0, self.max_hour - sum(1 for t in ts if t > now-3600)),
            "day_remaining":  max(0, self.max_day  - sum(1 for t in ts if t > now-86400)),
        }


rate_limiter = RateLimiter(
    max_hour=Config.RATE_LIMIT_HOUR,
    max_day=Config.RATE_LIMIT_DAY
)


# ═══════════════════════════════════════════════════════════════
# HONEYPOT DETECTION
# ═══════════════════════════════════════════════════════════════

class HoneypotChecker:
    """
    The form includes a hidden field called 'website'.
    Legitimate users don't see it and don't fill it.
    Bots fill every field automatically.
    """
    HONEYPOT_FIELD = "website"

    def triggered(self, form_data: dict) -> bool:
        return bool(form_data.get(self.HONEYPOT_FIELD, "").strip())


honeypot = HoneypotChecker()


# ═══════════════════════════════════════════════════════════════
# SUBMISSION VALIDATOR
# ═══════════════════════════════════════════════════════════════

class SubmissionValidator:
    VALID_SECTIONS    = {"Film", "Music", "Culture", "Literature", "Opinion", "Poetry", "Other"}
    MIN_PITCH_LEN     = 80
    MAX_PITCH_LEN     = 2000
    MIN_TITLE_LEN     = 4
    MAX_TITLE_LEN     = 160
    EMAIL_PATTERN     = re.compile(r'^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}$')
    INJECTION_PATTERN = re.compile(r'[<>{};]')
    _seen_fingerprints: set = set()

    def validate(self, data: dict) -> dict:
        errors = []
        clean  = {}

        clean["name"]       = self._check_name(data.get("name", ""), errors)
        clean["email"]      = self._check_email(data.get("email", ""), errors)
        clean["section"]    = self._check_section(data.get("section", ""), errors)
        clean["title"]      = self._check_title(data.get("title", ""), errors)
        clean["pitch"]      = self._check_pitch(data.get("pitch", ""), errors)
        clean["influences"] = self._check_influences(data.get("influences", ""), errors)
        clean["portfolio"]  = self._clean_url(data.get("portfolio", ""))

        fp = self._fingerprint(clean.get("email",""), clean.get("title",""))
        if fp in self._seen_fingerprints:
            errors.append("Duplicate submission detected.")
        else:
            self._seen_fingerprints.add(fp)

        clean["submitted_at"] = datetime.now().isoformat()
        clean["fingerprint"]  = fp

        return {"valid": len(errors) == 0, "errors": errors,
                "clean": clean if not errors else {}}

    # ── Field checks ──────────────────────────────────────────

    def _check_name(self, v, errs):
        v = v.strip()
        if not v:                              errs.append("Name is required.")
        elif len(v) < 2:                       errs.append("Name is too short.")
        elif len(v) > 120:                     errs.append("Name is too long.")
        elif self.INJECTION_PATTERN.search(v): errs.append("Name contains invalid characters.")
        return v

    def _check_email(self, v, errs):
        v = v.strip().lower()
        if not v:                              errs.append("Email is required.")
        elif not self.EMAIL_PATTERN.match(v):  errs.append("Invalid email address.")
        elif len(v) > 254:                     errs.append("Email address is too long.")
        return v

    def _check_section(self, v, errs):
        v = v.strip().capitalize()
        if v not in self.VALID_SECTIONS:
            errs.append(f"Section must be one of: {', '.join(sorted(self.VALID_SECTIONS))}")
        return v

    def _check_title(self, v, errs):
        v = v.strip()
        if len(v) < self.MIN_TITLE_LEN: errs.append(f"Title must be at least {self.MIN_TITLE_LEN} characters.")
        if len(v) > self.MAX_TITLE_LEN: errs.append(f"Title must be under {self.MAX_TITLE_LEN} characters.")
        return v

    def _check_pitch(self, v, errs):
        v = v.strip()
        if len(v) < self.MIN_PITCH_LEN:
            errs.append(f"Pitch too short — minimum {self.MIN_PITCH_LEN} characters. Make the case for your piece.")
        if len(v) > self.MAX_PITCH_LEN:
            errs.append(f"Pitch exceeds {self.MAX_PITCH_LEN} character limit.")
        return v

    def _check_influences(self, v, errs):
        v = v.strip()
        if len(v) < 8: errs.append("Please name at least one writer or work that influences you.")
        return v

    def _clean_url(self, v):
        v = v.strip()
        if v and not v.startswith(("http://", "https://")):
            v = "https://" + v
        return v[:2000]

    @staticmethod
    def _fingerprint(email, title):
        raw = f"{email.lower()}:{title.lower().replace(' ', '')}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


validator = SubmissionValidator()


# ═══════════════════════════════════════════════════════════════
# ANALYTICS ENGINE
# ═══════════════════════════════════════════════════════════════

@dataclass
class PageView:
    page:      str
    referrer:  str
    source:    str   # utm_source
    medium:    str   # utm_medium
    campaign:  str   # utm_campaign
    ip:        str
    country:   str   = ""
    timestamp: str   = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ConversionEvent:
    kind:      str   # "pitch_submitted", "subscribed", "pitch_valid", "pitch_published"
    source:    str
    medium:    str
    campaign:  str
    timestamp: str   = field(default_factory=lambda: datetime.now().isoformat())


class AnalyticsEngine:
    """
    Privacy-first analytics — no external service, no personal data stored.
    Tracks pageviews, traffic sources, UTM campaigns, and conversions.
    """

    def __init__(self):
        self._pageviews:    list[PageView]        = []
        self._conversions:  list[ConversionEvent] = []
        self._subscribers:  list[dict]            = []
        self._submissions:  list[dict]            = []

    # ── Ingest ────────────────────────────────────────────────

    def track_pageview(self, page: str, ip: str = "", referrer: str = "", **utm) -> None:
        pv = PageView(
            page     = page,
            referrer = self._clean_referrer(referrer),
            source   = utm.get("utm_source",   self._infer_source(referrer)),
            medium   = utm.get("utm_medium",   ""),
            campaign = utm.get("utm_campaign", ""),
            ip       = self._hash_ip(ip),
        )
        self._pageviews.append(pv)

    def track_conversion(self, kind: str, **utm) -> None:
        self._conversions.append(ConversionEvent(
            kind     = kind,
            source   = utm.get("utm_source",   "direct"),
            medium   = utm.get("utm_medium",   ""),
            campaign = utm.get("utm_campaign", ""),
        ))

    def track_submission(self, section: str, source: str = "direct") -> None:
        self._submissions.append({
            "section":    section,
            "source":     source,
            "timestamp":  datetime.now().isoformat(),
        })

    def track_subscriber(self, email: str, source: str = "website") -> dict:
        email = email.strip().lower()
        if any(s["email"] == email for s in self._subscribers):
            return {"success": False, "reason": "Already subscribed."}
        self._subscribers.append({
            "email":     email,
            "source":    source,
            "joined":    datetime.now().isoformat(),
            "active":    True,
        })
        self.track_conversion("subscribed", utm_source=source)
        return {"success": True, "total": len(self._subscribers)}

    # ── Summary stats ─────────────────────────────────────────

    def summary(self) -> dict:
        now    = datetime.now()
        day    = (now - timedelta(days=1)).isoformat()
        week   = (now - timedelta(days=7)).isoformat()
        month  = (now - timedelta(days=30)).isoformat()

        total_pv   = len(self._pageviews)
        pv_day     = sum(1 for p in self._pageviews if p.timestamp >= day)
        pv_week    = sum(1 for p in self._pageviews if p.timestamp >= week)
        pv_month   = sum(1 for p in self._pageviews if p.timestamp >= month)

        subscribers_active = sum(1 for s in self._subscribers if s["active"])
        submissions_total  = len(self._submissions)

        top_pages   = self._top(self._pageviews, key=lambda p: p.page)
        top_sources = self._top(self._pageviews, key=lambda p: p.source)
        top_campaigns = self._top(
            [p for p in self._pageviews if p.campaign],
            key=lambda p: p.campaign
        )

        conversion_rate = (
            round(sum(1 for c in self._conversions if c.kind == "pitch_submitted") /
                  max(total_pv, 1) * 100, 2)
        )

        sections = defaultdict(int)
        for s in self._submissions:
            sections[s["section"]] += 1

        sources_by_subs = defaultdict(int)
        for s in self._subscribers:
            if s["active"]:
                sources_by_subs[s["source"]] += 1

        conversions_by_source = defaultdict(int)
        for c in self._conversions:
            conversions_by_source[c.source] += 1

        pv_by_day = self._pageviews_by_day(30)

        return {
            "pageviews": {
                "total":       total_pv,
                "last_24h":    pv_day,
                "last_7d":     pv_week,
                "last_30d":    pv_month,
                "by_day":      pv_by_day,
            },
            "top_pages":             top_pages,
            "traffic_sources":       top_sources,
            "campaigns":             top_campaigns,
            "subscribers": {
                "total":          len(self._subscribers),
                "active":         subscribers_active,
                "by_source":      dict(sources_by_subs),
            },
            "submissions": {
                "total":          submissions_total,
                "by_section":     dict(sections),
            },
            "conversions": {
                "total":          len(self._conversions),
                "by_kind":        self._count_field(self._conversions, lambda c: c.kind),
                "by_source":      dict(conversions_by_source),
                "conversion_rate_pct": conversion_rate,
            },
            "security": security_log.threat_summary(),
            "generated_at": now.isoformat(),
        }

    # ── Helpers ───────────────────────────────────────────────

    @staticmethod
    def _top(items, key, n=5):
        counts: dict = defaultdict(int)
        for item in items:
            counts[key(item)] += 1
        return sorted(
            [{"label": k, "count": v} for k, v in counts.items()],
            key=lambda x: x["count"], reverse=True
        )[:n]

    @staticmethod
    def _count_field(items, key):
        counts: dict = defaultdict(int)
        for item in items:
            counts[key(item)] += 1
        return dict(counts)

    def _pageviews_by_day(self, days: int) -> list:
        result = []
        now = datetime.now()
        for i in range(days - 1, -1, -1):
            d = (now - timedelta(days=i)).strftime("%Y-%m-%d")
            count = sum(1 for p in self._pageviews if p.timestamp.startswith(d))
            result.append({"date": d, "views": count})
        return result

    @staticmethod
    def _clean_referrer(ref: str) -> str:
        if not ref: return "direct"
        ref = ref.lower()
        if "instagram" in ref: return "instagram"
        if "reddit"    in ref: return "reddit"
        if "google"    in ref: return "google"
        if "github"    in ref: return "github"
        if "twitter"   in ref or "t.co" in ref: return "twitter"
        return ref[:100]

    @staticmethod
    def _infer_source(ref: str) -> str:
        if not ref: return "direct"
        if "instagram" in ref: return "instagram"
        if "reddit"    in ref: return "reddit"
        if "google"    in ref: return "google"
        if "github"    in ref: return "github"
        return "referral"

    @staticmethod
    def _hash_ip(ip: str) -> str:
        """Store hashed IPs only — privacy first."""
        if not ip: return ""
        return hashlib.sha256(ip.encode()).hexdigest()[:12]

    def export_json(self, path: str = Config.ANALYTICS_FILE) -> None:
        with open(path, "w") as f:
            json.dump(self.summary(), f, indent=2)
        log.info(f"Analytics exported to {path}")


analytics = AnalyticsEngine()


# ═══════════════════════════════════════════════════════════════
# WEBHOOK VERIFIER
# ═══════════════════════════════════════════════════════════════

class WebhookVerifier:
    def __init__(self, secret: str = Config.FORMSPREE_SECRET):
        self.secret = secret

    def verify(self, payload: bytes, signature: str) -> bool:
        if not self.secret:
            log.warning("FORMSPREE_SECRET not set — skipping webhook verification")
            return True   # permissive if no secret set
        expected = hmac.new(self.secret.encode(), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature or "")


webhook_verifier = WebhookVerifier()


# ═══════════════════════════════════════════════════════════════
# FLASK APP
# ═══════════════════════════════════════════════════════════════

app = Flask(__name__)
app.secret_key = Config.SECRET_KEY


def get_ip() -> str:
    return request.headers.get("X-Forwarded-For", request.remote_addr or "").split(",")[0].strip()


def check_origin() -> bool:
    origin = request.headers.get("Origin", "")
    return not origin or origin in Config.ALLOWED_ORIGINS


def require_admin():
    token = request.headers.get("X-Admin-Token") or request.args.get("token")
    if token != Config.ADMIN_TOKEN:
        abort(403)


# ── CORS headers ──────────────────────────────────────────────
@app.after_request
def add_cors(response):
    origin = request.headers.get("Origin", "")
    if origin in Config.ALLOWED_ORIGINS:
        response.headers["Access-Control-Allow-Origin"]  = origin
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-CSRF-Token, X-Admin-Token"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"]        = "DENY"
    response.headers["Referrer-Policy"]        = "strict-origin-when-cross-origin"
    return response


@app.before_request
def security_checks():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    ip = get_ip()
    if blocklist.is_blocked(ip):
        security_log.record(EventType.BLOCKED_IP, ip=ip, detail="Request from blocked IP rejected")
        abort(429)
    if not check_origin():
        abort(403)


# ══════════════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════════════

# ── CSRF token ────────────────────────────────────────────────
@app.route("/api/csrf-token", methods=["GET"])
def get_csrf_token():
    return jsonify({"token": csrf.generate()})


# ── Pageview tracking ─────────────────────────────────────────
@app.route("/api/track/pageview", methods=["POST"])
def track_pageview():
    data     = request.get_json(silent=True) or {}
    ip       = get_ip()
    page     = data.get("page", "/")
    referrer = request.referrer or data.get("referrer", "")
    utm = {k: data.get(k, "") for k in ("utm_source", "utm_medium", "utm_campaign")}
    analytics.track_pageview(page=page, ip=ip, referrer=referrer, **utm)
    return jsonify({"ok": True})


# ── Pitch submission ──────────────────────────────────────────
@app.route("/api/submit/pitch", methods=["POST"])
def submit_pitch():
    ip   = get_ip()
    data = request.get_json(silent=True) or {}

    # Honeypot check
    if honeypot.triggered(data):
        security_log.record(EventType.HONEYPOT_TRIGGERED, ip=ip,
                            detail="Honeypot field filled — likely bot")
        blocklist.strike(ip)
        return jsonify({"success": False, "errors": ["Invalid submission."]}), 400

    # CSRF check
    csrf_token = request.headers.get("X-CSRF-Token") or data.get("csrf_token")
    if not csrf.verify(csrf_token):
        security_log.record(EventType.CSRF_FAIL, ip=ip, detail="CSRF token invalid or missing")
        blocklist.strike(ip)
        return jsonify({"success": False, "errors": ["Security check failed. Refresh and try again."]}), 403

    # Rate limit
    rate = rate_limiter.check(ip)
    if not rate["allowed"]:
        security_log.record(EventType.PITCH_RATE_LIMITED, ip=ip, detail=rate["reason"])
        blocklist.strike(ip)
        return jsonify({"success": False, "errors": [rate["reason"]]}), 429

    # Also rate-limit by email
    email = data.get("email", "").strip().lower()
    if email:
        email_rate = rate_limiter.check(email)
        if not email_rate["allowed"]:
            security_log.record(EventType.PITCH_RATE_LIMITED, ip=ip, detail=f"Email rate limit: {email}")
            return jsonify({"success": False, "errors": [email_rate["reason"]]}), 429

    # Validate
    result = validator.validate(data)
    if not result["valid"]:
        security_log.record(EventType.PITCH_INVALID, ip=ip,
                            detail=str(result["errors"]))
        return jsonify({"success": False, "errors": result["errors"]}), 422

    clean = result["clean"]
    security_log.record(EventType.PITCH_VALID, ip=ip,
                        detail=f"Valid pitch: {clean['title'][:40]}",
                        section=clean["section"], name=clean["name"])
    analytics.track_submission(section=clean["section"],
                               source=data.get("utm_source", "direct"))
    analytics.track_conversion("pitch_submitted",
                               utm_source=data.get("utm_source", "direct"),
                               utm_medium=data.get("utm_medium", ""),
                               utm_campaign=data.get("utm_campaign", ""))

    return jsonify({
        "success": True,
        "message": "Pitch received. The network will review it. All decisions are final.",
        "ref":     clean["fingerprint"],
    })


# ── Subscribe ─────────────────────────────────────────────────
@app.route("/api/subscribe", methods=["POST"])
def subscribe():
    ip   = get_ip()
    data = request.get_json(silent=True) or {}

    if honeypot.triggered(data):
        security_log.record(EventType.HONEYPOT_TRIGGERED, ip=ip)
        return jsonify({"success": False, "errors": ["Invalid submission."]}), 400

    email = data.get("email", "").strip().lower()
    if not email or not re.match(r'^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}$', email):
        return jsonify({"success": False, "errors": ["Valid email address required."]}), 422

    source = data.get("utm_source", "website")
    result = analytics.track_subscriber(email, source=source)

    if result["success"]:
        security_log.record(EventType.SUBSCRIBE_OK, ip=ip, detail=f"source={source}")
        return jsonify({"success": True, "message": "You're in the web. Stay tuned."})
    else:
        security_log.record(EventType.SUBSCRIBE_DUP, ip=ip)
        return jsonify({"success": False, "errors": [result["reason"]]}), 409


# ── Webhook from Formspree ────────────────────────────────────
@app.route("/api/webhook/formspree", methods=["POST"])
def formspree_webhook():
    ip        = get_ip()
    payload   = request.get_data()
    signature = request.headers.get("X-Formspree-Signature", "")

    if not webhook_verifier.verify(payload, signature):
        security_log.record(EventType.WEBHOOK_FAIL, ip=ip,
                            detail="Formspree webhook signature mismatch")
        abort(401)

    data = request.get_json(silent=True) or {}
    security_log.record(EventType.WEBHOOK_OK, ip=ip,
                        detail=f"Formspree submission: {data.get('_form_name','')}")

    # Mirror any Formspree submission into analytics
    source = data.get("utm_source", "formspree")
    analytics.track_conversion("formspree_submission", utm_source=source)

    return jsonify({"ok": True})


# ══════════════════════════════════════════════════════════════
# ADMIN / ANALYTICS API
# ══════════════════════════════════════════════════════════════

@app.route("/api/admin/analytics", methods=["GET"])
def admin_analytics():
    require_admin()
    security_log.record(EventType.ADMIN_ACCESS, ip=get_ip(), detail="Analytics API accessed")
    return jsonify(analytics.summary())


@app.route("/api/admin/security", methods=["GET"])
def admin_security():
    require_admin()
    return jsonify({
        "threats":    security_log.threat_summary(),
        "blocklist":  blocklist.status(),
        "recent_events": [asdict(e) for e in security_log.recent(24)][-50:],
    })


@app.route("/api/admin/export", methods=["POST"])
def admin_export():
    require_admin()
    analytics.export_json()
    return jsonify({"ok": True, "file": Config.ANALYTICS_FILE})


@app.route("/api/admin/unblock", methods=["POST"])
def admin_unblock():
    require_admin()
    data = request.get_json(silent=True) or {}
    ip   = data.get("ip", "")
    if ip:
        blocklist.unblock(ip)
        return jsonify({"ok": True, "unblocked": ip})
    return jsonify({"error": "ip required"}), 400


# ── Health check ──────────────────────────────────────────────
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status":  "operational",
        "service": "Salem Mania Security Backend",
        "version": "1.0.0",
    })


# ═══════════════════════════════════════════════════════════════
# SEED DEMO DATA (remove in production)
# ═══════════════════════════════════════════════════════════════

def _seed_demo():
    """Populate analytics with realistic demo data for the dashboard."""
    import random
    from datetime import datetime, timedelta

    pages    = ["/", "/articles", "/get-involved", "/those-involved", "/articlesalemmania"]
    sources  = ["instagram", "direct", "reddit", "google", "github", "submissiongrinder"]
    mediums  = ["bio", "post", "story", "organic", "post", "listing"]
    campaigns= ["pitch_season", "brand_awareness", "article_promo", "writer_recruitment", ""]
    sections = ["Film", "Music", "Culture", "Literature", "Opinion", "Poetry"]

    rng  = random.Random(42)
    now  = datetime.now()

    for i in range(420):
        days_ago = rng.randint(0, 29)
        fake_ts  = (now - timedelta(days=days_ago,
                                    hours=rng.randint(0,23),
                                    minutes=rng.randint(0,59)))
        pv = PageView(
            page     = rng.choice(pages),
            referrer = rng.choice(sources),
            source   = rng.choice(sources),
            medium   = rng.choice(mediums),
            campaign = rng.choice(campaigns),
            ip       = hashlib.sha256(f"ip{i}".encode()).hexdigest()[:12],
            timestamp= fake_ts.isoformat(),
        )
        analytics._pageviews.append(pv)

    for i in range(38):
        days_ago = rng.randint(0, 29)
        fake_ts  = (now - timedelta(days=days_ago)).isoformat()
        analytics._submissions.append({
            "section":   rng.choice(sections),
            "source":    rng.choice(sources),
            "timestamp": fake_ts,
        })
        analytics._conversions.append(ConversionEvent(
            kind     = "pitch_submitted",
            source   = rng.choice(sources),
            medium   = rng.choice(mediums),
            campaign = rng.choice(campaigns),
            timestamp= fake_ts,
        ))

    for i in range(27):
        days_ago = rng.randint(0, 29)
        analytics._subscribers.append({
            "email":  hashlib.sha256(f"sub{i}".encode()).hexdigest()[:8] + "@example.com",
            "source": rng.choice(sources),
            "joined": (now - timedelta(days=days_ago)).isoformat(),
            "active": rng.random() > 0.05,
        })

    log.info("Demo data seeded — remove _seed_demo() call in production")


# ═══════════════════════════════════════════════════════════════
# ENTRYPOINT
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    _seed_demo()
    print("\n  Salem Mania — Security Backend")
    print("  ─" * 24)
    print(f"  Admin token: {Config.ADMIN_TOKEN}")
    print(f"  Set SM_ADMIN_TOKEN env var in production")
    print(f"  API base:  http://localhost:5050/api")
    print(f"  Analytics: http://localhost:5050/api/admin/analytics?token={Config.ADMIN_TOKEN}")
    print(f"  Security:  http://localhost:5050/api/admin/security?token={Config.ADMIN_TOKEN}")
    print("  ─" * 24 + "\n")
    app.run(host="0.0.0.0", port=5050, debug=False)

    
