import {authClient,readProtectedSnapshot} from './auth.js';
import {TYPES,category,subtype,dateKey,todayKST,closedReason,selectNotices,publicationTone} from './notices.js';
const $=id=>document.getElementById(id);
let data;
const node=(tag,content,className)=>{const n=document.createElement(tag);n.textContent=content;if(className)n.className=className;return n;};
const age=date=>!date||Date.now()-Date.parse(date)>36*60*60*1000;
const stamp=date=>date?new Date(date).toLocaleString('ko-KR',{timeZone:'Asia/Seoul'})+' KST':'정상 수집 기록 없음';
const selectedTypes=()=>[...document.querySelectorAll('.type-choice input:checked')].map(n=>n.value);
function updateSubtypes(){
 const previous=$('subtype').value,types=selectedTypes();
 $('subtype').replaceChildren(node('option','세부 구분 전체'));$('subtype').firstChild.value='';
 for(const value of [...new Set(data.notices.filter(n=>types.includes(category(n))).map(subtype))].sort())$('subtype').append(node('option',value));
 if([...$('subtype').options].some(o=>o.value===previous))$('subtype').value=previous;
 $('detailFilters').hidden=!types.length;
}
function resetFilters(){
 for(const input of document.querySelectorAll('.type-choice input'))input.checked=TYPES.find(t=>t.id===input.value).default;
 for(const id of ['region','subtype','audience','query','income','ratio','localIncome','supplyTrack'])$(id).value='';
 $('includeClosed').checked=false;updateSubtypes();render();
}
function officialLink(n,label){
 try{const url=new URL(n.url);if(url.protocol==='https:'&&['apply.lh.or.kr','www.i-sh.co.kr','www.applyhome.co.kr','applyhome.co.kr'].includes(url.hostname)){const a=node('a',label,'link');a.href=url.href;a.target='_blank';a.rel='noopener noreferrer';return a;}}catch{}
 return node('span','원문 주소 확인 필요');
}
function noticeRow(n,today){
 const reason=closedReason(n,today),card=node('article','','tone-'+publicationTone(n,today)+(reason?' closed-item':'')),date=node('div','','deadline'),key=dateKey(n.deadline);
 date.append(node('span',n.deadlineMeaning?.startsWith('특별공급')?'특공 마감':'목록 마감','deadline-label'));
 if(key){date.append(node('strong',key.slice(5).replace('-','.')),node('span',key.slice(0,4),'deadline-year'));if(!reason){const days=Math.round((Date.parse(key)-Date.parse(today))/86400000);date.append(node('span',days===0?'오늘 · 시각 확인':'D−'+days,'remaining'));}}
 else date.append(node('strong','미확인','unknown'));
 const body=node('div','','row-main'),meta=node('div','','row-meta');meta.append(node('span','공고일 '+(dateKey(n.published)||'미확인'),'published'),node('span',n.source,'source'),node('span',n.region),node('span',n.status||'상태 미확인','status'));
 const heading=node('h3',''),title=officialLink(n,n.title);title.className='';heading.append(title);
 const actions=node('div','','row-actions');actions.append(node('span',TYPES.find(t=>t.id===category(n)).label+' · '+subtype(n),'program'),officialLink(n,'원문 ↗'));
 body.append(meta,heading,actions);
 if(reason)body.append(node('p',reason,'warning'));
 if(age(n.checkedAt)||!data.sources[n.feed||n.source]?.ok)body.append(node('p','수집 지연 · 이전 정상 자료, 원문 재확인','warning'));
 if(n.missingFromLatest)body.append(node('p','최신 수집 범위에 없음 · 상태 확인 필요','warning'));
 if(n.changes?.length)body.append(node('p','목록 변경 '+n.changes.length+'회 · 원문 확인','warning'));
 const detail=node('details','','item-detail');detail.append(node('summary','게시일 · 근거 · 자격 확인'),node('p','게시일 '+(n.published||'미확인')+' · 공식 유형 '+n.type),node('p',(n.evidence||'목록 근거')+' · 소득구간 미확인 · 지원 후보, 자격 확인 필요'),node('p','마지막 확인 '+stamp(n.checkedAt)+' · 접수시각은 원문 확인'));
 if(n.applicationWindows){const windows=n.applicationWindows;detail.append(node('p','전체 접수: '+(windows.RCEPT_BGNDE||'미확인')+' ~ '+(windows.RCEPT_ENDDE||'미확인')),node('p','특별공급: '+(windows.SPSPLY_RCEPT_BGNDE||'미확인')+' ~ '+(windows.SPSPLY_RCEPT_ENDDE||'미확인')));for(const rank of [1,2])for(const [code,label] of [['CRSPAREA','해당지역'],['ETC_GG','기타 경기'],['ETC_AREA','기타지역']]){const prefix='GNRL_RNK'+rank+'_'+code;detail.append(node('p','일반 '+rank+'순위 '+label+': '+(windows[prefix+'_RCPTDE']||'미확인')+' ~ '+(windows[prefix+'_ENDDE']||'미확인')));}detail.append(node('p','특공 구분: '+((n.specialTracks||[]).join(' · ')||'배정 유형 미확인')+' · 배정 수는 자격 확정이 아닙니다. 민영 신생아 우선공급은 원문 확인'));}
 body.append(detail);card.append(date,body);return card;
}
function render(){
 const types=selectedTypes(),filters={types};for(const id of ['region','subtype','audience','query','income','ratio','supplyTrack'])filters[id]=$(id).value;
 filters.includeClosed=$('includeClosed').checked;
 const today=todayKST(),selected=selectNotices(data.notices,filters,today),active=selected.filter(n=>!closedReason(n,today)),closed=selected.filter(n=>closedReason(n,today));
 $('count').textContent=active.length+'건'+(closed.length?' · 마감·지난 날짜 '+closed.length+'건':'');
 $('filterSummary').textContent=types.length?TYPES.filter(t=>types.includes(t.id)).map(t=>t.label).join(' · ')+(filters.supplyTrack?' / '+$('supplyTrack').selectedOptions[0].textContent:'')+(filters.region?' / '+filters.region:'')+(filters.subtype?' / '+filters.subtype:'')+(filters.audience?' / '+filters.audience:'')+(filters.query?' / 검색: '+filters.query:'')+(filters.income?' / 소득 '+(filters.income==='unknown'?'미확인':'검토 완료'):'')+(filters.ratio?' / 소득 '+filters.ratio+'% 구간':''):'선택한 주택 유형이 없습니다.';
 $('cards').replaceChildren(...active.map(n=>noticeRow(n,today)));
 $('closedCards').replaceChildren(...closed.map(n=>noticeRow(n,today)));$('closedSection').hidden=!closed.length;
 if(!active.length){const empty=node('div','','empty');empty.append(node('p',types.length?'선택한 조건에 맞는 진행 중 공고가 없습니다. 유형이나 세부 조건을 넓혀 보세요.':'위에서 주택 유형을 하나 이상 선택하세요.'));const reset=node('button','기본 조건으로 보기');reset.addEventListener('click',resetFilters);empty.append(reset);$('cards').append(empty);}
}
let client=null,epoch=0;
function clearData(){
 epoch++;data=null;$('protectedContent').hidden=true;$('cards').replaceChildren();$('closedCards').replaceChildren();$('count').textContent='';$('health').replaceChildren();$('filterSummary').textContent='';$('loginPanel').classList.remove('ready');
 $('localIncome').value='';$('query').value='';
}
async function refresh(){
 clearData();const current=epoch;$('authStatus').textContent='접근 권한 확인 중…';
 const result=await readProtectedSnapshot(client).catch(()=>({state:'error'}));if(current!==epoch)return;
 $('logoutButton').hidden=result.state==='signed-out';$('loginForm').hidden=result.state!=='signed-out';
 const states={'signed-out':'로그인 후 공고를 확인하세요.','denied':'이 계정은 공고 열람 권한이 없습니다. 관리자에게 확인하세요.','error':'데이터를 확인하지 못했습니다. 로그아웃 후 다시 시도하거나 관리자에게 문의하세요.','empty':'로그인과 권한 확인은 완료됐지만 아직 수집 자료가 없습니다.'};
 if(result.state!=='ready'){$('authStatus').textContent=states[result.state]||states.error;return;}
 data=result.payload;$('authStatus').textContent='로그인 · 열람 권한 확인 완료';$('loginPanel').classList.add('ready');$('protectedContent').hidden=false;
 for(const [name,s] of Object.entries(data.sources))$('health').append(node('p',name+' · '+(s.state==='unconnected'?'미연결 · API 키 미설정':s.ok&&!age(s.lastSuccess)?'수집 정상':'수집 지연')+' · 마지막 정상 '+stamp(s.lastSuccess)+' · '+(s.scope?.query||'수집 범위 미확인')+' · 페이지 상한 '+(s.scope?.pageCap||'?')+' · 범위 내 완료 '+(s.scope?.completeWithinQuery?'예':'미확인')));
 updateSubtypes();render();
}
async function init(){
 for(const type of TYPES){const label=node('label','','type-choice'),input=document.createElement('input');input.type='checkbox';input.value=type.id;input.checked=type.default;input.addEventListener('change',()=>{if(data){updateSubtypes();render();}});label.append(input,node('span',type.label));$(type.default?'primaryTypeOptions':'otherTypeOptions').append(label);}
 $('resetFilters').addEventListener('click',resetFilters);
 for(const id of ['region','subtype','audience','income','ratio','query','includeClosed','supplyTrack'])$(id).addEventListener('input',()=>{if(data)render();});
 try{const response=await fetch('config.json',{cache:'no-store'});client=authClient(await response.json());}catch{}
 if(!client){clearData();$('authStatus').textContent='Supabase 설정 준비 중입니다. 데이터 접근은 잠겨 있습니다.';return;}
 client.auth.onAuthStateChange(event=>{if(event==='SIGNED_OUT'){clearData();$('logoutButton').hidden=true;$('loginForm').hidden=false;$('authStatus').textContent='로그아웃했습니다.';}else if(event==='SIGNED_IN'||event==='TOKEN_REFRESHED')setTimeout(()=>refresh(),0);});
 $('loginForm').addEventListener('submit',async event=>{event.preventDefault();clearData();$('loginButton').disabled=true;$('authStatus').textContent='로그인 중…';try{const result=await client.auth.signInWithPassword({email:$('email').value.trim(),password:$('password').value});if(result.error)$('authStatus').textContent='로그인하지 못했습니다. 계정과 비밀번호를 확인하세요.';}catch{$('authStatus').textContent='로그인 서버에 연결하지 못했습니다.';}finally{$('password').value='';$('loginButton').disabled=false;}});
 $('logoutButton').addEventListener('click',async()=>{clearData();$('logoutButton').hidden=true;$('loginForm').hidden=false;$('email').value='';$('password').value='';try{await client.auth.signOut({scope:'local'});}catch{}$('authStatus').textContent='화면의 데이터를 지웠습니다. 로그아웃했습니다.';});
 await refresh();
}
init();
