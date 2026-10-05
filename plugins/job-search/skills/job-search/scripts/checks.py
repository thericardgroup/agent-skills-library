"""Shared assertion + accounting helpers.

Exists because the expensive failures are the silent ones:
  - a stale generator dropped an entire employment block, twice
  - a filter change removed 91 roles with no log line
  - fuzzy title matching reported a dead role as live
  - a verification certified one posting under a different posting's name

Nothing here is clever. It is all "print the number so a human notices" and
"refuse when you do not actually know."
"""
import hashlib, json, time, sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from statepath import load, save

MAX_AGE_DAYS = 3   # a 4-day-old snapshot had 3 dead roles in its top 10


class GateLog:
    """Counts what each filter removed. A gate that fires on nothing is broken.

    Gates are declared up front. A counter that only exists once it has been
    incremented can never be observed at zero, which is exactly the case the
    warning below is for.
    """

    def __init__(self, total_in, gates=()):
        self.total_in = total_in
        self.counts = {g: 0 for g in gates}
        self.penalties = {}

    def declare(self, *gates):
        for g in gates:
            self.counts.setdefault(g, 0)

    def drop(self, gate):
        """This record was removed from the result set."""
        if gate not in self.counts:
            raise KeyError(
                f"undeclared gate {gate!r}. Declare it in GateLog(gates=...) so the "
                "never-fired check can see it. A typo here hides a broken filter."
            )
        self.counts[gate] += 1

    def penalty(self, name):
        """This record lost points but stayed in. Not a removal; never balances."""
        self.penalties[name] = self.penalties.get(name, 0) + 1

    def report(self, total_out, stream=sys.stderr):
        p = lambda s: print(s, file=stream)
        p(f"\n  IN  {self.total_in}")
        for g, n in sorted(self.counts.items(), key=lambda x: -x[1]):
            p(f"  -{n:<6} {g}")
        p(f"  OUT {total_out}")

        unaccounted = self.total_in - sum(self.counts.values()) - total_out
        if unaccounted:
            p(f"  !! {unaccounted} unaccounted for. A filter is dropping silently.")

        # A silent gate is only suspicious if it had anything to judge. Two
        # cases where it did not:
        #
        #   - a small set, where most gates legitimately match nothing
        #   - one gate removing nearly everything, which starves the rest
        #
        # Eleven "probably broken" warnings after a sweep whose real story is
        # "this employer has nothing in your field" buries the finding under
        # noise, at the moment the user most needs a plain answer.
        quiet = [g for g, n in sorted(self.counts.items()) if n == 0]
        removed = sum(self.counts.values())
        dominant = next((g for g, n in self.counts.items()
                         if removed and n / removed >= 0.9), None)

        if quiet and dominant and total_out == 0:
            p(f"\n  Everything was removed by one gate: {dominant}.")
            p(f"  The other {len(quiet)} gate(s) never saw a record, so nothing is known "
              f"about them here.")
            p(f"  This is a statement about this input, not proof that no suitable roles "
              f"exist anywhere.")
        elif quiet and self.total_in >= 50:
            for g in quiet:
                p(f"  !! gate '{g}' never fired. Either nothing matched it, or it is broken.")
        elif quiet:
            p(f"  ({len(quiet)} gate(s) matched nothing, normal on {self.total_in} records)")

        if self.penalties:
            p("  penalties applied (not removals):")
            for name, n in sorted(self.penalties.items(), key=lambda x: -x[1]):
                p(f"   {n:>5}  {name}")


class Timer:
    """Cost disclosure. Say how long before, and how long it actually took."""

    def __init__(self, label, estimate=None):
        self.label, self.estimate = label, estimate

    def __enter__(self):
        self.t0 = time.time()
        est = f"  (estimated {self.estimate})" if self.estimate else ""
        print(f"[{self.label}] starting{est}", file=sys.stderr)
        return self

    def __exit__(self, *a):
        el = int(time.time() - self.t0)
        print(f"[{self.label}] done in {el // 60}m {el % 60}s", file=sys.stderr)


# --- verification records -------------------------------------------------
#
# A record is keyed by stable ATS identity (platform::board::requisition_id),
# never by title. Two postings on one board can share a title; certifying the
# first match under the caller's chosen name is how the wrong role gets packaged.

