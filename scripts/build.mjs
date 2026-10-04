import {build} from 'esbuild';
import {mkdir,readFile,writeFile,copyFile,rm,readdir} from 'node:fs/promises';
const url=process.env.SUPABASE_URL||'';
const key=process.env.SUPABASE_PUBLISHABLE_KEY||'';
if((url||key) && (!/^https:\/\/[a-z0-9]+\.supabase\.co$/.test(url)||!/^sb_publishable_[A-Za-z0-9_-]+$/.test(key)))throw Error('Only a valid project URL and publishable key can enter the build');
await rm('dist',{recursive:true,force:true});await mkdir('dist');
for(const f of ['index.html','style.css'])await copyFile('web/'+f,'dist/'+f);
await build({entryPoints:['web/app.js'],outfile:'dist/app.js',bundle:true,format:'esm',minify:true,sourcemap:false,platform:'browser'});
await writeFile('dist/config.json',JSON.stringify(url&&key?{url,publishableKey:key}:{}));
const allowed=['app.js','config.json','index.html','style.css'];
const files=(await readdir('dist')).sort();
if(JSON.stringify(files)!==JSON.stringify(allowed))throw Error('Unexpected public output');
for(const f of files){
 const content=await readFile('dist/'+f,'utf8');
 if(/sb_secret_[A-Za-z0-9_-]{10,}|-----BEGIN .*PRIVATE KEY-----|data\/notices\.json|2015122300020803|2015122300020859|310650|310653/.test(content))throw Error('Forbidden content in public output');
}
console.log('Safe static build:',files.length,'files; Supabase config:',url&&key?'present':'pending (fail closed)');
