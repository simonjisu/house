import {authClient,readProtectedSnapshot} from './auth.js';
'use strict';
const $ = id => document.getElementById(id);
let data;
const node = (tag, content, className) => { const n=document.createElement(tag); n.textContent=content; if(className)n.className=className; return n; };
const age = date => !date || Date.now()-Date.parse(date)>36*60*60*1000;
const stamp = date => date ? new Date(date).toLocaleString('ko-KR',{timeZone:'Asia/Seoul'})+' KST' : '정상 수집 기록 없음';
function render(){
 const selected=data.notices.filter(n => (! $('region').value || n.region.includes($('region').value)) &&
  (!$('type').value || n.type===$('type').value) && (!$('audience').value || n.audience.includes($('audience').value)) &&
  (!$('query').value || n.title.includes($('query').value)) &&
  (!$('ratio').value || n.eligibility!=='reviewed' || !n.income || n.income.maxPercent>({70:0,100:70,120:100,140:120,200:140}[$('ratio').value])) &&
  (!$('income').value || ($('income').value==='unknown' ? n.eligibility!=='reviewed' : n.eligibility==='reviewed')));
 $('count').textContent=selected.length+'건'; $('cards').replaceChildren();
 for(const n of selected){
  const card=node('article',''); const tags=node('div','','tags');
  for(const t of [n.source,n.region,n.type,n.status]) tags.append(node('span',t,'tag'));
  card.append(tags,node('h3',n.title),node('p','지원 후보 · 자격 확인 필요','warn'));
  if(age(n.checkedAt)||!data.sources[n.source]?.ok) card.append(node('p','수집 지연 / 이전 정상 자료입니다. 원문 재확인','warn'));
  if(n.missingFromLatest) card.append(node('p','최신 수집 범위에 없음 · 마감/취소 여부 확인 필요','warn'));
  if(n.changes?.length) card.append(node('p','목록 내용 변경 '+n.changes.length+'회 · 정정 여부 원문 확인','warn'));
  card.append(node('p','게시일 '+n.published+(n.deadline ? ' · 목록 마감일 '+n.deadline+' (접수시각 미확인)' : ' · 접수기간 미확인'),'meta'),
   node('p',n.evidence+' · 소득구간 미확인','meta'),node('p','마지막 확인 '+stamp(n.checkedAt),'meta'));
  const link=node('a','공식 원문 확인 ↗','link');
  const url=new URL(n.url);
  if(url.protocol==='https:' && ['apply.lh.or.kr','www.i-sh.co.kr'].includes(url.hostname)){link.href=url.href;link.target='_blank';link.rel='noopener noreferrer';card.append(link);}
  $('cards').append(card);
 }
 if(!selected.length) $('cards').append(node('p','조건에 맞는 공고가 없습니다. 필터를 넓히거나 공식 목록을 확인하세요.','empty'));
}
let client=null, epoch=0;
function clearData(){
 epoch++; data=null; $('protectedContent').hidden=true; $('cards').replaceChildren(); $('count').textContent=''; $('health').replaceChildren();
 $('localIncome').value=''; $('query').value='';
}
async function refresh(){
 clearData(); const current=epoch;
 $('authStatus').textContent='접근 권한 확인 중…';
 const result=await readProtectedSnapshot(client).catch(()=>({state:'error'}));
 if(current!==epoch)return;
 $('logoutButton').hidden=result.state==='signed-out';
 $('loginForm').hidden=result.state!=='signed-out';
 const states={'signed-out':'로그인 후 공고를 확인하세요.','denied':'이 계정은 공고 열람 권한이 없습니다. 관리자에게 확인하세요.','error':'데이터를 확인하지 못했습니다. 로그아웃 후 다시 시도하거나 관리자에게 문의하세요.','empty':'로그인과 권한 확인은 완료됐지만 아직 수집 자료가 없습니다.'};
 if(result.state!=='ready'){$('authStatus').textContent=states[result.state]||states.error;return;}
 data=result.payload; $('authStatus').textContent='로그인 · 열람 권한 확인 완료'; $('protectedContent').hidden=false;
 data.notices.sort((a,b)=>b.published.replaceAll('.', '-').localeCompare(a.published.replaceAll('.', '-')));
 for(const [name,s] of Object.entries(data.sources)) $('health').append(node('p',name+' · '+(s.ok&&!age(s.lastSuccess)?'수집 정상':'수집 지연')+' · 마지막 정상 '+stamp(s.lastSuccess)+' · '+(s.scope?.query||'수집 범위 미확인')+' · 페이지 상한 '+(s.scope?.pageCap||'?')+' · 범위 내 완료 '+(s.scope?.completeWithinQuery?'예':'미확인'),s.ok?'':'warn'));
 $('type').replaceChildren(node('option','모든 유형'));$('type').firstChild.value='';
 for(const type of [...new Set(data.notices.map(n=>n.type))].sort())$('type').append(node('option',type));
 render();
}
async function init(){
 for(const id of ['region','type','audience','income','ratio','query'])$(id).addEventListener('input',()=>{if(data)render();});
 try{const response=await fetch('config.json',{cache:'no-store'});client=authClient(await response.json());}catch{}
 if(!client){clearData();$('authStatus').textContent='Supabase 설정 준비 중입니다. 데이터 접근은 잠겨 있습니다.';return;}
 client.auth.onAuthStateChange((event)=>{
  if(event==='SIGNED_OUT'){clearData();$('logoutButton').hidden=true;$('loginForm').hidden=false;$('authStatus').textContent='로그아웃했습니다.';}
  else if(event==='SIGNED_IN'||event==='TOKEN_REFRESHED')setTimeout(()=>refresh(),0);
 });
 $('loginForm').addEventListener('submit',async event=>{
  event.preventDefault();clearData();$('loginButton').disabled=true;
  $('authStatus').textContent='로그인 중…';
  try{const result=await client.auth.signInWithPassword({email:$('email').value.trim(),password:$('password').value});
   if(result.error)$('authStatus').textContent='로그인하지 못했습니다. 계정과 비밀번호를 확인하세요.';
  }catch{$('authStatus').textContent='로그인 서버에 연결하지 못했습니다.';}
  finally{$('password').value='';$('loginButton').disabled=false;}
 });
 $('logoutButton').addEventListener('click',async()=>{
  clearData();$('logoutButton').hidden=true;$('loginForm').hidden=false;$('email').value='';$('password').value='';
  try{await client.auth.signOut({scope:'local'});}catch{}
  $('authStatus').textContent='화면의 데이터를 지웠습니다. 로그아웃했습니다.';
 });
 await refresh();
}
init();
