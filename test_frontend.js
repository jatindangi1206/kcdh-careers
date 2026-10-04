// Dependency-free checks for rendering and session-expiry preservation: node test_frontend.js
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
class Element {
  constructor(tag = 'div') { this.tag = tag; this.children = []; this.value = ''; this.hidden = false; this.events = {}; }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  get firstChild() { return this.children[0]; }
  addEventListener(name, fn) { this.events[name] = fn; }
  reset() {}
  reportValidity() { return true; }
  scrollIntoView() {}
  focus() {}
  removeAttribute(name) { delete this[name]; }
  querySelectorAll() { return []; }
}
const elements = {};
const context = vm.createContext({
  document: { createElement: tag => new Element(tag), getElementById: id => elements[id] ||= new Element() },
  URL, URLSearchParams, navigator: {}, window: { addEventListener() {} }, confirm: () => true,
  fetch: async url => ({ ok: true, json: async () => url === '/api/config' ? { today: '2026-10-04', maintainer_email: 'help@example.edu' } : { authed: false } }),
});
vm.runInContext(fs.readFileSync('static/listing.js', 'utf8'), context);
const run = code => vm.runInContext(code, context);
const posting = { title: '<script>literal title</script>', deadline: '2027-03-15', description: 'Summary',
  details: 'Paragraph one\n\nParagraph two', document_url: 'https://example.edu/brief.pdf',
  application_method: 'email', apply_email: 'staff@example.edu', email_subject: 'Application: A & B' };
context.posting = posting;
const card = run('card(posting)');
assert.equal(card.firstChild.textContent, posting.title);
assert.equal(card.firstChild.firstChild.textContent, 'Internship');
assert.equal(run("card({...posting, posting_type:'job'}).firstChild.firstChild.textContent"), 'Job');
const details = card.children.find(c => c.tag === 'details');
assert.equal(details.children[1].textContent, posting.details);
assert.equal(details.firstChild.textContent, 'Read more');
details.open = true; details.events.toggle(); assert.equal(details.firstChild.textContent, 'Read less');
assert.equal(card.children.at(-1).className, 'card-actions', 'Apply stays below expandable details');
const href = card.children.at(-1).firstChild.href;
assert.equal(new URL(href).pathname, posting.apply_email);
assert.equal(new URL(href).searchParams.get('subject'), posting.email_subject);
assert.equal(run("safeLink('javascript:alert(1)')"), '');
assert.equal(run("card({title:'x', deadline:'2027-03-15'}).children.some(c => c.tag === 'details')"), false);
const admin = fs.readFileSync('static/admin.html', 'utf8');
const source = admin.match(/<script>([\s\S]*?)<\/script>/)[1];
run(source);
(async () => {
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(elements.contact.href, 'mailto:help@example.edu');
  run("$('application_method').value = 'email'; methodFields()");
  assert.equal(elements['url-fields'].hidden, true);
  assert.equal(elements.apply_url.disabled, true);
  assert.equal(elements.apply_email.required, true);
  run("fill({...posting, id:'example'})");
  assert.equal(elements.posting_type.value, 'internship');
  run("fill({...posting, id:'job', posting_type:'job'})");
  assert.equal(elements.posting_type.value, 'job');
  run("$('title').value = 'Unsaved draft'; dirty = true");
  context.fetch = async () => ({ ok: false, status: 401, json: async () => ({ error: 'Please sign in.' }) });
  await assert.rejects(run("api('PUT', '/api/internships/example', {})"));
  assert.equal(elements.title.value, 'Unsaved draft');
  assert.equal(elements.login.hidden, false);
  assert.equal(elements.panel.hidden, true);
  assert.match(elements.loginerr.textContent, /preserved/);
  assert.equal(run('dirty'), true);
  run('pending = true');
  assert.equal(run('discard()'), false, 'Cannot switch editor while saving');
  run("pending = false; items = [{title:'Old internship', deadline:'2027-03-15'}, {title:'New job', deadline:'2027-03-15', posting_type:'job'}]; $('filter').value = 'active'; $('type-filter').value = 'job'; render()");
  assert.equal(elements.list.children.length, 1);
  assert.equal(elements.list.firstChild.firstChild.firstChild.textContent, 'New job');
  run("$('type-filter').value = 'internship'; render()");
  assert.equal(elements.list.firstChild.firstChild.firstChild.textContent, 'Old internship');
  const publicElements = {};
  const publicContext = vm.createContext({
    document: { createElement: tag => new Element(tag), getElementById: id => publicElements[id] ||= new Element() },
    URL, URLSearchParams, navigator: {},
    fetch: async () => ({ok:true, json: async () => [{title:'Old internship', deadline:'2027-03-15'}, {title:'New job', posting_type:'job', deadline:'2027-03-15'}]}),
  });
  vm.runInContext(fs.readFileSync('static/listing.js', 'utf8'), publicContext);
  vm.runInContext(fs.readFileSync('static/index.html', 'utf8').match(/<script>([\s\S]*?)<\/script>/)[1], publicContext);
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(publicElements.list.children.length, 2);
  publicElements.type.value = 'job'; publicElements.type.events.change();
  assert.equal(publicElements.list.children.length, 1);
  assert.equal(publicElements.list.firstChild.firstChild.textContent, 'New job');
  assert.equal(publicElements.status.textContent, '1 open opportunity');
  publicElements.type.value = 'internship'; publicElements.type.events.change();
  assert.equal(publicElements.list.firstChild.firstChild.textContent, 'Old internship');
  publicElements.clear.onclick();
  assert.equal(publicElements.list.children.length, 2);
  console.log('frontend ok');
})().catch(error => { console.error(error); process.exitCode = 1; });
