// Node's view of the profile revision. Must stay identical to
// checks.profile_fingerprint, which is why it hashes the same canonical JSON
// rather than reimplementing a judgement about which fields matter.
const crypto = require('crypto');
const { execFileSync } = require('child_process');
const path = require('path');

function profileFingerprint(profile) {
  const script = path.join(__dirname, '..', 'checks.py');
  const out = execFileSync('python3', ['-c',
    `import sys,json; sys.path.insert(0, ${JSON.stringify(path.dirname(script))}); ` +
    'from checks import profile_fingerprint; ' +
    'print(profile_fingerprint(json.load(sys.stdin)))'],
    { input: JSON.stringify(profile), encoding: 'utf8' });
  return out.trim();
}

module.exports = { profileFingerprint };
