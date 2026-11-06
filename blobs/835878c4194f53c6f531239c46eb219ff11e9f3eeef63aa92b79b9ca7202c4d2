// Read-only compiled-module normalization. Only the Python guard removes the
// exact reviewed fallback statements; this helper never removes game code.
const fs=require('node:fs');
const terser=require(process.argv[2]);
(async()=>{
 const [a,b]=JSON.parse(fs.readFileSync(0,'utf8'));
 const options={compress:{passes:3},mangle:{toplevel:true},format:{comments:false}};
 const [x,y]=await Promise.all([terser.minify(a,options),terser.minify(b,options)]);
 const crypto=require('node:crypto');const sha=s=>crypto.createHash('sha256').update(s).digest('hex');
 process.stdout.write(JSON.stringify({equal:x.code===y.code,before_canonical_sha256:sha(x.code),after_canonical_sha256:sha(y.code),normalizer:'Creator 3.8.8 bundled terser, exact hide removal then compress/mangle'}));
})().catch(e=>{process.stderr.write(String(e));process.exitCode=1});
