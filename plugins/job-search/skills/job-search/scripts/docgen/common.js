// Shared docx primitives. letter.js referenced r/p/link/FONT/NAVY without ever
// importing them, so the generator could not run in a clean process. They live
// here now, in one place, imported explicitly.
const { Document, Paragraph, TextRun, ExternalHyperlink } = require('docx');

const FONT = 'Calibri';
const NAVY = '1F3864';

const r = (text, opts = {}) => new TextRun({ text, font: FONT, ...opts });

const p = (children, spacing = {}) => new Paragraph({ spacing, children });

const link = (text, url, size = 18) => new ExternalHyperlink({
  link: url,
  children: [new TextRun({ text, font: FONT, size, color: '0563C1', underline: {} })],
});

const LETTER_PAGE = {
  size: { width: 12240, height: 15840 },
  margin: { top: 1080, bottom: 1080, left: 1260, right: 1260 },
};

// Identity comes from the user's profile, never from this file. A generator that
// knows whose documents it makes is a generator that can only serve one person.
function contactLine(identity) {
  const parts = [];
  if (identity.location) parts.push(r(`${identity.location}  |  `, { size: 18 }));
  if (identity.phone) parts.push(r(`${identity.phone}  |  `, { size: 18 }));
  if (identity.email) parts.push(r(`${identity.email}`, { size: 18 }));
  (identity.links || []).forEach((l) => {
    parts.push(r('  |  ', { size: 18 }));
    parts.push(link(l.text || l.url, l.url, 18));
  });
  return parts;
}

function requireIdentity(profile) {
  const id = (profile || {}).identity;
  const missing = ['name', 'email'].filter((k) => !id || !id[k]);
  if (missing.length) {
    throw new Error(
      `profile.identity is missing: ${missing.join(', ')}.\n` +
      'Document generation needs the user\'s own details. There is no fallback, ' +
      'because the fallback would be somebody else\'s name on their cover letter.'
    );
  }
  return id;
}

module.exports = { Document, Paragraph, TextRun, FONT, NAVY, r, p, link,
                   LETTER_PAGE, contactLine, requireIdentity };