def profile_fingerprint(profile):
    """A hash of the parts of the profile a verification actually depends on.

    An approval says "this posting suits this user". Change what the user will
    accept and the approval no longer means that, so it has to be reassessed --
    verifying a remote role and then deciding you will not work remotely must
    not leave the gate open.
    """
    relevant = {
        "location": (profile or {}).get("location") or {},
        "constraints": (profile or {}).get("constraints") or {},
    }
    blob = json.dumps(relevant, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def verification_key(platform, board, requisition_id):
    if not requisition_id:
        raise ValueError(
            "requisition_id is required. Title is not identity: boards carry "
            "duplicate titles, and titles change under a stable id."
        )
    return f"{platform}::{board}::{requisition_id}"


def record_verification(key, *, live, location_ok, requirements_read, apply_url,
                        title_matched, apply_url_ok=False, body_fingerprint=None,
                        profile_rev=None, company=None, notes=""):
    """A successful check. Every field must be something the caller actually
    established -- there are no defaults here on purpose.

    body_fingerprint survives across runs so the requirements attestation can be
    bound to the exact text that was displayed.
    """
    d = load("verified.json")
    prior = d.get(key, {})
    d[key] = dict(status="verified", checked_at=time.time(), live=live,
                  location_ok=location_ok, apply_url_ok=apply_url_ok,
                  requirements_read=requirements_read, apply_url=apply_url,
                  title_matched=title_matched,
                  body_fingerprint=body_fingerprint or prior.get("body_fingerprint"),
                  profile_rev=profile_rev or prior.get("profile_rev"),
                  company=company or prior.get("company", ""),
                  notes=notes)
    save("verified.json", d)


def record_attempt_failed(key, reason):
    """A recheck that could not complete.

    This overwrites any earlier success. An unreachable board does not mean the
    role is still live -- it means we no longer know, and packaging must stop
    until someone finds out.
    """
    d = load("verified.json")
    prior = d.get(key, {})
    d[key] = dict(status="failed", checked_at=time.time(), reason=reason,
                  live=False, location_ok=False, apply_url_ok=False,
                  requirements_read=False,
                  apply_url=prior.get("apply_url", ""),
                  title_matched=prior.get("title_matched", ""),
                  body_fingerprint=prior.get("body_fingerprint"),
                  superseded_verified_at=prior.get("checked_at"))
    save("verified.json", d)


def verification_gate(key, profile=None):
    """Returns (ok, reason). The package step must call this and refuse on False.

    Pass the current profile to check that the approval still describes this
    user; omit it only where no profile is available to compare.
    """
    d = load("verified.json").get(key)
    if not d:
        return False, (f"never verified. Run:  python3 scripts/verify_one.py --key '{key}'")

    if d.get("status") == "failed":
        return False, (f"last check failed ({d.get('reason', 'unknown')}). "
                       "The earlier approval no longer counts. Re-verify.")

    age = (time.time() - d["checked_at"]) / 86400
    if age > MAX_AGE_DAYS:
        return False, f"verification is {age:.1f} days old (max {MAX_AGE_DAYS}). Re-verify."

    # location_ok is deliberately tri-state. Reporting an unresolved location as
    # a failed one sends someone off to fix a constraint that was never checked.
    if d.get("location_ok") is None:
        return False, ("location was never resolved -- no profile constraints to compare "
                       "against, or the posting does not say where the work happens. "
                       "Read it and decide by hand.")

    if profile is not None:
        # Fail closed on a missing binding. A record written before candidate
        # binding existed is not evidence that this profile was assessed, and
        # treating absence as compatibility is how a stale approval survives an
        # incompatible edit.
        if not d.get("profile_rev"):
            return False, ("this approval carries no profile revision, so there is no "
                           "evidence it was assessed against the current profile. "
                           "Re-verify.")
        if profile_fingerprint(profile) != d["profile_rev"]:
            return False, ("the profile's location or constraints changed after this role "
                           "was verified, so the approval no longer describes this user. "
                           "Re-verify.")

    for field, msg in [("live", "posting is not live"),
                       ("location_ok", "location does not clear the user's constraint"),
                       ("apply_url_ok", "the apply link does not resolve, so the user "
                                        "cannot actually apply"),
                       ("requirements_read", "requirements were never actually read")]:
        if not d.get(field):
            return False, msg
    return True, "ok"
