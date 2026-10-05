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

module.exports = { letter, writeLetter };

if (require.main === module) {
  const [cfgPath, outPath, key] = process.argv.slice(2);
  if (!cfgPath || !outPath || !key) {
    console.error('usage: node letter.js <letter-config.json> <output.docx> <requisition-key>\n' +
      '  config: { "date", "title", "company", "letter": ["para", ...] }');
    process.exit(2);
  }
  writeLetter(JSON.parse(fs.readFileSync(cfgPath, 'utf8')), outPath, null, { key })
    .then((res) => console.log(`   wrote ${res.path} (${res.bytes} bytes)`))
    .catch((e) => { console.error(e.message); process.exit(1); });
}
