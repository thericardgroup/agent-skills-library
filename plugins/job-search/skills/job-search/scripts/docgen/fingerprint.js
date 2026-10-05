// Node's view of the profile revision. Must stay identical to
// checks.profile_fingerprint, which is why it hashes the same canonical JSON
// rather than reimplementing a judgement about which fields matter.
const crypto = require('crypto');
const { execFileSync } = require('child_process');
const path = require('path');

function ask(fn, profile) {
  const scripts = path.join(__dirname, '..');
  const out = execFileSync('python3', ['-c',
    `import sys,json; sys.path.insert(0, ${JSON.stringify(scripts)}); ` +
    `from checks import ${fn}; print(${fn}(json.load(sys.stdin)))`],
    { input: JSON.stringify(profile), encoding: 'utf8' });
  return out.trim();
}

const profileFingerprint = (profile) => ask('profile_fingerprint', profile);

// Who the profile belongs to. Needed separately because the assessment
// revision deliberately excludes identity -- two people with the same
// constraints share a revision, and without this the second one could
// generate documents under the first one's approval.
const candidateId = (profile) => ask('candidate_id', profile);

module.exports = { profileFingerprint, candidateId };
