// Node's view of the same state root the Python scripts use. Kept in sync by
// shelling to statepath.py rather than reimplementing the rule in two languages,
// because the last time two files each decided where state lived, the gate could
// not see its own records.
const { execFileSync } = require('child_process');
const path = require('path');
const fs = require('fs');

function stateRoot() {
  const script = path.join(__dirname, '..', 'statepath.py');
  return execFileSync('python3', ['-c',
    `import sys; sys.path.insert(0, ${JSON.stringify(path.dirname(script))}); ` +
    'from statepath import state_root; print(state_root())'],
    { encoding: 'utf8' }).trim();
}

function loadState(name, fallback) {
  const p = path.join(stateRoot(), name);
  try { return JSON.parse(fs.readFileSync(p, 'utf8')); }
  catch (e) { if (e.code === 'ENOENT') return fallback; throw e; }
}

function loadProfile() {
  const prof = loadState('profile.json', null);
  if (!prof) {
    throw new Error(
      `No profile at ${path.join(stateRoot(), 'profile.json')}.\n` +
      'Run the onboarding interview in SKILL.md before generating documents.');
  }
  return prof;
}

module.exports = { stateRoot, loadState, loadProfile };
