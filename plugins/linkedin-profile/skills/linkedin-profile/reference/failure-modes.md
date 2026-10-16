# Failure modes

Every entry here is something that actually broke during a real profile rebuild, cost time, and
would have passed silently as success. They are the reason this skill verifies instead of trusting.

Read this before writing any code that touches a live profile.

---

## Reading failures

**The activity feed swallows the profile.**
Extracting a profile's text returned the person's recent posts, comments and reactions in such
volume that the Experience section never appeared in the output. The conclusion drawn was that an
employer was missing from the profile. It was there the whole time.
**Fix: never conclude a section is absent from a text extraction alone. Scroll to and read each
section by its own anchor, and when something appears missing, say "I could not read it" rather
than "it is not there."**

**Logged-out reads hit an authwall.**
A browser without the person's session gets a sign-up wall on every profile URL, including their
own. The page returns HTTP 200 with no profile content, so a naive check reports success.
**Fix: confirm the reader is authenticated before reading anything. Check for a signed-in marker,
not for a 200.**

**Screenshot coordinates and DOM coordinates are different frames.**
Element positions read from the page do not line up with the coordinate space of a screenshot.
Clicks computed from DOM geometry land in the wrong place.
**Fix: click by element reference where the tooling supports it. When clicking by position, take a
screenshot first and use coordinates from that image.**

---

## Writing failures

**Setting a field programmatically can revert.**
A company name written directly into the field appeared to save, showed correctly on screen, and
was silently reverted afterward. The same edit, typed as real keyboard input, persisted.
**Fix: apply every change as real typed input. Never write values straight into fields.**

**The platform reports success it did not deliver.**
There was no error, no warning, and no visual difference between the edit that held and the one
that did not. The only way to tell was to read the field again after the page had genuinely been
re-fetched.
**Fix: after every write, close the editor and force a full reload of the profile, then re-read
the field and compare it against the intended value. If it does not match, report a failure.
Never report success you have not re-read.**

**Leaving the page and returning is not a reload.**
Client-side routing, browser history and an editor left open can all hand back the value you just
typed while the server still holds the old one. A check built that way confirms your own keystrokes
and nothing else.
**Fix: require a full reload with the editor closed, or an independent read of the saved profile,
before declaring anything persisted.**

**Batch application hides which change failed.**
Applying several fields in one pass makes a partial failure invisible: the summary says "applied"
and one field quietly kept its old value.
**Fix: one field at a time, approved individually, verified individually, reported individually.**

---

## Link preview failures

**A link preview is rejected until the URL matches the canonical form exactly.**
Adding a site to the Featured section failed twice with a generic "couldn't generate a preview"
message. The URL was correct and the page loaded fine in a browser. The difference was a trailing
slash: the canonical URL had one and the submitted URL did not.
**Fix: when a preview fails, try the canonical form of the URL, with and without the trailing
slash, before assuming the page or its tags are at fault. The error message does not distinguish
between a missing tag, an unreachable page, and a URL variant.**

**Preview images are cached per image URL, not per page.**
A preview image was fetched before the site finished deploying and was stored at a placeholder
size. Fixing the image at the same path changed nothing, because the cached copy was keyed to that
URL. Re-requesting the preview returned the same wrong image.
**Fix: publish the corrected image at a new filename, then force a re-scrape. Changing the bytes at
an existing URL does not clear the cache.**

**A missing asset can return HTTP 200.**
A preview image path that did not exist returned the site's homepage HTML with a 200 status, so
every existence check passed while the image was never there.
**Fix: check the response content type, not the status code. An image URL that returns
`text/html` is missing, whatever the status says.**

**Preview images have a minimum size.**
An image below the platform's threshold is accepted without complaint and then not displayed, or
displayed cropped.
**Fix: verify the rendered preview visually after any image change. Confirm dimensions at the
source rather than trusting that an accepted upload will display.**

---

## Suppression failures

**A profile can be complete, accurate, well written, and invisible.**
A single unchecked preference excluded an otherwise strong profile from every recruiter search
filtered on that preference. Nothing on the profile looked wrong. There is no notification, no
warning, and no way to tell from the public view.
**Fix: audit the recruiter-facing preferences before auditing anything cosmetic. The settings layer
determines whether the content layer is ever seen.**

**The public view is not the recruiter view.**
What a logged-out visitor sees, what a connection sees, and what a recruiter searching with filters
sees are three different things. Reviewing the public profile tells you almost nothing about
searchability.
**Fix: audit the settings that drive search inclusion directly. Do not infer them from how the
profile looks.**

---

## Process failures

**Rewriting before reading the resume produces confident contradictions.**
Polished new copy that disagrees with the resume in a recruiter's other tab is worse than the
original. A recruiter comparing the two documents is doing their job; a mismatch in dates, titles
or employer names reads as carelessness at best.
**Fix: the contradiction audit is a gate. No rewriting until the profile and the resume have been
compared line by line and every conflict is either resolved or deliberately accepted.**
**Exception, and only this one:** where the person has no resume and has explicitly chosen to
continue without one, the gate cannot run and the evidence standard replaces it. Every factual
claim must then come from the existing profile, or from something the person stated in the session
and confirmed when it was read back. A claim that traces to neither does not go in.

**Generic keyword advice optimises for nothing.**
Keywords guessed from a job title produce copy aimed at an imagined posting. The person's actual
target roles state their own language, and it is frequently not what the title suggests.
**Fix: align against the stated requirements of real postings the person is actually pursuing. If
they have none yet, say the alignment stage is unavailable rather than substituting guesses.**

**An uploaded file is not an applied change.**
Producing the copy, the image, or the checklist is the easy half. The change is not real until it
is on the profile and has been read back.
**Fix: track applied and verified as separate states from drafted. Never summarise drafted work as
done.**
