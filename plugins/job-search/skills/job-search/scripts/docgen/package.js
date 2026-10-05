// The only supported way to produce documents for a role.
//
// The gate used to be a function nobody called. Three generators each had their
// own CLI, none of them asked whether the role was verified, and all three wrote
// files against an empty verified.json. A gate that is available but optional is
// not a gate, so this is now the entry point and the generators refuse to write
// without a key that clears it.
//
// Writes are staged: documents are built in a temporary directory, asserted, and
// only moved into place once every assertion has passed. A failed assertion used
// to leave its output behind, which is the one case where a bad document is most
// likely to get sent.
const fs = require('fs');
const os = require('os');
const path = require('path');
const crypto = require('crypto');
const { requireVerified, assertResume, assertPasteSafe } = require('./check');
const { loadProfile, loadState } = require('./state');

function verifiedRecord(key) {
  const rec = (loadState('verified.json', {}) || {})[key];
  if (!rec) throw new Error(`no verification record for "${key}"`);
  return rec;
}

async function buildPackage({ key, outDir, resume, letter, fit, profile }) {
  const { authorize } = require('./authorize');

  // A supplied profile is the one that will be used, so it is the one the
  // approval has to cover. Writing it to a file lets the single Python gate
  // evaluate it rather than this file forming a second opinion.
  let profilePath = null;
  if (profile) {
    profilePath = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'jobprof-')),
                            'profile.json');
    fs.writeFileSync(profilePath, JSON.stringify(profile));
  }

  const { rec, profile: prof } = authorize({
    key,
    contents: [{ label: 'letter', cfg: letter }, { label: 'fit', cfg: fit },
               { label: 'resume', cfg: resume }],
    profile, profilePath,
  });

  const staged = fs.mkdtempSync(path.join(os.tmpdir(), 'jobpkg-'));
  const written = [];

  try {
    if (resume) {
      const { writeResume } = require('./resume');
      const p = path.join(staged, 'resume.docx');
      // writeResume asserts before it writes; nothing lands if it fails.
      await writeResume(resume, p, prof, { key, profilePath });
      written.push(p);
    }
    if (letter) {
      const { writeLetter } = require('./letter');
      const p = path.join(staged, 'cover-letter.docx');
      await writeLetter(letter, p, prof, { key, profilePath });
      written.push(p);
      for (const para of letter.letter || []) {
        await assertPasteSafe(para, 'cover letter paragraph');
      }
    }
    if (fit) {
      const { writeFit } = require('./fit');
      const p = path.join(staged, 'fit-summary.md');
      // The fit summary carries the requisition and the verified apply URL, so
      // what the user reads cannot drift from what was checked.
      // The checked link wins, always. Taking it from the config let an
      // unverified URL reach the document the user applies through.
      await writeFit({ ...fit, key, apply_url: rec.apply_url },
                     p, prof, { key, profilePath });
      written.push(p);
    }

    fs.mkdirSync(outDir, { recursive: true });

    // Anything already here from an earlier run is declared, not silently left
    // to blend in. A reused directory holding a stale cover letter beside a
    // fresh resume is the mixed package A05 exists to prevent.
    const incoming = new Set(written.map((f) => path.basename(f))
                             .concat(['package-manifest.json']));
    const preexisting = fs.readdirSync(outDir).filter((f) => !incoming.has(f));

    const digest = (f) => 'sha256:' +
      crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex').slice(0, 32);

    // Build the manifest against the staged bytes, then publish manifest and
    // documents together. Copying first and describing afterwards leaves a
    // directory that looks like a package if the run dies between the two.
    const files = written.map((src) => ({
      name: path.basename(src),
      bytes: fs.statSync(src).size,
      sha256: digest(src),
    }));

    const manifest = {
      schema: 'job-search/package-manifest@1',
      key,
      generated_at: Date.now() / 1000,
      files,
      // The approval exactly as it stood. verified.json is overwritten on every
      // recheck, so a package that only points at it cannot be audited once the
      // role is re-verified or the record expires.
      approval: {
        status: rec.status,
        verified_at: rec.checked_at,
        title_matched: rec.title_matched,
        company: rec.company || null,
        apply_url: rec.apply_url,
        apply_url_ok: rec.apply_url_ok === true,
        location_ok: rec.location_ok === true,
        requirements_read: rec.requirements_read === true,
        body_fingerprint: rec.body_fingerprint || null,
        profile_rev: rec.profile_rev || null,
      },
      profile_rev: rec.profile_rev || null,
      preexisting_files: preexisting,
    };

    const staged_manifest = path.join(staged, 'package-manifest.json');
    fs.writeFileSync(staged_manifest, JSON.stringify(manifest, null, 1));

    const landed = written.concat([staged_manifest]).map((src) => {
      const dest = path.join(outDir, path.basename(src));
      fs.copyFileSync(src, dest);
      return dest;
    });
    if (preexisting.length) {
      console.log(`   note  ${preexisting.length} file(s) already in ${outDir} are not part `
                  + `of this package: ${preexisting.slice(0, 4).join(', ')}`);
    }

    return { key, files: landed };
  } finally {
    fs.rmSync(staged, { recursive: true, force: true });
  }
}

module.exports = { buildPackage };

if (require.main === module) {
  const [cfgPath, outDir] = process.argv.slice(2);
  if (!cfgPath || !outDir) {
    console.error(
      'usage: node package.js <package-config.json> <output-dir>\n\n' +
      '  config: {\n' +
      '    "key":    "greenhouse::acme::4056789",\n' +
      '    "resume": { "headline", "summary", "skills" },\n' +
      '    "letter": { "date", "title", "company", "letter": [...] },\n' +
      '    "fit":    { "title", "company", "verdict", "requirements": [...] }\n' +
      '  }\n\n' +
      '  Any of resume/letter/fit may be omitted. The key is never optional.');
    process.exit(2);
  }
  const cfg = JSON.parse(fs.readFileSync(cfgPath, 'utf8'));
  buildPackage({ ...cfg, outDir })
    .then((res) => {
      console.log(`\n   package for ${res.key}`);
      res.files.forEach((f) => console.log(`   wrote ${f}`));
    })
    .catch((e) => { console.error(`\n${e.message}`); process.exit(1); });
}
