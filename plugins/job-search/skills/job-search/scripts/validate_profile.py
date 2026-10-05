#!/usr/bin/env python3
"""Check a profile before anything depends on it.

A syntactically valid profile is not a usable one. A regex that does not
compile, a pay floor written as a string, a metro list that is a bare string
rather than a list -- each of these produces a search that runs, returns
something, and is quietly wrong.

Requirements differ by stage, so they are reported separately: searching needs
targets and constraints, packaging needs an identity.

Usage:
  validate_profile.py                 validate the current profile
  validate_profile.py --file p.json
  validate_profile.py --stage search  only what scoring needs
"""
import argparse, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from statepath import load, state_file


def _patterns(value, where, errors):
    if not isinstance(value, list):
        errors.append(f"{where} must be a list, got {type(value).__name__}")
        return
    for pat in value:
        if not isinstance(pat, str):
            errors.append(f"{where} contains a non-string entry: {pat!r}")
            continue
        try:
            re.compile(pat)
        except re.error as e:
            errors.append(f"{where} has an invalid regular expression {pat!r}: {e}")


def validate(profile, stage="all"):
    errors, warnings = [], []
    want_search = stage in ("all", "search")
    want_package = stage in ("all", "package")

    if not isinstance(profile, dict):
        return ["profile must be a JSON object"], []

    if want_search:
        titles = profile.get("titles")
        if not isinstance(titles, dict):
            errors.append("titles is required for searching and must be an object")
        else:
            target = titles.get("target")
            if not target:
                errors.append("titles.target is empty; there is nothing to search for")
            else:
                _patterns(target, "titles.target", errors)
            if titles.get("exclude"):
                _patterns(titles["exclude"], "titles.exclude", errors)

            # How the targets got here changes what they mean. A user who named
            # them has decided; a derivation from their history is a hypothesis
            # the first ranking should be allowed to revise, and it has to show
            # the evidence it came from or nobody can argue with it.
            source = titles.get("source")
            if source is None:
                warnings.append("titles.source is not set, so there is no record of whether "
                                "the user named these targets or they were derived from "
                                "their history")
            elif source not in ("stated", "derived"):
                errors.append(f"titles.source must be 'stated' or 'derived', not {source!r}")
            elif source == "derived":
                ev = titles.get("derived_from")
                if not ev:
                    errors.append("titles.source is 'derived' but titles.derived_from is "
                                  "empty. A derived target without the evidence behind it "
                                  "cannot be checked or argued with.")
                elif not isinstance(ev, list):
                    errors.append("titles.derived_from must be a list")
                else:
                    for i, item in enumerate(ev):
                        if not isinstance(item, dict):
                            errors.append(f"titles.derived_from[{i}] must be an object")
                            continue
                        if not item.get("family"):
                            errors.append(f"titles.derived_from[{i}] needs a family name")
                        if not item.get("evidence"):
                            errors.append(f"titles.derived_from[{i}] needs the evidence from "
                                          f"the user's own history that supports it")

        loc = profile.get("location")
        if not isinstance(loc, dict):
            errors.append("location is required; without it no posting can be judged")
        else:
            if "remote_ok" not in loc:
                errors.append("location.remote_ok is required. Leaving it unset used to "
                              "default to accepting remote, which silently passed roles "
                              "the user cannot take.")
            for field in ("acceptable_metros", "metro_aliases", "reject_metros"):
                if field in loc and not isinstance(loc[field], list):
                    errors.append(f"location.{field} must be a list of strings")
            if not loc.get("remote_ok") and not loc.get("acceptable_metros"):
                errors.append("this profile accepts neither remote work nor any metro, "
                              "so every posting will be rejected")
            if loc.get("remote_ok") and not loc.get("acceptable_metros"):
                warnings.append("no acceptable_metros: any onsite posting will be "
                                "unresolved rather than rejected, and will need a "
                                "manual decision")

        pay = profile.get("pay") or {}
        for field in ("floor", "target"):
            if field in pay and not isinstance(pay[field], (int, float)):
                errors.append(f"pay.{field} must be a number, not {type(pay[field]).__name__}")
        if not pay.get("floor"):
            warnings.append("no pay.floor: postings below the user's minimum will not be "
                            "filtered out")

        cons = profile.get("constraints")
        if cons is not None:
            if not isinstance(cons, dict):
                errors.append("constraints must be an object")
            else:
                tc = cons.get("travel_ceiling_pct")
                if tc is not None and not (isinstance(tc, (int, float)) and 0 <= tc <= 100):
                    errors.append("constraints.travel_ceiling_pct must be a number 0-100")
                for flag in ("will_relocate", "visa_sponsorship_needed"):
                    if flag in cons and not isinstance(cons[flag], bool):
                        errors.append(f"constraints.{flag} must be true or false")
                od = cons.get("onsite_days_max")
                if od is not None and not (isinstance(od, int) and 0 <= od <= 7):
                    errors.append("constraints.onsite_days_max must be a whole number 0-7")
        else:
            warnings.append("no constraints block: travel, relocation and sponsorship "
                            "cannot be filtered on")

        for group, where in ((profile.get("interests") or [], "interests"),
                             (profile.get("gaps") or [], "gaps")):
            if not isinstance(group, list):
                errors.append(f"{where} must be a list")
                continue
            for i, item in enumerate(group):
                if not isinstance(item, dict) or "name" not in item:
                    errors.append(f"{where}[{i}] needs a name")
                    continue
                _patterns(item.get("patterns", []), f"{where}[{i}].patterns", errors)
        hard = [g for g in (profile.get("gaps") or [])
                if isinstance(g, dict) and g.get("hard")]
        if len(hard) > 4:
            warnings.append(f"{len(hard)} gaps are marked hard. Each one disqualifies a "
                            f"role outright, and too many returns an empty list that "
                            f"teaches the user nothing.")

    if want_package:
        ident = profile.get("identity")
        if not isinstance(ident, dict):
            errors.append("identity is required to generate documents")
        else:
            for field in ("name", "email"):
                if not ident.get(field):
                    errors.append(f"identity.{field} is required to generate documents")
            for l in ident.get("links") or []:
                if not isinstance(l, dict) or not l.get("url"):
                    errors.append("each identity.links entry needs a url")
        res = profile.get("resume") or {}
        if not res.get("required_sections"):
            warnings.append("resume.required_sections is empty, so a generator that "
                            "silently drops a section will not be caught")
        if want_package and not res.get("experience"):
            warnings.append("resume.experience is empty; the resume generator will refuse")

    return errors, warnings


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file")
    ap.add_argument("--stage", choices=("all", "search", "package"), default="all")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)

    if a.file:
        profile = json.load(open(a.file, encoding="utf-8"))
        where = a.file
    else:
        profile = load("profile.json")
        where = state_file("profile.json")
        if not profile:
            print(f"No profile at {where}. Run the onboarding interview first.")
            return 1

    errors, warnings = validate(profile, a.stage)
    if not a.quiet:
        print(f"  {where}")
    for w in warnings:
        print(f"  warn  {w}")
    for e in errors:
        print(f"  ERROR {e}")
    if errors:
        print(f"\n  {len(errors)} problem(s) must be fixed before this profile can be used.")
        return 1
    if not a.quiet:
        print(f"  valid for '{a.stage}'" + (f", {len(warnings)} warning(s)" if warnings else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
