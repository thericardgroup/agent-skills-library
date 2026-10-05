#!/usr/bin/env python3
"""Broad discovery sweep across an aggregator, to find employers worth resolving.

This is reconnaissance, not a source of truth. Aggregator records go stale within
days, so what comes out of here feeds resolve_ats.py and sweep_ats.py -- it is not
something to apply from.

The failure this guards against: a request that fails after its retries returns
nothing, and nothing looks exactly like a page with no results. Enough of those
and a broken sweep reports a complete, empty market. Failures are counted
separately and the run refuses to overwrite good data with a mostly-failed one.

Usage:
  sweep_aggregator.py --pages 200
  sweep_aggregator.py --pages 200 --max-failure-rate 0.02
"""
import argparse, json, sys, os, time, threading, queue, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from statepath import load, save
from checks import Timer

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
STEP = 20


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pages", type=int, default=200,
                    help="pages of %d. The full index is large; start small." % STEP)
    ap.add_argument("--workers", type=int, default=4,
                    help="14 used to be safe here and is now rate-limited: it fails "
                         "around half of all pages. 4 fails ~5%%, 2 fails none.")
    ap.add_argument("--max-failure-rate", type=float, default=0.05,
                    help="refuse to save if more than this fraction of pages failed")
    a = ap.parse_args(argv)

    q = queue.Queue()
    for off in range(0, a.pages * STEP, STEP):
        q.put(off)

    lock = threading.Lock()
    rows, failures, empties, done = [], [], [0], [0]
    t0 = time.time()

    def fetch(url):
        for _ in range(3):
            try:
                with urllib.request.urlopen(
                        urllib.request.Request(url, headers=UA), timeout=30) as r:
                    return json.load(r), None
            except Exception as e:
                last = f"{type(e).__name__}"
                time.sleep(1.5)
        return None, last

    def worker():
        while True:
            try:
                off = q.get_nowait()
            except queue.Empty:
                return
            d, err = fetch(f"https://himalayas.app/jobs/api?limit={STEP}&offset={off}")
            with lock:
                done[0] += 1
                if err:
                    # The distinction that matters: this page is unknown, not empty.
                    failures.append((off, err))
                else:
                    js = (d or {}).get("jobs") or []
                    if js:
                        rows.extend(js)
                    else:
                        empties[0] += 1
                if done[0] % 200 == 0:
                    print(f"  {done[0]}/{a.pages} pages  {len(rows)} rows  "
                          f"{len(failures)} failed  {int(time.time() - t0)}s",
                          file=sys.stderr, flush=True)
            q.task_done()

    with Timer(f"aggregator sweep, {a.pages} pages", f"~{a.pages // 25}s"):
        ths = [threading.Thread(target=worker, daemon=True) for _ in range(a.workers)]
        [t.start() for t in ths]
        [t.join() for t in ths]

    rate = len(failures) / max(1, a.pages)
    seen, uniq = set(), []
    for j in rows:
        g = j.get("guid") or j.get("applicationLink")
        if g in seen:
            continue
        seen.add(g)
        j["source"] = "aggregator"
        uniq.append(j)

    print(f"\n  pages:   {a.pages}", file=sys.stderr)
    print(f"  ok:      {a.pages - len(failures)}  ({empties[0]} genuinely empty)", file=sys.stderr)
    print(f"  failed:  {len(failures)}  ({rate:.1%})", file=sys.stderr)
    print(f"  unique:  {len(uniq)} postings", file=sys.stderr)

    if rate > a.max_failure_rate:
        print(f"\n  REFUSING to save. {rate:.1%} of pages failed, above the "
              f"{a.max_failure_rate:.1%} threshold.\n"
              f"  Coverage this incomplete would look like a small market rather than "
              f"a broken sweep.\n  Previous postings.json is untouched. Retry, or raise "
              f"--max-failure-rate deliberately.", file=sys.stderr)
        for off, err in failures[:10]:
            print(f"    offset {off}: {err}", file=sys.stderr)
        return 1

    existing = load("postings.json", [])
    save("postings.json", uniq)
    print(f"\n  saved {len(uniq)} postings (replaced {len(existing)})", file=sys.stderr)
    if failures:
        print(f"  !! {len(failures)} pages still failed. Coverage is incomplete; "
              f"some employers are missing from this set.", file=sys.stderr)
    print("\n  These are leads, not verified postings. Next: resolve_ats.py "
          "--from-postings", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
