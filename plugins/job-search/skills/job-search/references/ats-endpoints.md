# ATS endpoints — what works, and the traps

All verified working as of 2026-09-29. No API keys required for any of these.

## Greenhouse
```
https://boards-api.greenhouse.io/v1/boards/{slug}/jobs
https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true      # full JD
https://boards-api.greenhouse.io/v1/boards/{slug}/jobs/{id}?content=true
https://boards-api.greenhouse.io/v1/boards/{slug}/jobs/{id}?questions=true   # application fields
```
`?questions=true` is the one people miss. It returns every field on the application form, including
whether a cover letter is accepted and whether it is a file upload or a textarea. **Check this
before writing a cover letter.** One employer checked this way had no cover letter field at all, only a required free-text question. That employer is on Ashby, not Greenhouse, and Ashby publishes no equivalent questions endpoint -- fetch the board page and read the form. Do not assume the Greenhouse trick generalises.

**Trap: `absolute_url` can be broken.** Pindrop's was
`pindrop.com/careers/job-title/?gh_jid=8157227` where `job-title` is an unfilled template
placeholder. Every variant 404s, including both greenhouse.io hosts, which redirect into the same
dead path. The working fallback is the embedded form:
```
https://boards.greenhouse.io/embed/job_app?for={slug}&token={id}
```
**Always HTTP-check the apply URL before handing it to anyone.**

**Trap: slugs are not company names.** Pindrop is `pindropsecurity`. Toast is `toast`. Trase is
`trase`. When a guess returns 0 jobs, scrape the careers page for the real slug rather than
assuming the board is empty.

## Ashby
```
https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true
```
Returns compensation as a formatted string in `compensation.compensationTierSummary`.

**Trap: `isRemote` is unreliable.** PermitFlow returns `isRemote: true` with
`workplaceType: "Hybrid"` on a role that requires three days a week in a New York office. Only
`workplaceType === "Remote"` means remote, and even then read the JD body.

## Lever
```
https://api.lever.co/v0/postings/{slug}?mode=json
```
Has a top-level `workplaceType` field that has been accurate in testing. Description is split
across `description` plus a `lists` array; concatenate both or you lose the requirements section.

## SmartRecruiters
```
https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=100&offset={n}
https://api.smartrecruiters.com/v1/companies/{slug}/postings/{id}     # full JD + pay
```
100 per page, paginate on `totalFound`. ServiceNow has ~705 postings.

**Trap: paginate fully before concluding a role is gone.** A first-page-only check falsely reported
both ServiceNow Voice AI roles as closed.

## Workday
```
POST https://{tenant}.wd{N}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs
     {"appliedFacets":{}, "limit":20, "offset":0, "searchText":"..."}
GET  https://{tenant}.wd{N}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/job{externalPath}
```
**Tenant and site must be extracted from the company's careers-page HTML**, never guessed:
```
([a-z0-9-]+)\.wd(\d+)\.myworkdayjobs\.com/([A-Za-z0-9_-]+)
```
Guessing produced zero hits. A 406 at the tenant root is the wildcard default and is **not**
evidence the tenant exists. Instance numbers go at least to wd503.

## iCIMS
```
https://careers-{slug}.icims.com/jobs/search?ss=1&in_iframe=1
https://careers-{slug}.icims.com/jobs/search?ss=1&in_iframe=1&searchKeyword=...
```
**`in_iframe=1` is required.** Without it the page returns only nav and footer chrome. Confirmed
working on Cotiviti. Did not render for Granicus even after clearing a cookie wall, so coverage is
partial. Requires a browser, not curl — the list is JS-rendered.

## Aggregators, screened 2026-09-25

| Source | Verdict |
|---|---|
| **Himalayas** `himalayas.app/jobs/api?limit=20` | Best available. ~98K jobs. Cursor pagination is the documented path but slow at ~35 pages/min; the **deprecated `offset` param still works and parallelizes**, 14 threads pulled 41,825 unique jobs in 23 min. **Ignores every search/filter param** — filter client-side. |
| RemoteOK | Hard cap at 100 records |
| Remotive | Free tier returns 19 records regardless of `limit` |
| Arbeitnow | Europe only |
| **Indeed** | **Unreachable.** Cloudflare bot detection redirects to a login wall. Needs an authenticated human browser session. |

## LinkedIn
Authwall for any non-logged-in client. Job data is not reachable programmatically. Useful only
through an authenticated browser session, and then for people research rather than enumeration.
