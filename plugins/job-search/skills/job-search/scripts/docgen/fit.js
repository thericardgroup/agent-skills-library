// Fit summary. Never submitted -- this is the document the user reads before an
// interview, and the one place in the pipeline where the honest answer lives.
//
// Markdown rather than docx on purpose: it is read on screen, pasted into notes,
// and edited. A .docx would make it feel like something to send.
const fs = require('fs');
const path = require('path');
const { loadProfile } = require('./state');

function fitSummary(cfg, profile) {
  const id = profile.identity || {};
  const L = [];
  const verdictLine = {
    apply: 'APPLY',
    stretch: 'APPLY — stretch, go in knowing that',
    no: 'DO NOT APPLY',
  }[cfg.verdict] || cfg.verdict;

  L.push(`# ${cfg.title} — ${cfg.company}`, '');
  L.push(`**${verdictLine}**`, '');
  if (cfg.verdict_because) L.push(cfg.verdict_because, '');
  L.push(`Requisition: \`${cfg.key || 'unverified'}\``);
  if (cfg.apply_url) L.push(`Apply: ${cfg.apply_url}`);
  L.push('');

  if ((cfg.requirements || []).length) {
    L.push('## Requirements, as stated', '');
    L.push('| Requirement | Have it? | Evidence or gap |');
    L.push('|---|---|---|');
    cfg.requirements.forEach((q) => {
      const mark = { yes: 'Yes', partial: 'Partly', no: 'No' }[q.status] || q.status;
      L.push(`| ${q.text} | ${mark} | ${q.note || ''} |`);
    });
    L.push('');
  }

  const hard = (cfg.requirements || []).filter((q) => q.status === 'no' && q.required);
  if (hard.length) {
    L.push('## Stated minimums not met', '');
    hard.forEach((q) => L.push(`- **${q.text}** — ${q.note || 'no evidence in the profile'}`));
    L.push('');
    L.push(hard.length === 1
      ? 'One stated minimum missed. That is usually a no, however good the rest looks.'
      : `${hard.length} stated minimums missed. This is a no.`);
    L.push('');
  }

  if ((cfg.gaps || []).length) {
    L.push('## Gaps, and what to say about each', '');
    cfg.gaps.forEach((g) => {
      L.push(`**${g.name}**`, '');
      L.push(`> ${g.say}`, '');
    });
  }

  if ((cfg.stories || []).length) {
    L.push('## Lead with these', '');
    cfg.stories.forEach((s) => L.push(`- ${s}`));
    L.push('');
  }

  if ((cfg.questions || []).length) {
    L.push('## Ask them', '');
    cfg.questions.forEach((q) => L.push(`- ${q}`));
    L.push('');
  }

  L.push('## Before submitting', '');
  const checks = cfg.checklist || [
    'Verification is current — the gate refuses otherwise',
    'Cover letter only if the form actually accepts one',
    'Text fields pasted and re-read in the form, not just in the document',
    'Salary expectation stated as a range you would accept the bottom of',
  ];
  checks.forEach((c) => L.push(`- [ ] ${c}`));
  L.push('');
  L.push('---', '', `Prepared for ${id.name || 'this candidate'} · not for submission`);
  return L.join('\n');
}


async function writeFit(cfg, outPath, profile, opts) {
  const { authorize } = require('./authorize');
  const { rec, profile: effective } = authorize({
    key: (opts || {}).key || (opts || {})._gated,
    contents: [{ label: 'fit', cfg }],
    profile, profilePath: (opts || {}).profilePath,
  });
  const prof = effective;
  const text = fitSummary(cfg, prof);
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, text, 'utf8');
  return { path: outPath, bytes: Buffer.byteLength(text) };
}

module.exports = { fitSummary, writeFit };

if (require.main === module) {
  const [cfgPath, outPath, key] = process.argv.slice(2);
  if (!cfgPath || !outPath || !key) {
    console.error('usage: node fit.js <fit-config.json> <output.md> <requisition-key>');
    process.exit(2);
  }
  writeFit(JSON.parse(fs.readFileSync(cfgPath, 'utf8')), outPath, null, { key })
    .then((res) => console.log(`   wrote ${res.path} (${res.bytes} bytes)`))
    .catch((e) => { console.error(e.message); process.exit(1); });
}
