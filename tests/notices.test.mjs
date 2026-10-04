import test from 'node:test';
import assert from 'node:assert/strict';
import {TYPES,category,subtype,dateKey,closedReason,selectNotices,publicationTone} from '../web/notices.js';
const row=(title,extra={})=>({title,type:'매입임대',region:'서울',audience:['신혼'],status:'모집중',eligibility:'unknown',...extra});
const defaults=TYPES.filter(t=>t.default).map(t=>t.id);
const base={types:[...defaults,'purchase-rental']};
test('defaults distinguish named programs and deposit support',()=>{
 assert.deepEqual(defaults,['sale','long-jeonse','mirinae']);
 assert.equal(category(row('도시형 매입임대',{type:'도시형생활주택'})),'purchase-rental');
 assert.equal(category(row('장기전세 II (미리내집) 공고',{type:'장기전세'})),'mirinae');
 assert.equal(category(row('장기전세 공고',{type:'장기전세'})),'long-jeonse');
 assert.equal(category(row('장기안심 공고',{type:'장기안심주택'})),'deposit-support');
 assert.equal(category(row('행복주택 공고',{type:'행복주택'})),'happy');
 assert.equal(category(row('희망하우징',{type:'희망하우징'})),'other');
});
test('subtypes use explicit names and normalize Roman numerals',()=>{
 assert.equal(subtype(row('신혼·신생아 매입임대주택Ⅱ 공고')),'신혼·신생아 매입Ⅱ');
 assert.equal(subtype(row('신혼 매입임대I 공고')),'신혼·신생아 매입Ⅰ');
 assert.equal(subtype(row('든든전세 모집')),'든든전세');
 assert.equal(subtype(row('공공한옥 미리내집')),'공공한옥');
});
test('strict calendar dates and closure respect KST date including today',()=>{
 assert.equal(dateKey('2026.10.4.'),'2026-10-04');assert.equal(dateKey('2026-02-30'),null);assert.equal(dateKey('접수중'),null);
 assert.equal(closedReason(row('today',{deadline:'2026-10-04'}),'2026-10-04'),null);
 assert.match(closedReason(row('past',{deadline:'2026-10-03'}),'2026-10-04'),/지남/);
 assert.match(closedReason(row('cancel',{status:'취소',deadline:'2026-10-15'}),'2026-10-04'),/공식/);
 assert.equal(closedReason(row('unknown'), '2026-10-04'),null);
});
test('deadline ascending, unknown last, past hidden unless enabled',()=>{
 const notices=[row('unknown',{published:'2026.10.04'}),row('later',{deadline:'2026.10.15'}),row('past',{deadline:'2026.10.03'}),row('today',{deadline:'2026.10.04'})];
 assert.deepEqual(selectNotices(notices,base,'2026-10-04').map(n=>n.title),['today','later','unknown']);
 assert.deepEqual(selectNotices(notices,{...base,includeClosed:true},'2026-10-04').map(n=>n.title),['past','today','later','unknown']);
});
test('multi-select and dependent filters combine while retaining unknown income',()=>{
 const notices=[row('청년 매입임대'),row('신혼 매입임대Ⅱ'),row('신혼 장기전세',{type:'장기전세',region:'경기'}),row('신혼 행복주택',{type:'행복주택'})];
 assert.equal(selectNotices(notices,base).length,3);
 assert.equal(selectNotices(notices,{...base,region:'서울',subtype:'신혼·신생아 매입Ⅱ',audience:'신혼',ratio:'140'}).length,1);
 assert.equal(selectNotices(notices,{...base,income:'reviewed'}).length,0);
 assert.equal(selectNotices(notices,{types:[]}).length,0);
 assert.equal(selectNotices(notices,{...base,query:'없는 단지'}).length,0);
});

test('sales are distinct from purchase rental and rental conversion',()=>{
 assert.equal(category(row('공공분양 신혼 특별공급',{type:'공공분양'})),'sale');
 assert.equal(category(row('국민임대 특별공급',{type:'국민임대'})),'national');
 assert.equal(category(row('분양전환 공공임대',{type:'공공임대'})),'public');
 assert.equal(publicationTone(row('new',{published:'2026-10-01'}),'2026-10-04'),'new');
 assert.equal(publicationTone(row('old',{published:'2025-01-01'}),'2026-10-04'),'old');
 assert.equal(publicationTone(row('unknown'),'2026-10-04'),'unknown');
});
