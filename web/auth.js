import {createClient} from '@supabase/supabase-js';
export function validConfig(config){
 return !!config && /^https:\/\/[a-z0-9]+\.supabase\.co$/.test(config.url||'') && /^sb_publishable_[A-Za-z0-9_-]+$/.test(config.publishableKey||'');
}
export function authClient(config){
 if(!validConfig(config))return null;
 return createClient(config.url,config.publishableKey,{auth:{persistSession:false,autoRefreshToken:true,detectSessionInUrl:false}});
}
export async function readProtectedSnapshot(client){
 const {data:user,error:userError}=await client.auth.getUser();
 if(userError||!user?.user) return {state:'signed-out'};
 const access=await client.rpc('house_can_read');
 if(access.error) return {state:'error'};
 if(access.data!==true)return {state:'denied'};
 const result=await client.from('house_snapshot').select('payload').eq('id','current').maybeSingle();
 if(result.error)return {state:'error'};
 if(!result.data)return {state:'empty'};
 const payload=result.data.payload;
 if(!payload||!Array.isArray(payload.notices)||!payload.sources)return {state:'error'};
 return {state:'ready',payload};
}
