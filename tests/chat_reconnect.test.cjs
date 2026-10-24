const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '..', 'static', 'app.js'), 'utf8');
const begin = source.indexOf('async function connectProducerChatRun(');
const end = source.indexOf('\nasync function streamProducerChat(', begin);
assert.ok(begin >= 0 && end > begin);
const functionSource = source.slice(begin, end);

test('page reload resumes from the last saved event and serves new script version', () => {
  const html = fs.readFileSync(path.join(__dirname, '..', 'static', 'index.html'), 'utf8');
  assert.match(source, /connectProducerChatRun\(stored\.runId,[\s\S]*?Number\(stored\.seq \|\| 0\)\)/);
  assert.match(html, /app\.js\?v=20260913-chat-reconnect/);
});

function stream(chunks) {
  let index = 0;
  return {
    ok: true,
    body: {
      getReader() {
        return {
          async read() {
            const item = chunks[index++];
            if (item instanceof Error) throw item;
            return item ?? { done: true };
          },
        };
      },
    },
  };
}

function eventChunk(event) {
  return { done: false, value: Buffer.from(JSON.stringify(event) + '\n') };
}

function subject({ responses, status }) {
  const requests = [];
  const saved = [];
  const cleared = [];
  const notices = [];
  const context = {
    fetch: async url => {
      requests.push(url);
      const next = responses.shift();
      if (next instanceof Error) throw next;
      return next;
    },
    api: async () => status,
    document: { getElementById: () => ({}) },
    TextDecoder,
    Uint8Array,
    setTimeout: callback => callback(),
    storeChatRun: value => saved.push(value),
    clearStoredChatRun: value => cleared.push(value),
    renderChatLiveProgress: (...args) => notices.push(args),
    summarizeChatCliEvent: () => null,
    encodeURIComponent,
    Error,
    Promise,
  };
  vm.runInNewContext(functionSource + '\nthis.connect = connectProducerChatRun;', context);
  return { connect: context.connect, requests, saved, cleared, notices };
}

test('resumes the same run after a stream read failure without posting again', async () => {
  const result = { reply: 'đã xong', history: [] };
  const first = stream([eventChunk({ type: 'started', seq: 1 }), new Error('network error')]);
  const second = stream([eventChunk({ type: 'result', seq: 2, result })]);
  const app = subject({ responses: [first, second], status: { status: 'running' } });
  const actual = await app.connect('chat-123', { selected_job_id: 'job-1' }, 'thinking', {}, 'gemini');
  assert.equal(actual.reply, 'đã xong');
  assert.deepEqual(app.requests, [
    '/api/producer-chat/runs/chat-123/events?after=0',
    '/api/producer-chat/runs/chat-123/events?after=1',
  ]);
  assert.equal(app.cleared.length, 1);
  assert.ok(app.notices.some(item => String(item[3]).includes('reconnecting')));
});

test('returns persisted result when stream disconnects after server finishes', async () => {
  const result = { reply: 'kết quả đã lưu', history: [] };
  const app = subject({ responses: [new Error('network error')], status: { status: 'succeeded', result } });
  const actual = await app.connect('chat-456', {}, 'thinking', {}, 'gemini');
  assert.equal(actual.reply, 'kết quả đã lưu');
  assert.deepEqual(app.requests, ['/api/producer-chat/runs/chat-456/events?after=0']);
  assert.equal(app.cleared.length, 1);
});

test('reports persisted terminal failure rather than a generic network error', async () => {
  const app = subject({ responses: [new Error('network error')], status: { status: 'failed', error: 'Phiên AI bị gián đoạn' } });
  await assert.rejects(app.connect('chat-789', {}, 'thinking', {}, 'gemini'), /Phiên AI bị gián đoạn/);
});
