import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';

const source=fs.readFileSync(new URL('../src/services.ts',import.meta.url),'utf8').replace('import.meta.env.VITE_API_URL',"''");
const js=ts.transpile(source,{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ES2022});
const local=new Map(),records=new Map();
globalThis.localStorage={getItem:key=>local.get(key)||null,setItem:(key,value)=>local.set(key,value),removeItem:key=>local.delete(key)};
globalThis.window={dispatchEvent:()=>{}};
Object.defineProperty(globalThis,'navigator',{value:{onLine:true},configurable:true});
// A transaction double exercises outbox decisions; real IndexedDB is separately checked in-browser.
globalThis.indexedDB={open(){const request={};queueMicrotask(()=>{request.result={close(){},transaction(){const tx={};tx.objectStore=()=>({getAll(){const req={result:[...records.values()].map(x=>structuredClone(x))};queueMicrotask(()=>tx.oncomplete?.());return req;},put(row){records.set(row.id,structuredClone(row));queueMicrotask(()=>tx.oncomplete?.());},delete(id){records.delete(id);queueMicrotask(()=>tx.oncomplete?.());}});return tx;}};request.onsuccess();});return request;}};
const service=await import('data:text/javascript;base64,'+Buffer.from(js).toString('base64'));
const phaseJS=ts.transpile(fs.readFileSync(new URL('../src/checkin.ts',import.meta.url),'utf8'),{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ES2022});
const {checkInPhase}=await import('data:text/javascript;base64,'+Buffer.from(phaseJS).toString('base64'));

test('deadline reconciliation covers near ETA, overdue and manual escalation',()=>{
 assert.equal(checkInPhase(1_000_000,0),'active');
 assert.equal(checkInPhase(100_000,0),'near_eta');
 assert.equal(checkInPhase(0,0),'overdue');
 assert.equal(checkInPhase(0,900_000),'manual_escalation');
});
test('outbox preserves blobs offline, retries stable keys, and retains conflicts',async()=>{
 records.clear(); const image=new File(['sample'],'test.jpg',{type:'image/jpeg'});
 await service.saveDraft({id:'stable-key',fields:{street:'Test'},image,state:'queued',updated:'now'});
 navigator.onLine=false; let calls=0;globalThis.fetch=async()=>{calls++;throw new Error('offline');};
 await service.syncDrafts();assert.equal(calls,0);assert.equal((await service.drafts())[0].image.size,6);
 navigator.onLine=true;const keys=[];
 globalThis.fetch=async(_url,init)=>{keys.push(init.headers['Idempotency-Key']);throw new Error('temporary network failure');};
 await service.syncDrafts();assert.equal((await service.drafts())[0].state,'queued');
 globalThis.fetch=async(_url,init)=>{keys.push(init.headers['Idempotency-Key']);return new Response(JSON.stringify({detail:'payload changed'}),{status:409});};
 await service.syncDrafts();assert.deepEqual(keys,['stable-key','stable-key']);assert.equal((await service.drafts())[0].state,'conflict');
 assert.equal((await service.drafts())[0].image.size,6);
 await service.saveDraft({...records.get('stable-key'),id:'new-revision',state:'queued'});
 globalThis.fetch=async()=>new Response(JSON.stringify({report:{id:'server-confirmed'}}),{status:200});
 await service.syncDrafts();assert.equal(records.get('new-revision').state,'synced');assert.equal(records.get('new-revision').image,undefined);assert.equal(records.get('stable-key').state,'conflict');
});
test('service worker excludes API, third parties and mutations; offline navigation uses shell',async()=>{
 const listeners={},cached=[];let offline=false;
 const context={URL,Promise,self:{location:{origin:'https://safepath.test'},clients:{claim:async()=>{}},skipWaiting(){},addEventListener:(name,fn)=>listeners[name]=fn},caches:{open:async()=>({addAll:async assets=>cached.push(...assets),match:async path=>'cached:'+path}),match:async path=>'cached:'+path,keys:async()=>['safepath-shell-v1','unrelated-cache'],delete:async name=>{assert.notEqual(name,'unrelated-cache');}},fetch:async()=>{if(offline)throw new Error('offline');return 'network';}};
 const code=fs.readFileSync(new URL('../dist/sw.js',import.meta.url),'utf8');vm.runInNewContext(code,context);
 let install;listeners.install({waitUntil:p=>install=p});await install;
 assert.ok(cached.includes('/index.html'));assert.ok(cached.some(p=>p.includes('MapPage')));
 for(const [url,method] of [['https://safepath.test/api/reports','GET'],['https://tile.openstreetmap.org/x.png','GET'],['https://safepath.test/api/report','POST']]){let intercepted=false;listeners.fetch({request:{url,method},respondWith:()=>intercepted=true});assert.equal(intercepted,false);}
 offline=true;let navigation;listeners.fetch({request:{url:'https://safepath.test/nested',method:'GET',mode:'navigate'},respondWith:p=>navigation=p});assert.equal(await navigation,'cached:/index.html');
});
test('manifest icons and all precache bundles exist',()=>{
 const manifest=JSON.parse(fs.readFileSync(new URL('../dist/manifest.webmanifest',import.meta.url),'utf8'));
 for(const icon of manifest.icons)assert.ok(fs.existsSync(new URL('../dist'+icon.src,import.meta.url)));
 const worker=fs.readFileSync(new URL('../dist/sw.js',import.meta.url),'utf8');assert.ok(!worker.includes('__PRECACHE__'));assert.ok(!worker.includes('__BUILD__'));
});
