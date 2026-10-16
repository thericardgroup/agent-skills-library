# Platform details

**Everything in this file rots.** The platform moves settings, renames pages and changes
thresholds without notice, and this file is a snapshot of what was true when it was written, not
a contract. Treat every value here as a starting point to confirm, never as fact to rely on.

**When something here does not match what you find:** say so, use what is actually on the screen,
and tell the person the skill's reference is out of date. Never force the page to match this file,
and never report a check as done when you could not find the thing to check.

---

## Settings pages

**Starting point.** The profile menu in the top navigation, usually labelled **Me**, opens a menu
containing **Settings & Privacy**. From there the controls below sat under the sections named.

**These names and groupings move.** If a label is not where this says, search the settings area for
the control by name, and if you still cannot find it, say so and record it as unchecked.

| What to check | Where it lived | Why it matters |
|---|---|---|
| Open-to-work preferences: job titles, workplace types, locations, start date | Editable from the **Open to** button on the profile itself, and under the job-seeking section of Settings & Privacy | The highest-yield check in the skill. Wanting remote work and never enabling it removes the person from every search filtered on remote. |
| Who can see they are open to work | Same place as the preferences, usually a choice between recruiters only and all members | Both are legitimate. The person should know which is set, and why. |
| Public profile visibility and search-engine indexing | Settings & Privacy, visibility section, public profile controls. Also reachable from **Edit public profile & URL** on the profile | Determines whether the profile is reachable at all from outside. |
| Custom profile URL | **Edit public profile & URL**, top right of that page | A URL ending in random digits looks unfinished on a resume. |
| Location and industry | On the profile itself, in the intro section, via the pencil icon | Both drive filters recruiters use constantly. Industry is frequently whatever was picked years ago. |

**In review mode the person has to look at these themselves.** Give them the starting point above
in plain words, one control at a time, and ask what they see. **A setting they could not find is
recorded as not checked, never as passing.**

### Requesting the data export

Settings & Privacy, then the data privacy section, then **Get a copy of your data**. The person
selects what to include and confirms; the archive arrives by email, typically within about ten
minutes for the profile-only selection and longer for a full archive.

Offer to continue with a pasted profile while they wait rather than stalling the session.

---

## Link previews

**Image size.** The commonly recommended preview image is about **1200 by 627 pixels**. A hard
minimum also exists below which the image is accepted and then silently not displayed.

**This file does not state that minimum, because stating a number nobody has verified is worse
than stating none.** Confirm the current requirement from the platform's own published guidance
before declaring an image acceptable. If you cannot confirm it, use the recommended size above and
**verify the rendered preview visually** — that check is authoritative regardless of what any
documented threshold says, because the failure is silent either way.

**Forcing a re-scrape.** The platform runs a Post Inspector tool at
`linkedin.com/post-inspector/`. Paste the URL there and inspect; that fetch is what refreshes a
stale preview. If that address has moved, search the platform's developer or help pages for "post
inspector" rather than guessing.

**The cache is keyed to the image URL, not the page.** Replacing the bytes at the same path
changes nothing. Publish the corrected image at a new filename and then re-scrape.

**Check the content type, not the status code.** A missing image path can return the site's
homepage HTML with a success status, so an existence check that only looks at the status passes
while the image is not there.

**Trailing slashes matter.** A preview that refuses to generate is frequently a URL variant rather
than a missing tag. Try the canonical form, with and without the trailing slash, before concluding
the page or its tags are at fault. The error message does not distinguish between these cases.
