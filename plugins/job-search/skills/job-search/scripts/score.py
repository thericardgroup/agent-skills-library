#!/usr/bin/env python3
"""Rank cached postings against THIS user's profile.

Every threshold, keyword and weight comes from profile.json. There are no
defaults for what a good role looks like, because a default here is just one
person's taste applied silently to someone else's career.

Input:  postings.json   (written by sweep_ats.py / sweep_aggregator.py)
Output: ranked.json     sorted, with the reason for every score
Usage:  score.py [--limit 20] [--include-stretch]
"""
import argparse, datetime, json, re, sys, os, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from checks import GateLog, Timer
from statepath import load, require_profile, state_root


def compile_group(patterns):
    return re.compile("|".join(f"(?:{p})" for p in patterns), re.I) if patterns else None


def requirements_block(text):
    m = re.search(r'(requirement|qualification|what you.{0,6}(need|bring|ll have)'
                  r'|who you are|about you|minimum qualifications)', text, re.I)
    return text[m.start():m.start() + 4000] if m else text[:4000]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--include-stretch", action="store_true",
                    help="keep roles above the user's stated level instead of flagging them")
    a = ap.parse_args(argv)

    prof = require_profile()
    postings = load("postings.json", [])
    if not postings:
        raise SystemExit("postings.json is empty. Run a sweep first.")

    titles = prof.get("titles", {})
    TITLE_OK = compile_group(titles.get("target", []))
    TITLE_BAD = compile_group(titles.get("exclude", []))
    if not TITLE_OK:
        raise SystemExit("profile.titles.target is empty. Nothing to search for.")

    locp = prof.get("location", {})
    # Unknown country is not evidence of exclusion. Boards write location as free
    # text, so "Chicago, IL" contains no country name and used to be discarded as
    # foreign -- dropping exactly the local roles the user most wants.
    own_country = (locp.get("country") or "united states").lower()
    COUNTRY_ALIASES = {"united states": ["united states", "usa", "u.s.", "us",
                                         "america", "remote - us", "anywhere"]}
    own_terms = COUNTRY_ALIASES.get(own_country, [own_country])
    FOREIGN = compile_group(locp.get("reject_countries") or [
        "canada", "united kingdom", "ireland", "germany", "france", "netherlands",
        "spain", "poland", "india", "australia", "singapore", "japan", "brazil",
        "mexico", "israel", "emirates", "south africa", "new zealand"])
    metros = compile_group(locp.get("acceptable_metros", []) + locp.get("metro_aliases", []))
    other_cities = compile_group(locp.get("reject_metros", []))
    remote_ok = locp.get("remote_ok", True)

    pay_floor = (prof.get("pay") or {}).get("floor")
    max_age = prof.get("max_posting_age_days", 60)

    interests = prof.get("interests", [])
    gaps = prof.get("gaps", [])
    for g in interests + gaps:
        g["_re"] = compile_group(g.get("patterns", []))

    seniority = prof.get("seniority", {})
    at_level = compile_group(seniority.get("at_level", []))
    above = compile_group(seniority.get("above_level", []))
    below = compile_group(seniority.get("below_level", []))

    # Applications are tracked per requisition. Excluding a whole employer after
    # one application hides every other vacancy there, which is the opposite of
    # what a user wants from a company they were interested enough to apply to.
    # Requisition ids are only unique within a board. Deduplicating on the bare
    # number let an application at one employer suppress an unrelated role at
    # another that happened to share it.
    apps = load("applications.json", {})
    SUPPRESSING = set(prof.get("suppress_statuses")
                      or ["submitted", "in_progress", "interviewing", "offer", "rejected"])
    applied_reqs = set()
    for v in apps.values():
        if not isinstance(v, dict) or not v.get("requisition_id"):
            continue
        if v.get("status") and v["status"] not in SUPPRESSING:
            continue
        applied_reqs.add("::".join([str(v.get("platform", "")), str(v.get("board", "")),
                                    str(v["requisition_id"])]))
    excluded_employers = {e.lower() for e in (prof.get("exclude_employers") or [])}

    # Constraints the interview collects. Until these were wired in they were
    # asked for, written down, and then ignored by every filter -- which is
    # worse than not asking, because the user believes they have been heard.
    cons = prof.get("constraints") or {}
    days_cap = cons.get("onsite_days_max")
    travel_cap = cons.get("travel_ceiling_pct")
    will_relocate = cons.get("will_relocate", False)
    needs_sponsorship = cons.get("visa_sponsorship_needed", False)

    DAYS_RE = re.compile(
        r'(\d)\s*\+?\s*days?\s*(?:per|a|/|each)\s*week\s*(?:in[- ]?(?:the\s*)?office|on[-\s]?site)'
        r'|(?:every\s*weekday|five\s*days\s*a\s*week)', re.I)
    TRAVEL = re.compile(r'(\d{1,3})\s*%\s*(?:travel|of the time travel)'
                        r'|travel\s*(?:up to|of)?\s*(\d{1,3})\s*%', re.I)
    RELOC_REQ = re.compile(r'relocat(?:e|ion)\s*(?:to\s+\w+\s*)?(?:is\s*)?(?:required|expected)'
                           r'|must\s*relocate', re.I)
    NO_SPONSOR = re.compile(r'(?:are\s*)?(?:un(?:able|willing)|not able|cannot|will not)\s*'
                            r'(?:to\s*)?(?:provide|offer|sponsor)[^.]{0,40}sponsor'
                            r'|no\s*(?:visa\s*)?sponsorship', re.I)

    ONSITE = compile_group(prof.get("onsite_patterns") or [
        r"\d\s*\+?\s*(?:day|days)\s*(?:per|a|/|each)\s*week\s*(?:in[- ]?(?:the\s*)?office|on[-\s]?site)",
        r"hybrid\s*(?:work\s*)?schedule", r"this\s*(?:is\s*a\s*)?hybrid\s*(?:role|position)",
        r"must\s*(?:be\s*)?(?:located|reside|live)\s*(?:in|within|near)",
        r"commut(?:e|ing)\s*distance", r"relocat(?:e|ion)\s*(?:is\s*)?required"])

    # The age window exists for aggregator records, which go stale within days
    # and keep listing roles that closed. A board is different: the employer's
    # own system returned this posting just now, which is the liveness proof the
    # date was standing in for. Greenhouse reports updated_at, so a long-running
    # requisition looks months old while being perfectly open -- on one real
    # board a third of live postings fell outside a 60-day window.
    # "source": "board" says where a row came from, not when. A saved sweep from
    # a month ago is just as stale as an old aggregator row, so the exemption
    # requires a recent observation of that posting, not merely a board label.
    cut = time.time() - max_age * 86400
    cache_cut = time.time() - prof.get("max_cache_age_days", 7) * 86400
    recently_seen = lambda p: (p.get("fetched_at") or 0) >= cache_cut
    fresh = [p for p in postings
             if (p.get("source") == "board" and recently_seen(p))
             or (p.get("pubDate") or 0) >= cut]
    stale_board = [p for p in postings
                   if p.get("source") == "board" and not recently_seen(p)]
    if stale_board:
        print(f"  !! {len(stale_board)} board posting(s) have not been re-fetched recently "
              f"and are being judged on publication date instead. Re-run the sweep.",
              file=sys.stderr)

    GATES = ["older than window", "title mismatch", "outside country",
             "employer excluded by the user", "already applied to this requisition",
             "below pay floor", "onsite outside acceptable metros",
             "hard requirement missed", "travel above the stated ceiling",
             "relocation required", "no visa sponsorship",
             "more office days than the user accepts"]
    gl = GateLog(len(postings), gates=GATES)
    for _ in range(len(postings) - len(fresh)):
        gl.drop("older than window")

    out, rejected_onsite = [], []

    with Timer("score", "a few seconds"):
        for j in fresh:
            title = j.get("title") or ""
            if not TITLE_OK.search(title) or (TITLE_BAD and TITLE_BAD.search(title)):
                gl.drop("title mismatch"); continue

            locs = ", ".join(j.get("locationRestrictions") or [])
            low = locs.lower()
            if locs and not any(t in low for t in own_terms):
                # Only drop on positive evidence of somewhere else.
                if FOREIGN and FOREIGN.search(locs):
                    gl.drop("outside country"); continue

            # Excluded metros are checked against the stated location too, not
            # only inside the body window. verify_one.py was strict here and
            # score.py was not, so a London-only role could rank second for a
            # candidate who cannot leave San Francisco. Acceptable first, so a
            # multi-city posting is kept on the strength of one good location.
            if locs:
                if metros and metros.search(locs):
                    pass
                elif other_cities and other_cities.search(locs):
                    rejected_onsite.append(dict(company=(j.get("companyName") or "").strip(),
                                                title=title,
                                                city=other_cities.search(locs).group(0),
                                                phrase="stated location"))
                    gl.drop("onsite outside acceptable metros"); continue

            company = (j.get("companyName") or "").strip()
            if company.lower() in excluded_employers:
                gl.drop("employer excluded by the user"); continue
            posting_key = "::".join([str(j.get("platform", "")), str(j.get("board", "")),
                                      str(j.get("requisition_id"))])
            if posting_key in applied_reqs:
                gl.drop("already applied to this requisition"); continue

            lo, hi = j.get("minSalary"), j.get("maxSalary")
            if (j.get("salaryPeriod") or "yearly").lower() not in ("yearly", "annual", "year"):
                lo = hi = None
            if pay_floor and hi and hi < pay_floor:
                gl.drop("below pay floor"); continue

            desc = j.get("description") or ""
            reqs = requirements_block(desc)
            blob = f"{title} {desc[:8000]}"

            score, plus, minus = 0, [], []

            # --- location, read from the body rather than any API flag -------
            loc_note = ""
            m = ONSITE.search(desc) if ONSITE else None
            if m:
                window = desc[max(0, m.start() - 400): m.start() + 400]
                if metros and metros.search(window):
                    loc_note = "onsite, acceptable metro"
                elif other_cities and other_cities.search(window):
                    city = other_cities.search(window).group(0)
                    rejected_onsite.append(dict(company=company, title=title, city=city,
                                                phrase=" ".join(m.group(0).split())[:60]))
                    gl.drop("onsite outside acceptable metros"); continue
                elif not remote_ok:
                    gl.drop("onsite outside acceptable metros"); continue
                else:
                    loc_note = "onsite language, city unclear"

            # --- stated constraints -------------------------------------------
            if days_cap is not None:
                dm = DAYS_RE.search(desc)
                if dm:
                    need = int(dm.group(1)) if dm.group(1) else 5
                    if need > days_cap:
                        gl.drop("more office days than the user accepts"); continue
            if travel_cap is not None:
                tm = TRAVEL.search(desc)
                if tm:
                    pct = int(next(g for g in tm.groups() if g))
                    if pct > travel_cap:
                        gl.drop("travel above the stated ceiling"); continue
            if not will_relocate and RELOC_REQ.search(desc):
                gl.drop("relocation required"); continue
            if needs_sponsorship and NO_SPONSOR.search(desc):
                gl.drop("no visa sponsorship"); continue

            # --- interests ---------------------------------------------------
            for grp in interests:
                rx = grp["_re"]
                if not rx:
                    continue
                if rx.search(title):
                    score += grp.get("title_weight", 20)
                    plus.append(f"{grp['name']} in title")
                elif rx.search(blob):
                    score += grp.get("body_weight", 8)
                    plus.append(f"{grp['name']} in scope")

            # --- seniority ---------------------------------------------------
            if at_level and at_level.search(title):
                score += seniority.get("at_level_bonus", 12)
            elif above and above.search(title):
                if not a.include_stretch:
                    score += seniority.get("above_level_penalty", -8)
                minus.append("above stated level")
            elif below and below.search(title):
                score += seniority.get("below_level_penalty", -6)
                minus.append("below stated level")

            # --- gaps ----------------------------------------------------------
            hard_miss = None
            for grp in gaps:
                rx = grp["_re"]
                if rx and rx.search(reqs):
                    if grp.get("hard"):
                        hard_miss = grp["name"]
                        break
                    score -= abs(grp.get("penalty", 10))
                    minus.append(grp["name"])
                    gl.penalty(grp["name"])
            if hard_miss:
                gl.drop("hard requirement missed")
                continue

            # --- pay and recency ------------------------------------------------
            if hi and pay_floor:
                ratio = hi / pay_floor
                score += 14 if ratio >= 1.6 else 10 if ratio >= 1.3 else 5 if ratio >= 1.1 else 0
            elif not hi:
                score += 2
                minus.append("pay not posted")

            if loc_note.startswith("onsite, acceptable"):
                score += 6
            elif loc_note:
                score -= 12
                minus.append(loc_note)

            posted = datetime.datetime.fromtimestamp(j.get("pubDate") or 0)
            age = (datetime.datetime.now() - posted).days
            # Recency is a staleness proxy for aggregator records only. On a
            # board, the date is when the requisition was last edited, and
            # penalising that ranked an untouched-but-open senior role below an
            # early-career one posted last week.
            if j.get("source") != "board":
                score += 8 if age <= 14 else 3 if age <= 30 else -10 if age > 45 else 0

            out.append(dict(score=score, posted=posted.strftime("%Y-%m-%d"),
                            company=company, title=title, min=lo, max=hi,
                            plus="; ".join(plus) or "generalist match",
                            minus="; ".join(minus) or "-",
                            url=j.get("applicationLink") or "",
                            platform=j.get("platform", ""), board=j.get("board", ""),
                            requisition_id=j.get("requisition_id", "")))

    out.sort(key=lambda r: -r["score"])
    with open(os.path.join(state_root(), "ranked.json"), "w") as fh:
        json.dump(dict(ranked=out, rejected_onsite=rejected_onsite), fh, indent=1)

    gl.report(len(out))
    print(f"\n  qualifying: {len(out)}", file=sys.stderr)
    print(f"  rejected as onsite outside acceptable metros: {len(rejected_onsite)}",
          file=sys.stderr)
    print("\n  Scores rank against this profile only. They are not a quality judgment,\n"
          "  and a low score on a role you want is a reason to check the profile.\n",
          file=sys.stderr)

    for i, r in enumerate(out[:a.limit], 1):
        pay = f"${r['min']//1000}-{r['max']//1000}K" if r['min'] and r['max'] else "not posted"
        print(f"{i:2}. [{r['score']:3}] {r['company'][:22]:22} | {r['title'][:44]:44} "
              f"| {pay:12} | -{r['minus'][:34]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
