# Supabase 설정 (Free · 관리자 생성 계정)

프로젝트 `house`를 만든 뒤 아래 순서로 진행합니다. 비밀번호·secret key·실제 사용자 UUID는 채팅이나 Git 파일에 붙이지 마세요. 로그인 화면/코드는 공개, 공고 자료는 Supabase RLS로 허용된 계정만 읽습니다. 가족 소득/자녀 정보 저장 테이블은 없습니다.

## 1. 데이터베이스 보호부터 적용

Supabase Dashboard → SQL Editor → New query에서 [001_house.sql](../supabase/migrations/001_house.sql)의 전체 내용을 붙여 실행합니다. **새 house 전용 객체를 생성하는 1회용 migration**입니다. 이미 같은 객체가 있으면 중단하므로, 오류 때 표를 삭제하거나 RLS를 끄지 말고 확인하세요.

`public.house_snapshot`은 RLS가 켜져 있고 익명 권한은 없으며 로그인 계정도 기본 거부됩니다. `private.house_readers`의 UUID 허용 목록에 있는 계정만 SELECT할 수 있습니다. 브라우저는 INSERT/UPDATE/DELETE 권한이 없습니다. API 설정의 exposed schemas에 `private`를 추가하지 마세요.

## 2. 공개 가입 끄고 본인 앱 계정 만들기

Authentication → 설정/Sign In and Sign Up에서 **Allow new users to sign up**을 끕니다. Anonymous sign-ins도 꺼진 상태를 유지합니다. Email/password 로그인은 켭니다. Google/GitHub OAuth·SMTP를 추가할 필요는 없습니다.

Authentication → Users → Add user → **Create new user**를 선택합니다. **Send invitation**과 다릅니다. 본인 이메일과 새 앱 로그인 비밀번호를 직접 입력하고, 관리자 생성 계정을 이메일 확인 완료(Auto Confirm)로 만듭니다. 이는 Supabase Dashboard 로그인 비밀번호나 DB 비밀번호와 다른 앱 계정입니다. 비밀번호는 직접 안전하게 저장하세요.

기본 SMTP는 조직 팀원 주소에만 이메일을 보내며 현재 2통/시간 제한입니다. 따라서 외부 주소 초대/확인/비밀번호 재설정 이메일이 정상 도착한다고 가정하지 않습니다. 이 제약을 피하려고 배우자를 조직 관리자에 추가하지 마세요. 계정을 직접 생성하면 초대 메일에 의존하지 않고 로그인할 수 있습니다. 비밀번호 분실 시 관리자 제공 기능 또는 별도 승인된 SMTP 구성을 확인해야 하며, 이 앱에는 메일 복구 기능을 구현하지 않았습니다.

## 3. 본인 UUID를 허용 목록에 등록

Authentication → Users에서 방금 생성한 본인 계정의 **User UID/UUID**를 복사합니다. SQL Editor에서 아래 자리표시자를 **대시보드 안에서만** 바꾸어 실행합니다. 실제 UUID/이메일은 저장소·채팅에 넣지 마세요.

```sql
insert into private.house_readers (user_id)
values ('YOUR_AUTH_USER_UUID'::uuid)
on conflict (user_id) do nothing;
```

회원가입이나 로그인 성공 자체는 열람 권한이 아닙니다. 허용 목록에 없는 로그인 계정은 공고를 읽을 수 없습니다. 추가 사용자 허용은 별도 접근 권한 결정이므로 필요할 때 직접 진행합니다.

## 4. GitHub 공개 설정값과 서버 Secret 구분

프로젝트의 Connect/API Keys 화면에서 Project URL과 **publishable key (`sb_publishable_…`)**를 찾습니다. DB 비밀번호는 사용하지 않습니다. legacy anon JWT 대신 publishable key만 프런트 빌드가 허용합니다.

GitHub → `simonjisu/house` → Settings → Secrets and variables → Actions:

