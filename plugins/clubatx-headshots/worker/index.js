const tool = {
  name: 'create_headshot',
  description: 'Create a transparent PNG headshot with a black shirt using ClubAtx POST /v1/images/headshot. Requests preservation of identity, face and hair, but generative editing can introduce small changes. Source must be PNG, JPEG or WebP up to 10 MB in the configured Vercel Blob store. Supplying athlete_slug REPLACES that athlete profile photo: only include it when the user requested a profile update. Without athlete_slug only a new file is saved. Do not retry automatically: generation creates a new file and incurs processing. On 409/500 preserve returned PNG metadata and explain whether the profile update was unconfirmed.',
  inputSchema: { type: 'object', properties: {
    source_url: {type:'string', maxLength:2048, description:'Direct HTTPS image URL in the configured Vercel Blob store, no query or fragment.'},
    athlete_slug: {type:'string', maxLength:100, pattern:'^[a-z0-9]+(?:-[a-z0-9]+)*$', description:'Athlete profile to update. If source_url omitted, uses current photo.'}
  }, anyOf:[{required:['source_url']},{required:['athlete_slug']}], additionalProperties:false },
  annotations: {readOnlyHint:false, destructiveHint:true, idempotentHint:false, openWorldHint:true}
};
const statusTool = { name:'headshot_connection_status', description:'Check whether the ClubAtx API credential is configured, without processing images or exposing secrets.', inputSchema:{type:'object',properties:{},additionalProperties:false}, annotations:{readOnlyHint:true,openWorldHint:false} };
const content = (data, isError=false) => ({content:[{type:'text',text:JSON.stringify(data)}],isError});
export default {async fetch(request,env) {
 const path=new URL(request.url).pathname;
 if(path!='/mcp') return new Response('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>ClubAtx Headshots</title><body style="font:18px system-ui;max-width:650px;margin:10vh auto;padding:24px"><h1>ClubAtx Headshots</h1><p>Create transparent PNG athlete headshots with a black shirt from your ClubAtx images.</p><p>Connect the ClubAtx Headshots plugin in ChatGPT. Provide an image URL, or request an athlete profile photo update by slug.</p><p>Setup: configure the private runtime secret <code>CLUBATX_API_KEY</code> with a ClubAtx <code>read_write</code> API key.</p><p>Source images must be PNG, JPEG or WebP, up to 10 MB, in the configured Vercel Blob store. Image editing may introduce small changes to facial details.</p></body></html>',{headers:{'content-type':'text/html; charset=utf-8'}});
 if(request.method!=='POST') return new Response('Method not allowed',{status:405,headers:{Allow:'POST'}});
 let rpc; try{rpc=await request.json()}catch{return Response.json({jsonrpc:'2.0',id:null,error:{code:-32700,message:'Parse error'}})}
 if(!rpc||typeof rpc!=='object'||Array.isArray(rpc)||typeof rpc.method!=='string')return Response.json({jsonrpc:'2.0',id:null,error:{code:-32600,message:'Invalid Request'}});
 const reply=result=>Response.json({jsonrpc:'2.0',id:rpc.id??null,result});
 if(rpc.method==='server/discover') return reply({supportedVersions:['2026-07-28'],capabilities:{tools:{}}});
 if(rpc.method==='initialize') return reply({protocolVersion:'2026-07-28',serverInfo:{name:'clubatx-headshots',version:'0.1.0'},capabilities:{tools:{}}});
 if(rpc.method?.startsWith('notifications/'))return new Response(null,{status:202});
 if(rpc.method==='tools/list')return reply({tools:[tool,statusTool]});
 if(rpc.method!=='tools/call')return Response.json({jsonrpc:'2.0',id:rpc.id??null,error:{code:-32601,message:'Method not found'}});
 if(rpc.params?.name==='headshot_connection_status')return reply(content({configured:!!env.CLUBATX_API_KEY,endpoint:'https://api.clubathletix.com/v1/images/headshot'}));
 if(rpc.params?.name!=='create_headshot')return reply(content({error:'Unknown tool'},true));
 const a=rpc.params.arguments??{};
 if(!a||typeof a!=='object'||Array.isArray(a)||Object.keys(a).some(k=>!['source_url','athlete_slug'].includes(k))||(!a.source_url&&!a.athlete_slug))return reply(content({error:'Supply source_url or athlete_slug'},true));
 if(a.athlete_slug!==undefined&&(typeof a.athlete_slug!=='string'||a.athlete_slug.length>100||!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(a.athlete_slug)))return reply(content({error:'Invalid athlete_slug'},true));
 if(a.source_url!==undefined){try{const u=new URL(a.source_url);if(typeof a.source_url!=='string'||a.source_url.length>2048||u.protocol!=='https:'||! /^[a-z0-9]+\.(public|private)\.blob\.vercel-storage\.com$/.test(u.hostname)||u.search||u.hash||u.port||u.username||u.password)throw Error()}catch{return reply(content({error:'Invalid direct HTTPS Vercel Blob source_url'},true))}}
 if(!env.CLUBATX_API_KEY)return reply(content({error:'Configure the private CLUBATX_API_KEY runtime secret with a read_write ClubAtx API key.'},true));
 try{
 const res=await fetch('https://api.clubathletix.com/v1/images/headshot',{method:'POST',headers:{authorization:`Bearer ${env.CLUBATX_API_KEY}`,'content-type':'application/json'},body:JSON.stringify(a),signal:AbortSignal.timeout(290000),redirect:'error'});
 let data;try{data=await res.json()}catch{return reply(content({status:res.status,error:'ClubAtx returned an unreadable response. Outcome unknown; do not retry automatically.'},true))}
 return reply(content({status:res.status,...data},!res.ok));
 }catch{return reply(content({error:'ClubAtx request failed or timed out. Outcome unknown; check for an existing result before retrying.'},true))}
}};
