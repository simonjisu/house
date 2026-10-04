begin;
-- Synthetic UUIDs and fixture payload only. Nothing leaves this temporary transaction.
insert into private.house_readers values ('00000000-0000-0000-0000-000000000001');
insert into public.house_snapshot (id,payload) values ('current','{"notices":[],"sources":{}}');
set local role anon;
do $$ begin
 begin perform * from public.house_snapshot; raise exception 'anon must be denied';
 exception when insufficient_privilege then null; end;
 begin perform public.house_can_read(); raise exception 'anon RPC must be denied';
 exception when insufficient_privilege then null; end;
end $$;
reset role;
set local role authenticated;
select set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000002',true);
do $$ begin
 if public.house_can_read() or (select count(*) from public.house_snapshot)<>0 then raise exception 'non-owner read'; end if;
 begin insert into public.house_snapshot values ('current','{}',now()); raise exception 'client write';
 exception when insufficient_privilege then null; end;
 begin select user_id from private.house_readers; raise exception 'allowlist leaked';
 exception when insufficient_privilege then null; end;
end $$;
reset role;
set local role authenticated;
select set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000001',true);
do $$ begin
 if not public.house_can_read() or (select count(*) from public.house_snapshot)<>1 then raise exception 'owner read denied'; end if;
 begin update public.house_snapshot set payload='{}'; raise exception 'owner client update';
 exception when insufficient_privilege then null; end;
 begin delete from public.house_snapshot; raise exception 'owner client delete';
 exception when insufficient_privilege then null; end;
end $$;
reset role;
set local role authenticated;
select set_config('request.jwt.claim.sub','',true);
do $$ begin
 if public.house_can_read() or (select count(*) from public.house_snapshot)<>0 then raise exception 'missing identity read'; end if;
end $$;
reset role;
set local role service_role;
update public.house_snapshot set payload='{"notices":[],"sources":{},"test":true}' where id='current';
reset role;
rollback;
