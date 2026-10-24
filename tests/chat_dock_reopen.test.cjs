const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const source = fs.readFileSync(path.join(__dirname, '..', 'static', 'app.js'), 'utf8');
const start = source.indexOf('async function renderGlobalProducerChat(');
const end = source.indexOf('async function applyProducerUiActions(', start);
const implementation = source.slice(start, end);

test('closing and reopening dock preserves a live progress card and its connection', async () => {
  const elements = new Map();
  const element = id => {
    if (!elements.has(id)) elements.set(id, { classList: { toggle() {}, add() {}, remove() {} }, focus() {} });
    return elements.get(id);
  };
  const messages = element('#globalCodexMessages');
  messages.innerHTML = '<div id="globalCodexThinking">LIVE timeline</div>';
  const state = { globalCodexOpen: true, chatRunConnections: { globalCodexThinking: true }, globalCodexAttachments: [], appTab: 'overview' };
  const context = {
    state, $: element, document: { body: { classList: { toggle() {}, add() {}, remove() {} } } },
    api: async () => [{ role: 'user', content: 'history' }],
    producerChatHistoryUrl: () => '/history',
    producerChatMessagesHtml: () => '<div>history replaced live card</div>',
    refreshGlobalCodexContext: async () => {},
    renderPendingChatAttachments() {},
    resumeStoredProducerChatRun() {},
    localStorage: { setItem() {} },
  };
  vm.runInNewContext(implementation + '; this.renderGlobalProducerChat = renderGlobalProducerChat;', context);

  await context.renderGlobalProducerChat({ loadHistory: true });
  element('#globalCodexCloseBtn').onclick();
  await element('#globalCodexToggle').onclick();

  assert.match(messages.innerHTML, /LIVE timeline/);
  assert.equal(state.chatRunConnections.globalCodexThinking, true);
});
