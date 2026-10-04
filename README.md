# house

서울·경기 LH/SH 주택 공고를 살펴보는 모바일 웹앱. **정적 로그인 UI/코드는 공개, 공고 데이터는 Supabase Auth + RLS + 명시적 UUID 허용 목록으로 보호합니다.**

## Supabase 설정

[한국어 설정 가이드](docs/SUPABASE_SETUP.ko.md) · [1회용 migration](supabase/migrations/001_house.sql)

프로젝트는 사용자가 직접 만들고 계정/키/접근 권한을 설정합니다. 설정값이 없으면 데이터 접근이 잠긴 '준비 중' 화면만 나타납니다. 실제 Supabase 로그인/호스팅 통합은 프로젝트 설정 후 별도 검증해야 합니다.

- GitHub Variables: `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`
- GitHub Actions Secret: `SUPABASE_SECRET_KEY` (server-only; RLS bypass 권한)
- 관리자 생성 Email/password 계정, 공개 가입 비활성화, `private.house_readers`에 허용 UUID 등록
- DB 비밀번호/secret key/실제 UUID/개인정보를 Git·채팅·로그에 넣지 않습니다.

## 실행과 일일 수집

```sh
npm ci
npm test
npm run build
python3 -m http.server 8765 --bind 127.0.0.1 --directory dist
```

로컬에서 프로젝트 공개 설정값을 환경변수로 지정하지 않았다면 로그인은 비활성화됩니다. 프런트는 publishable key만 허용하고 secret/legacy JWT key는 빌드에서 거부합니다.

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/collect.py
```

수집 결과는 Git에서 제외된 `runtime/notices.json`에만 생깁니다. `Daily official notices`는 기존 하루 한 번(09:00 KST) 스케줄을 유지하며, 설정된 서버 Secret으로 이전 정상 자료를 읽어 소스별 실패를 보존한 뒤 Supabase snapshot에 저장합니다. 공고 데이터 Git 커밋·Pages 업로드·공개 JSON fallback 없음. 설정이 없는 동안 수집은 실행하되 DB 전송은 보류됩니다.

`Pages safe login UI`는 `dist`의 HTML/CSS/번들JS/공개config 네 파일만 배포합니다. 로그인 화면에 넣은 계정/비밀번호는 Supabase Auth로만 전송합니다. 로그인 세션은 브라우저 메모리만 사용하므로 새로고침하면 다시 로그인합니다.

## 수집 범위·자격 정보

- LH 공식 청약플러스 HTML: 최근 60일 임대/매입/전세임대, 서울·경기·전국 행, 100행×최대5페이지.
- SH 서울시 공식 공공임대 미러: 최대10페이지. SH 원문 직접 수집하지 않고 원문 `seq`를 안정 식별자로 사용.
- robots를 먼저 확인하고 차단/확인 실패 시 중단. LH 첨부 다운로드/로그인/대기열 우회 없음. 공식 API는 key 미발급으로 미사용.
- 제외: GH 등 다른 기관, LH 분양/토지/상가, SH 분양/기타 공지, 첨부파일.
- 소득표 검토 0건. 모든 공고 소득은 unknown. 비율 구간 선택으로 미확인 공고를 제외하지 않습니다. 제목 키워드는 자격 판정이 아닙니다.
- 신혼/자녀/소득/자산/자동차/거주/혼인 기준은 공고별 원문과 첨부로 확인해야 합니다. 목록 마감일과 접수시각을 구별하며 접수시각은 미확인.
- 중복 ID, 해시 변경 이력, 범위에서 사라짐, 소스 오류, 36시간 stale 표시. 사라짐을 취소로 단정하지 않습니다.

가족의 실제 소득·자녀 정보를 저장하는 테이블은 없습니다. 브라우저 메모는 저장·서버 전송하지 않습니다.

## 검증 및 공개 전 감사

Git 전체 이력의 17개 blob, Actions 로그 2건에서 비밀키/개인 연락처 패턴 매치 0. 초기 공고 snapshot은 공식 메타데이터임을 확인했습니다. 공개화 전에 `web/data/notices.json`을 전체 Git 이력에서 제거하고 로컬 bundle 복구본을 Mac에만 남겼습니다. Actions 공개 산출물에 수집 JSON을 넣지 않습니다.

- Python 수집기 테스트 4개
- Node 인증 경계/설정 누락/오류/허용 및 거부 테스트 6개
- 임시 PostgreSQL에서 실제 grants/RLS: 익명 거부, 비허용 계정 0행, 허용 계정 읽기, 클라이언트 쓰기 거부, 서버 역할 업데이트 검증
- build는 허용 네 파일만 만들며 secret key/공고 JSON/특정 실공고 식별자 혼입을 거부

테스트의 합성 계정/UUID/HTML은 시험 데이터입니다. 실 Supabase 프로젝트의 정책/가입설정/계정과는 별도입니다.

## 정책

서울시 [저작권 정책](https://www.seoul.go.kr/helper/copyright.do)은 공공누리 미표시 자료 이용 시 사전 협의를 안내합니다. 공고명/일자/상태/원문 링크 등 메타데이터만 취급하고 원문/첨부를 재게시하지 않습니다. 공고별 소득표 검토와 재이용 범위 확인은 남은 작업입니다.
