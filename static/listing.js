const el = (tag, props = {}) => Object.assign(document.createElement(tag), props);
const readableDate = value => /^\d{4}-\d{2}-\d{2}$/.test(value || '')
  ? new Date(value + 'T12:00:00').toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' }) : value;
function safeLink(value, email = false) {
  try { const u = new URL(value); return ['https:', 'http:', ...(email ? ['mailto:'] : [])].includes(u.protocol) ? value : ''; }
  catch { return ''; }
}
const postingType = i => i.posting_type || 'internship';
const typeLabel = i => postingType(i) === 'job' ? 'Job' : 'Internship';
function card(i) {
  const c = el('article', { className: 'card' });
  const h = el('h2', { textContent: i.title });
  h.append(el('span', { className: 'tag', textContent: typeLabel(i) }));
  if (i.category) h.append(el('span', { className: 'tag', textContent: i.category }));
  c.append(h, el('div', { className: 'meta', textContent: [i.faculty, i.department, i.centre].filter(Boolean).join(' · ') }));
  if (i.description) c.append(el('p', { className: 'prose', textContent: i.description }));
  const dl = el('dl');
  for (const [k, v] of [['Eligibility', i.eligibility], ['Duration', i.duration], ['Apply by', readableDate(i.deadline)]])
    if (v) dl.append(el('dt', { textContent: k }), el('dd', { textContent: v }));
  c.append(dl);
  const doc = safeLink(i.document_url);
  if (i.details || doc) {
    const details = el('details');
    details.append(el('summary', { textContent: 'Read more' }));
    details.addEventListener('toggle', () => details.firstChild.textContent = details.open ? 'Read less' : 'Read more');
    if (i.details) details.append(el('p', { className: 'prose', textContent: i.details }));
    if (doc) details.append(el('a', { href: doc, textContent: i.document_title || 'Supporting document', target: '_blank', rel: 'noopener' }));
    c.append(details);
  }
  const legacy = (i.apply_url || '').startsWith('mailto:');
  const email = i.application_method === 'email' ? i.apply_email : legacy ? i.apply_url.slice(7).split('?')[0] : '';
  const subject = i.email_subject || (legacy ? new URLSearchParams(i.apply_url.split('?')[1] || '').get('subject') : '') || 'Application: ' + i.title;
  const href = email ? 'mailto:' + encodeURIComponent(email).replace(/%40/g, '@') + '?subject=' + encodeURIComponent(subject) : safeLink(i.apply_url);
  if (href) {
    const actions = el('div', { className: 'card-actions' });
    actions.append(el('a', { className: 'apply', href, textContent: email ? 'Apply by email' : 'Apply', ...(email ? {} : { target: '_blank', rel: 'noopener' }) }));
    if (email) {
      const fallback = el('p', { className: 'hint', textContent: 'Email: ' + email });
      const copy = el('button', { type: 'button', className: 'ghost', textContent: 'Copy email' });
      copy.onclick = async () => {
        try { await navigator.clipboard.writeText(email); copy.textContent = 'Copied'; }
        catch { copy.textContent = 'Select the email above to copy'; }
      };
      actions.append(fallback, copy);
    }
    c.append(actions);
  }
  return c;
}
