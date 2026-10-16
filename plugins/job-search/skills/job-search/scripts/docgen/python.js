// Find the Python interpreter on this machine.
//
// The command is not the same everywhere. A default Windows install from
// python.org provides `python` and `py` but NOT `python3`, so hardcoding
// `python3` meant a Windows user who had installed Python still hit a silent
// second failure with nothing explaining it.
//
// Resolution order matters: `py -3` is the Windows launcher and is the most
// reliable there, while `python3` is the safest on macOS and Linux because
// `python` can still be Python 2 on older systems.
const { execFileSync } = require('child_process');

let cached = null;

const CANDIDATES = process.platform === 'win32'
  ? [['py', ['-3']], ['python', []], ['python3', []]]
  : [['python3', []], ['python', []], ['py', ['-3']]];

function pythonCommand() {
  if (cached) return cached;
  const tried = [];
  for (const [cmd, prefix] of CANDIDATES) {
    try {
      const v = execFileSync(cmd, [...prefix, '-c',
        'import sys; print(sys.version_info[0])'],
        { encoding: 'utf8', stdio: ['pipe', 'pipe', 'pipe'] }).trim();
      if (v === '3') {
        cached = { cmd, prefix };
        return cached;
      }
      tried.push(`${cmd} (reported Python ${v})`);
    } catch (e) {
      tried.push(`${cmd} (not found)`);
    }
  }
  throw new Error(
    'Python 3 is required and was not found.\n' +
    `  Tried: ${tried.join(', ')}\n` +
    '  On Windows, install it from the Microsoft Store (search "Python 3"), which\n' +
    '  also provides the python3 command. On macOS, run: xcode-select --install');
}

/** Run a Python script or -c snippet with whichever interpreter exists. */
function runPython(args, opts = {}) {
  const { cmd, prefix } = pythonCommand();
  return execFileSync(cmd, [...prefix, ...args], opts);
}

module.exports = { pythonCommand, runPython };
