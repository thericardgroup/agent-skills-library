// Cover letter generator. Everything personal comes from profile.json.
const fs = require('fs');
const path = require('path');
const { Packer } = require('docx');
const { Document, Paragraph, r, p, LETTER_PAGE, NAVY, FONT,
        contactLine, requireIdentity } = require('./common');
const { loadProfile } = require('./state');

function letter(cfg, profile) {
  const id = requireIdentity(profile);
  const signoff = id.signature || id.name;
  return new Document({
    styles: { default: { document: { run: { font: FONT, size: 21 } } } },
    sections: [{
      properties: { page: LETTER_PAGE },
      children: [
        new Paragraph({ spacing: { after: 20 },
          children: [r(id.name, { bold: true, size: 28, color: NAVY })] }),
        new Paragraph({ spacing: { after: 240 }, children: contactLine(id) }),
        p([r(cfg.date, { size: 20, color: '444444' })], { after: 200 }),
        p([r(`Re: ${cfg.title}`, { bold: true })], { after: 40 }),
        p([r(cfg.company, { bold: true })], { after: 200 }),
        ...cfg.letter.map((t) => p([r(t)], { after: 160 })),
        p([r(signoff)], { before: 200, after: 0 }),
      ],
    }],
  });
}


async function writeLetter(cfg, outPath, profile, opts) {
  const { authorize } = require('./authorize');
  const { rec, profile: effective } = authorize({
    key: (opts || {}).key || (opts || {})._gated,
    contents: [{ label: 'letter', cfg }],
    profile, profilePath: (opts || {}).profilePath,
  });
  const buf = await Packer.toBuffer(letter(cfg, effective));
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, buf);
  return { path: outPath, bytes: buf.length };
}

// No CLI here on purpose. A document written through a standalone entry point
// carries no requisition identity, no approval evidence and no digest, so it
// cannot be audited afterwards -- and an unauditable deliverable is exactly
// what the manifest exists to prevent. scripts/docgen/package.js is the only
// supported way to produce one; these functions are its internals.
module.exports = { letter, writeLetter };

