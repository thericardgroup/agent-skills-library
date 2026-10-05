// Post-generation assertions. A stale generator silently dropped an entire
// employment block twice. The docx packer never errors on missing content, so
// check the bytes you actually wrote rather than the inputs you meant to write.
const JSZip = require('jszip');
const { execFileSync } = require('child_process');
const path = require('path');
const { loadProfile } = require('./state');

async function docxText(buffer) {
  const zip = await JSZip.loadAsync(buffer);
  const xml = await zip.file('word/document.xml').async('string');
  return xml.replace(/<\/w:p>/g, '\n').replace(/<[^>]+>/g, '')
            .replace(/&amp;/g, '&').replace(/&quot;/g, '"').replace(/&#\d+;/g, "'");
}

// What must appear in a resume is a property of whose resume it is. These come
// from the profile: the user's own contact details, plus any sections they told
// us never to drop. Hardcoding them means rejecting every other user's resume.
function requiredStrings(profile) {
  const id = profile.identity || {};
  const resume = profile.resume || {};
  const required = [
    ...(resume.required_sections || []),
    ...(resume.never_drop_employers || []),
  ];
  if (id.email) required.push(id.email);
  (id.links || []).forEach((l) => l.text && required.push(l.text));
  if (!required.length) {
    throw new Error(
      'profile.resume defines nothing that must survive generation.\n' +
      'Set resume.required_sections (for example "EDUCATION", "EARLIER EXPERIENCE") ' +
      'so a silently truncated document fails loudly instead of being sent.');
  }
  return required;
}

async function assertResume(buffer, label, profile) {
  const prof = profile || loadProfile();
  const required = requiredStrings(prof);
  const t = await docxText(buffer);
  const minChars = (prof.resume || {}).min_chars || 3000;

  const missing = required.filter((s) => !t.toLowerCase().includes(String(s).toLowerCase()));
  const problems = [];
  if (missing.length) problems.push(`MISSING: ${missing.join(', ')}`);
  if ((t.match(/—/g) || []).length) problems.push('contains em dashes');
  if (t.length < minChars) problems.push(`suspiciously short (${t.length} chars, min ${minChars})`);
  if (problems.length) {
    throw new Error(`[${label}] resume assertion failed -> ${problems.join(' | ')}`);
  }
  console.log(`   ok  ${label}  (${t.length} chars, ${required.length} required strings present)`);
}

// Characters an ATS text box may reject. One form rejected semicolons outright
// and gave no indication which character was the problem.
async function assertPasteSafe(text, label) {
  const bad = [];
  if (text.includes(';')) bad.push('semicolon');
  if (/[‘’“”]/.test(text)) bad.push('smart quotes');
  if (/—/.test(text)) bad.push('em dash');
  if (/ {2,}/.test(text)) bad.push('doubled spaces');
  if (bad.length) throw new Error(`[${label}] paste-unsafe -> ${bad.join(', ')}`);
  console.log(`   ok  ${label}  paste-safe`);
}

// Blocking verification gate. Shells to gate.py so Python and Node read one
// record. gate.py lives in scripts/, one level up from this directory.
function requireVerified(key) {
  const script = path.join(__dirname, '..', 'gate.py');
  try {
    execFileSync('python3', [script, key], { stdio: 'pipe' });
  } catch (e) {
    const msg = (e.stdout || Buffer.from('')).toString().trim() || e.message;
    throw new Error(`REFUSING to generate package for "${key}": ${msg}`);
  }
  console.log(`   ok  ${key}  verification current`);
}

module.exports = { docxText, assertResume, assertPasteSafe, requireVerified, requiredStrings };
