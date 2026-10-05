// Resume generator. Employment history comes from profile.json and is never
// rewritten -- only the summary, headline and skills change per role. Facts stay
// fixed; emphasis moves. A generator that edits history is a generator that
// invents it.
const fs = require('fs');
const path = require('path');
const { Packer, AlignmentType, BorderStyle } = require('docx');
const { Document, Paragraph, r, p, link, FONT, NAVY,
        contactLine, requireIdentity } = require('./common');
const { loadProfile } = require('./state');

const PAGE = { size: { width: 12240, height: 15840 },
               margin: { top: 720, bottom: 720, left: 900, right: 900 } };

const rule = () => new Paragraph({
  spacing: { before: 120, after: 80 },
  border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: NAVY } },
});

const heading = (text) => new Paragraph({
  spacing: { before: 160, after: 40 },
  children: [r(text.toUpperCase(), { bold: true, size: 22, color: NAVY })],
});

function bulletList(items) {
  return items.map((t) => new Paragraph({
    bullet: { level: 0 }, spacing: { after: 40 }, children: [r(t, { size: 20 })],
  }));
}

function roleBlock(job) {
  const out = [new Paragraph({
    spacing: { before: 120, after: 0 },
    children: [
      r(job.title, { bold: true, size: 21 }),
      r(`   ${job.employer}`, { size: 21 }),
      r(`   ${job.dates || ''}`, { size: 19, color: '555555' }),
    ],
  })];
  if (job.scope) {
    out.push(p([r(job.scope, { size: 19, italics: true, color: '444444' })], { after: 40 }));
  }
  return out.concat(bulletList(job.bullets || []));
}

function resume(cfg, profile) {
  const id = requireIdentity(profile);
  const res = profile.resume || {};
  const experience = res.experience || [];
  if (!experience.length) {
    throw new Error(
      'profile.resume.experience is empty. There is nothing to generate.\n' +
      'Run the onboarding interview; Step 2 builds the timeline.');
  }

  const children = [
    new Paragraph({ spacing: { after: 20 }, alignment: AlignmentType.CENTER,
      children: [r(id.name, { bold: true, size: 30, color: NAVY })] }),
    new Paragraph({ spacing: { after: 60 }, alignment: AlignmentType.CENTER,
      children: contactLine(id) }),
  ];

  // Per-role tailoring. These three are the only things that move.
  if (cfg.headline) {
    children.push(new Paragraph({ spacing: { after: 80 }, alignment: AlignmentType.CENTER,
      children: [r(cfg.headline, { bold: true, size: 22 })] }));
  }
  children.push(rule());
  if (cfg.summary) {
    children.push(heading('Summary'));
    children.push(p([r(cfg.summary, { size: 20 })], { after: 80 }));
  }
  if (cfg.skills && cfg.skills.length) {
    children.push(heading('Skills'));
    children.push(p([r(cfg.skills.join('  |  '), { size: 20 })], { after: 80 }));
  }

  // Fixed history.
  children.push(heading('Experience'));
  experience.forEach((job) => children.push(...roleBlock(job)));

  if ((res.earlier_experience || []).length) {
    children.push(heading('Earlier Experience'));
    children.push(...bulletList(res.earlier_experience));
  }
  if ((res.education || []).length) {
    children.push(heading('Education'));
    children.push(...bulletList(res.education));
  }

  return new Document({
    styles: { default: { document: { run: { font: FONT, size: 20 } } } },
    sections: [{ properties: { page: PAGE }, children }],
  });
}


async function writeResume(cfg, outPath, profile, opts) {
  const { authorize } = require('./authorize');
  const { rec, profile: effective } = authorize({
    key: (opts || {}).key || (opts || {})._gated,
    contents: [{ label: 'resume', cfg }],
    profile, profilePath: (opts || {}).profilePath,
  });
  const prof = effective;
  const buf = await Packer.toBuffer(resume(cfg, prof));

  // Assert before publishing, not after. Writing first and checking second
  // left a failed document on disk, which is the single most likely thing to
  // get sent by mistake -- it looks finished.
  const { assertResume } = require('./check');
  await assertResume(buf, path.basename(outPath), prof);

  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, buf);
  return { path: outPath, bytes: buf.length };
}

// No CLI here on purpose. A document written through a standalone entry point
// carries no requisition identity, no approval evidence and no digest, so it
// cannot be audited afterwards -- and an unauditable deliverable is exactly
// what the manifest exists to prevent. scripts/docgen/package.js is the only
// supported way to produce one; these functions are its internals.
module.exports = { resume, writeResume };

