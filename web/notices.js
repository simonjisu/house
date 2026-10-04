export const TYPES=[
 {id:'sale',label:'분양 · 주택 구입',default:true},
 {id:'purchase-rental',label:'매입임대',default:false},
 {id:'long-jeonse',label:'장기전세',default:true},
 {id:'mirinae',label:'미리내집·연계형',default:true},
 {id:'national',label:'국민임대',default:false},
 {id:'permanent',label:'영구임대',default:false},
 {id:'integrated',label:'통합공공임대',default:false},
 {id:'public',label:'공공·재개발임대',default:false},
 {id:'happy',label:'행복·신혼희망',default:false},
 {id:'jeonse',label:'전세임대',default:false},
 {id:'deposit-support',label:'장기안심 (보증금 지원)',default:false},
 {id:'other',label:'기타·분류 확인 필요',default:false}
];
const normalized=n=>(n.title+' '+n.type).normalize('NFKC');
export function category(n){
 const t=normalized(n);
 if(t.includes('미리내집'))return 'mirinae';
 if(!t.includes('분양전환')&&(/공공분양|민간분양|분양주택|주택분양|분양아파트|분양 모집|분양공고/.test(t)||n.type==='분양'))return 'sale';
 if(t.includes('매입임대'))return 'purchase-rental';
 if(t.includes('장기전세'))return 'long-jeonse';
 if(t.includes('장기안심'))return 'deposit-support';
 if(t.includes('통합공공'))return 'integrated';
 if(t.includes('국민'))return 'national';
 if(t.includes('영구임대'))return 'permanent';
 if(t.includes('행복주택')||t.includes('신혼희망'))return 'happy';
 if(t.includes('전세임대'))return 'jeonse';
 if(t.includes('공공임대')||t.includes('재개발임대'))return 'public';
 return 'other';
}
export function subtype(n){
 const t=normalized(n);
 if(t.includes('공공한옥'))return '공공한옥';
 if(t.includes('든든전세'))return '든든전세';
 if(/신혼|신생아/.test(t)){
  if(/매입임대(?:주택)?\s*(?:II|2)(?![0-9])/.test(t))return '신혼·신생아 매입Ⅱ';
  if(/매입임대(?:주택)?\s*(?:I(?!I)|1)(?![0-9])/.test(t))return '신혼·신생아 매입Ⅰ';
  return '신혼·신생아 기타';
 }
 if(t.includes('청년'))return '청년';
 if(t.includes('고령자'))return '고령자';
 if(t.includes('다자녀'))return '다자녀';
 return '일반·기타 / 대상 확인';
}
export function dateKey(raw){
 const m=/^(\d{4})[.-](\d{1,2})[.-](\d{1,2})\.?$/.exec(String(raw||'').trim());
 if(!m)return null;
 const [y,mo,d]=m.slice(1).map(Number),dt=new Date(Date.UTC(y,mo-1,d));
 if(dt.getUTCFullYear()!==y||dt.getUTCMonth()!==mo-1||dt.getUTCDate()!==d)return null;
 return `${y}-${String(mo).padStart(2,'0')}-${String(d).padStart(2,'0')}`;
}
export const todayKST=()=>new Intl.DateTimeFormat('sv-SE',{timeZone:'Asia/Seoul'}).format(new Date());
export function closedReason(n,today=todayKST()){
 if(/마감|종료|취소/.test(n.status||''))return '공식 목록 '+n.status;
 if(dateKey(n.deadline)&&dateKey(n.deadline)<today)return '목록 마감일 지남 · 공식 상태 재확인';
 return null;
}
export function deadlineSort(a,b){
 const da=dateKey(a.deadline)||'9999-99-99',db=dateKey(b.deadline)||'9999-99-99';
 return da.localeCompare(db)||(dateKey(b.published)||'').localeCompare(dateKey(a.published)||'')||a.title.localeCompare(b.title,'ko');
}
export function selectNotices(notices,filters,today=todayKST()){
 return notices.filter(n=>filters.types.includes(category(n))&&
 (!filters.region||n.region.includes(filters.region))&&
 (!filters.subtype||subtype(n)===filters.subtype)&&
 (!filters.audience||(n.audience||[]).includes(filters.audience))&&
 (!filters.query||n.title.includes(filters.query.trim()))&&
 (filters.includeClosed||!closedReason(n,today))&&
 (!filters.income||(filters.income==='unknown'?n.eligibility!=='reviewed':n.eligibility==='reviewed'))&&
 (!filters.ratio||n.eligibility!=='reviewed'||!n.income||n.income.maxPercent>({70:0,100:70,120:100,140:120,200:140}[filters.ratio]))
 ).sort(deadlineSort);
}

export function publicationTone(n,today=todayKST()){
 const date=dateKey(n.published);if(!date)return 'unknown';
 const days=Math.max(0,Math.round((Date.parse(today)-Date.parse(date))/86400000));
 return days<=7?'new':days<=30?'recent':days<=90?'older':'old';
}
