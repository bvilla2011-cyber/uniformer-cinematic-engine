const {createCanvas}=require('@napi-rs/canvas');const fs=require('fs');
const path=require('path'); const {pathToFileURL}=require('url'); const root=path.resolve(process.argv[2]||'../Super-Soccer'); const out=path.resolve(process.argv[3]||'output/gameframes');
(async()=>{global.window={devicePixelRatio:1};global.document={createElement:()=>createCanvas(1,1)};global.ResizeObserver=class{observe(){} disconnect(){}};
const {createCareer}=await import(pathToFileURL(path.join(root,'src/career.js')).href);const {MatchSimulation}=await import(pathToFileURL(path.join(root,'src/match.js')).href);const {Renderer}=await import(pathToFileURL(path.join(root,'src/render.js')).href);
let w=createCareer({seed:20261114});let home=w.teams.find(t=>t.id==='es-2'),away=w.teams.find(t=>t.id==='es-1');away.colors=['#f3ce79','#242939'];
let g=new MatchSimulation({home,away,fixtureId:'marketing-capture',duration:180,seed:42});let c=createCanvas(1280,800);c.getBoundingClientRect=()=>({width:1280,height:800});let r=new Renderer(c,{quality:'high'});
fs.mkdirSync(out,{recursive:true});for(let i=0;i<300;i++)g.update(1/30);
for(let i=0;i<450;i++){g.update(1/30);r.draw(g,1/30);fs.writeFileSync(path.join(out,`${String(i).padStart(5,'0')}.png`),c.toBuffer('image/png'));}
fs.writeFileSync(path.join(out,'capture.json'),JSON.stringify({home:home.name,away:away.name,source:'Super-Soccer/src/match.js + src/render.js',seed:42}));})();
