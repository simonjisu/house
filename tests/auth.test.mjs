import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readProtectedSnapshot,validConfig} from '../web/auth.js';
const payload={notices:[],sources:{}};
function fake({signedIn=true,allowed=true,rpcError=null,data=payload,dataError=null}={}){
 let reads=0;
 return {auth:{getUser:async()=>({data:{user:signedIn?{id:'synthetic-test-user'}:null}})},rpc:async()=>({data:allowed,error:rpcError}),from:()=>{reads++;return{select:()=>({eq:()=>({maybeSingle:async()=>({data:data?{payload:data}:null,error:dataError})})})}},reads:()=>reads};
}
test('missing/secret/malformed configuration fails closed',()=>{
 for(const c of [null,{}, {url:'https://wrong.invalid',publishableKey:'sb_publishable_test'},{url:'https://fixture.supabase.co',publishableKey:'sb_secret_fixture'}])assert.equal(validConfig(c),false);
 assert.equal(validConfig({url:'https://fixture.supabase.co',publishableKey:'sb_publishable_fixture'}),true);
});
test('signed out never reads protected table',async()=>{const c=fake({signedIn:false});assert.equal((await readProtectedSnapshot(c)).state,'signed-out');assert.equal(c.reads(),0);});
test('signed in but not allowed never reads table',async()=>{const c=fake({allowed:false});assert.equal((await readProtectedSnapshot(c)).state,'denied');assert.equal(c.reads(),0);});
test('allowlisted account receives validated snapshot',async()=>{assert.deepEqual(await readProtectedSnapshot(fake()),{state:'ready',payload});});
test('authorization and data errors reveal no payload',async()=>{
 assert.deepEqual(await readProtectedSnapshot(fake({rpcError:{}})),{state:'error'});
 assert.deepEqual(await readProtectedSnapshot(fake({dataError:{}})),{state:'error'});
 assert.deepEqual(await readProtectedSnapshot(fake({data:{privateValue:'synthetic'}})),{state:'error'});
});
test('authorized empty database is explicit',async()=>{assert.deepEqual(await readProtectedSnapshot(fake({data:null})),{state:'empty'});});
