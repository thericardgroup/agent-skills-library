// The single authorization boundary for producing a deliverable.
//
// A01 / A02 of docs/ACCEPTANCE.md. There were four writing entry points and
// three of them checked only that *some* approval was current, while the
// content, the posting and the candidate went unexamined. Three near-identical
// gateFor() copies is how that happened, so there is now one function and the
// writers have no other way in.
//
// What an approval actually asserts: this requisition, assessed against this
// candidate's stated constraints, at this time. Anything the approval does not
// name is not covered by it.
const { loadState, loadProfile } = require('./state');
const { execFileSync } = require('child_process');
const path = require('path');

// Identity comparison. Case and surrounding punctuation are formatting; the
// words are not. Containment is deliberately NOT accepted: "Researcher" at
// "Example" is a different posting from "Senior Researcher" at "Example
// Unrelated Subsidiary", and substring matching cannot tell them apart.
const norm = (x) => String(x == null ? '' : x)
  .toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();

function keyParts(key) {
  const p = String(key || '').split('::');
  if (p.length !== 3 || p.some((x) => !x)) {
    throw new Error(
      `"${key}" is not a requisition key. Expected platform::board::requisition_id.\n` +
      'Documents are generated for one verified posting, never for a title.');
  }
  return { platform: p[0], board: p[1], requisition_id: p[2] };
}

function gateOpen(key, profilePath) {
  // Shell to the same gate the Python side uses, so there is one definition of
  // "current approval" rather than a second one drifting here.
  const script = path.join(__dirname, '..', 'gate.py');
  const args = [script, key];
  if (profilePath) args.push('--profile', profilePath);
  try {
    execFileSync('python3', args, { stdio: 'pipe' });
  } catch (e) {
    const msg = (e.stdout || Buffer.from('')).toString().trim() || e.message;
    throw new Error(`REFUSING to generate for "${key}": ${msg}`);
  }
}

/**
 * Throws unless this exact content, for this exact candidate, is covered by a
 * current approval for this exact requisition. Returns the verified record and
 * the effective profile on success.
 *
 * contents: [{ label, cfg }] -- any config carrying title/company/apply_url.
 */
function authorize({ key, contents = [], profile, profilePath }) {
  keyParts(key);

  const effective = profile || loadProfile();
  const rec = (loadState('verified.json', {}) || {})[key];
  if (!rec) {
    throw new Error(
      `REFUSING: no verification record for "${key}".\n` +
      `Run:  python3 scripts/verify_one.py --key '${key}' --requirements-reviewed`);
  }

  // The gate is evaluated against the profile that will actually be used, not
  // whatever happens to be on disk. A caller-supplied profile that the approval
  // never saw is the case this exists for.
  gateOpen(key, profilePath || null);

  const conflicts = [];

  // A02: the approval must name the candidate assessment it covers. A record
  // without one is not evidence that this profile was considered.
  // Checked here against the profile that will actually be used, not only in
  // the Python gate. An exported writer can be handed a profile object with no
  // path, and the gate then reads whatever is on disk -- which let a second
  // person generate documents under the first person's approval.
  const { profileFingerprint, candidateId } = require('./fingerprint');
  if (!rec.profile_rev || !rec.candidate) {
    conflicts.push(
      'the approval carries no candidate binding, so there is no evidence of who ' +
      'it was assessed for. Re-verify.');
  } else if (candidateId(effective) !== rec.candidate) {
    conflicts.push(
      'this approval was given for a different candidate. An approval is evidence ' +
      'about one posting and one person.');
  } else if (profileFingerprint(effective) !== rec.profile_rev) {
    conflicts.push(
      "the profile used for generation is not the one this posting was approved " +
      'against (location or constraints differ). Re-verify against the current profile.');
  }

  // A01: content must name the approved posting, exactly.
  const recTitle = norm(rec.title_matched);
  const recCompany = norm(rec.company || keyParts(key).board);
  for (const { label, cfg } of contents) {
    if (!cfg) continue;
    if (cfg.title && recTitle && norm(cfg.title) !== recTitle) {
      conflicts.push(`${label}.title is "${cfg.title}" but the approval is for `
                     + `"${rec.title_matched}"`);
    }
    if (cfg.company && recCompany && norm(cfg.company) !== recCompany) {
      conflicts.push(`${label}.company is "${cfg.company}" but the approval is for `
                     + `"${rec.company || keyParts(key).board}"`);
    }
    if (cfg.apply_url && rec.apply_url && cfg.apply_url !== rec.apply_url) {
      conflicts.push(`${label}.apply_url is not the link that was checked`);
    }
    if (cfg.key && cfg.key !== key) {
      conflicts.push(`${label}.key names a different requisition`);
    }
  }

  if (conflicts.length) {
    throw new Error(
      `REFUSING: this is not covered by the approval for "${key}".\n  `
      + conflicts.join('\n  ')
      + '\n\nVerify the posting these documents are actually for.');
  }
  return { rec, profile: effective };
}

module.exports = { authorize, norm, keyParts };
