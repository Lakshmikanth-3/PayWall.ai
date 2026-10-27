// PayWall bridge to the Meterless H-MEM reference engine. stdin: {"op":"recall","query":...} | {"op":"save",...}
import { HMEM } from './src/index.ts';

const dir = process.env.PAYWALL_HMEM_DIR ?? 'data/hmem';
const input = JSON.parse(await new Response(process.stdin as unknown as ReadableStream).text() || '{}');
const hmem = new HMEM({ persistDir: dir, actor: 'paywall-ai' });
if (input.op === 'recall') {
  const r = hmem.query(String(input.query ?? ''), { topN: Number(input.topN ?? 3), threshold: 0.05 });
  console.log(JSON.stringify({ memories: r.memories.map(m => ({ id: m.memory.id, content: m.memory.content, relevance: Math.round(m.relevance * 1000) / 1000 })), total: hmem.store.all().length }));
} else if (input.op === 'save') {
  const rec = hmem.add({ content: String(input.content), type: 'factual', layer: 'working', confidence: 0.7, tags: (input.tags ?? []).map(String), source: String(input.source ?? 'paywall-ai'), provenance: { origin: 'model_response', learnedAt: hmem.clock(), label: String(input.source ?? '') } });
  console.log(JSON.stringify({ id: rec.id, total: hmem.store.all().length }));
} else { console.error('op must be recall or save'); process.exit(2); }