| 종류 | 이름 | 넣을 값 |
| --- | --- | --- |
| Variables | `SUPABASE_URL` | `https://프로젝트참조.supabase.co` (끝 `/` 없음) |
| Variables | `SUPABASE_PUBLISHABLE_KEY` | publishable key만. 브라우저에 공개되는 값 |
| Secrets | `SUPABASE_SECRET_KEY` | 프로젝트의 서버 secret key (`sb_secret_…`), 또는 기존 legacy service_role key |

**secret/service_role key는 RLS를 우회합니다.** 반드시 Actions **Secrets**에만 넣고 Variables, 프런트 코드, URL, 채팅에는 넣지 마세요. 코드가 새 key를 발급하지 않습니다. 본인이 Dashboard의 서버 key를 직접 확인/입력합니다. Supabase 개인 access token·DB 비밀번호·OAuth secret은 이 구성에 필요하지 않습니다.

## 5. 사이트 주소와 실행

Authentication → URL Configuration에서 Site URL을 `https://simonjisu.github.io/house/`로 설정합니다. 이메일/비밀번호 로그인은 현재 redirect 흐름을 쓰지 않습니다. 나중에 이메일 복구를 추가한다면 허용 Redirect URL도 이 정확한 주소로 제한하고 wildcard를 추가하지 마세요.

GitHub Actions → **Pages safe login UI** → Run workflow: 공개 설정값 두 개를 읽어 정적 로그인 UI를 빌드/배포합니다. 설정이 없으면 '설정 준비 중' 화면만 열리고 데이터는 잠긴 상태입니다.

GitHub Actions → **Daily official notices** → Run workflow: 기존 일일 수집을 즉시 한 번 실행하고 서버 Secret으로 `house_snapshot`에 자료를 올립니다. 매일 09:00 KST 스케줄은 하나만 유지합니다. 수집 자료를 Git 커밋/Pages 산출물에 넣지 않습니다.

## 6. 실제 권한 검증

1. 시크릿 창에서 페이지를 열면 공고가 보이지 않아야 합니다. Supabase API 직접 익명 요청도 표를 읽을 수 없어야 합니다.
2. 로그인했지만 allowlist에 없는 계정은 '열람 권한 없음'이어야 합니다.
3. 허용한 본인 계정으로 로그인하면 수집 자료가 보여야 합니다.
4. 로그아웃하면 공고와 브라우저 메모 입력이 즉시 지워져야 합니다. 새로고침하면 다시 로그인합니다.
5. 잘못된 비밀번호/네트워크 오류/설정 누락 때 공고 JSON fallback이 없어야 합니다.

계정 정보는 Supabase Auth에만 전송합니다. 세션은 브라우저 메모리만 사용하며 localStorage/sessionStorage에 저장하지 않습니다. 가족 소득 등 메모는 브라우저 화면에서만 사용하며 서버에 보내지 않습니다.

Free는 현재 DB 500MB, 월 활성 사용자 50,000명, egress 5GB 등 한도가 있고 1주 미사용 프로젝트는 일시 중지될 수 있습니다. 자동 유료 업그레이드/유료 플랜은 설정하지 않습니다. 실제 프로젝트 플랜/사용량은 Dashboard에서 확인하세요.

## 참고

- [RLS와 권한](https://supabase.com/docs/guides/database/postgres/row-level-security)
- [API key 구분](https://supabase.com/docs/guides/getting-started/api-keys)
- [기본 SMTP 제한](https://supabase.com/docs/guides/auth/auth-smtp)
- [가입 설정](https://supabase.com/docs/guides/auth/general-configuration)
- [Free 요금/한도](https://supabase.com/pricing)

Migration의 역할별 테스트는 `supabase/tests/house_rls.sql`이며 CI의 임시 Postgres에서 검증합니다. 실제 Supabase 프로젝트의 설정/정책/로그인 통합 검증은 위 값을 본인이 입력한 뒤 별도로 해야 합니다.
