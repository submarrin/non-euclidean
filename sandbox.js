/* Hyperbolic sandbox: ruler-and-compass constructions in the Poincaré disk,
   with a view of the same figure in the upper half-plane.
   Points are stored as complex numbers in the disk |z| < 1. Every
   construction is done by moving one point to the centre with a disk
   isometry, where hyperbolic lines through 0 are diameters, and mapping back. */
(function(){
"use strict";

/* ---------------- complex numbers ---------------- */
const C = (x,y)=>({x:x,y:y});
const add=(a,b)=>C(a.x+b.x,a.y+b.y), sub=(a,b)=>C(a.x-b.x,a.y-b.y);
const mul=(a,b)=>C(a.x*b.x-a.y*b.y,a.x*b.y+a.y*b.x);
const conj=a=>C(a.x,-a.y), abs=a=>Math.hypot(a.x,a.y), scl=(a,s)=>C(a.x*s,a.y*s);
const div=(a,b)=>{const d=b.x*b.x+b.y*b.y; return C((a.x*b.x+a.y*b.y)/d,(a.y*b.x-a.x*b.y)/d);};
const ONE=C(1,0), I=C(0,1);
const toO =(p,z)=>div(sub(z,p),sub(ONE,mul(conj(p),z)));   // isometry sending p to 0
const from0=(p,z)=>div(add(z,p),add(ONE,mul(conj(p),z)));  // inverse: 0 to p

/* ---------------- hyperbolic measurements ---------------- */
function hdist(a,b){ const r=Math.min(abs(toO(a,b)),0.999999999); return 2*Math.atanh(r); }
function hangle(v,a,b){ // angle at v between the lines va and vb, in degrees
  const u=toO(v,a), w=toO(v,b);
  let t=Math.abs(Math.atan2(u.y,u.x)-Math.atan2(w.y,w.x));
  if(t>Math.PI) t=2*Math.PI-t;
  return t*180/Math.PI;
}
function segmentPts(a,b,n){ const t=toO(a,b), pts=[]; for(let k=0;k<=n;k++) pts.push(from0(a,scl(t,k/n))); return pts; }
function linePts(a,b,n){
  const t=toO(a,b), L=abs(t); if(L<1e-12) return [];
  const u=scl(t,1/L), pts=[];
  for(let k=0;k<=n;k++){ const s=-1+2*k/n; pts.push(from0(a,scl(u,Math.sign(s)*Math.pow(Math.abs(s),0.6)))); }
  return pts;
}
function circlePts(c,p,n){ const r=abs(toO(c,p)), pts=[]; for(let k=0;k<=n;k++){ const t=2*Math.PI*k/n; pts.push(from0(c,C(r*Math.cos(t),r*Math.sin(t)))); } return pts; }
// point at hyperbolic distance d from p in the direction of the unit vector dir (as seen at p)
function along(p,dir,d){ return from0(p,scl(dir,Math.tanh(d/2))); }

/* ---------------- model views ---------------- */
const toH  =w=>div(mul(I,add(ONE,w)),sub(ONE,w));   // Cayley map disk → upper half-plane
const fromH=z=>div(sub(z,I),add(z,I));

function mount(root, opts){
  opts = opts || {};
  const canvas=root.querySelector("canvas"), ctx=canvas.getContext("2d");
  const out=root.querySelector("[data-readout]");
  let model="disk", tool="move", sel=[], objs=[], pts=[], drag=null, nextLabel=0, W=0, H=0, dpr=1, hover=null;

  function label(){ const L="ABCDEFGHIJKLMNOPQRSTUVWXYZ"; const n=nextLabel++; return L[n%26]+(n>=26?Math.floor(n/26):""); }
  function newPoint(z,name){ const p={z:z,name:name||label()}; pts.push(p); return p; }

  /* coordinates */
  function geom(){ // disk: centre & radius; half-plane: origin & scale
    if(model==="disk"){ const R=Math.min(W,H)/2-14; return {cx:W/2,cy:H/2,R:R}; }
    const S=W/6; return {ox:W/2, oy:H-28, S:S};
  }
  function toScreen(w){
    const g=geom();
    if(model==="disk") return {x:g.cx+g.R*w.x, y:g.cy-g.R*w.y};
    const z=toH(w); return {x:g.ox+g.S*z.x, y:g.oy-g.S*z.y};
  }
  function toModel(x,y){
    const g=geom();
    if(model==="disk"){ let w=C((x-g.cx)/g.R,(g.cy-y)/g.R); const r=abs(w); if(r>0.985) w=scl(w,0.985/r); return w; }
    let z=C((x-g.ox)/g.S,Math.max(0.03,(g.oy-y)/g.S)); let w=fromH(z); const r=abs(w); if(r>0.985) w=scl(w,0.985/r); return w;
  }

  /* drawing */
  function css(v){ return getComputedStyle(root).getPropertyValue(v).trim() || "#333"; }
  function poly(list, close){
    ctx.beginPath(); let prev=null;
    list.forEach(function(w){
      const p=toScreen(w);
      if(!isFinite(p.x)||!isFinite(p.y)){ prev=null; return; }
      if(prev && Math.hypot(p.x-prev.x,p.y-prev.y)>Math.max(W,H)) ctx.moveTo(p.x,p.y);
      else if(prev) ctx.lineTo(p.x,p.y); else ctx.moveTo(p.x,p.y);
      prev=p;
    });
    if(close) ctx.closePath();
  }
  function draw(){
    if(W<10){ readout(); return; }
    const ink=css("--fig-1"), acc=css("--fig-2"), soft=css("--fig-3"), fill=css("--fig-fill"), sheet=css("--sheet");
    ctx.setTransform(dpr,0,0,dpr,0,0); ctx.clearRect(0,0,W,H);
    const g=geom();
    ctx.save();
    if(model==="disk"){
      ctx.beginPath(); ctx.arc(g.cx,g.cy,g.R,0,2*Math.PI); ctx.fillStyle=fill; ctx.fill();
      ctx.lineWidth=1.5; ctx.strokeStyle=ink; ctx.stroke();
      ctx.beginPath(); ctx.arc(g.cx,g.cy,g.R,0,2*Math.PI); ctx.clip();
    } else {
      ctx.fillStyle=fill; ctx.fillRect(0,0,W,g.oy);
      ctx.beginPath(); ctx.moveTo(0,g.oy); ctx.lineTo(W,g.oy); ctx.lineWidth=1.5; ctx.strokeStyle=ink; ctx.stroke();
      ctx.beginPath(); ctx.rect(0,0,W,g.oy); ctx.clip();
    }
    // triangle fills first
    objs.forEach(function(o){
      if(o.type!=="triangle") return;
      const a=o.p[0].z,b=o.p[1].z,c=o.p[2].z;
      poly(segmentPts(a,b,40).concat(segmentPts(b,c,40),segmentPts(c,a,40)),true);
      ctx.globalAlpha=.18; ctx.fillStyle=acc; ctx.fill(); ctx.globalAlpha=1;
    });
    objs.forEach(function(o){
      ctx.setLineDash([]); ctx.lineWidth=2; ctx.strokeStyle=o.hl?acc:ink;
      if(o.type==="line"){ poly(linePts(o.p[0].z,o.p[1].z,240)); ctx.stroke(); }
      else if(o.type==="segment"){ poly(segmentPts(o.p[0].z,o.p[1].z,80)); ctx.stroke(); }
      else if(o.type==="circle"){ poly(circlePts(o.p[0].z,o.p[1].z,160),true); ctx.stroke(); }
      else if(o.type==="triangle"){
        ctx.strokeStyle=acc; ctx.lineWidth=2.4;
        [[0,1],[1,2],[2,0]].forEach(function(e){ poly(segmentPts(o.p[e[0]].z,o.p[e[1]].z,80)); ctx.stroke(); });
      }
      else if(o.type==="distance"){
        ctx.setLineDash([6,5]); ctx.strokeStyle=soft; poly(segmentPts(o.p[0].z,o.p[1].z,80)); ctx.stroke(); ctx.setLineDash([]);
      }
      else if(o.type==="angle"){
        const v=o.p[1].z, sv=toScreen(v);
        const a1=toScreen(segmentPts(v,o.p[0].z,60)[4]), a2=toScreen(segmentPts(v,o.p[2].z,60)[4]);
        let t1=Math.atan2(a1.y-sv.y,a1.x-sv.x), t2=Math.atan2(a2.y-sv.y,a2.x-sv.x), d=t2-t1;
        while(d>Math.PI) d-=2*Math.PI; while(d<-Math.PI) d+=2*Math.PI;
        ctx.beginPath(); ctx.arc(sv.x,sv.y,16,t1,t1+d,d<0); ctx.strokeStyle=acc; ctx.lineWidth=2; ctx.stroke();
      }
    });
    ctx.restore();
    // points on top
    ctx.font="600 14px "+css("--f-ui");
    pts.forEach(function(p){
      const s=toScreen(p.z); if(!isFinite(s.x)||s.y>H+20) return;
      const on=sel.indexOf(p)>=0, hv=hover===p;
      ctx.beginPath(); ctx.arc(s.x,s.y,on||hv?7:5.5,0,2*Math.PI);
      ctx.fillStyle=on?acc:ink; ctx.fill(); ctx.lineWidth=2; ctx.strokeStyle=sheet; ctx.stroke();
      ctx.fillStyle=ink; ctx.fillText(p.name,s.x+9,s.y-9);
    });
    readout();
  }

  /* measurements */
  function fmt(x,d){ return x.toFixed(d===undefined?2:d); }
  function readout(){
    const rows=[];
    objs.forEach(function(o){
      const n=o.p.map(function(p){return p.name;});
      if(o.type==="distance") rows.push('<li><span>d('+n[0]+', '+n[1]+')</span><b>'+fmt(hdist(o.p[0].z,o.p[1].z))+'</b></li>');
      if(o.type==="angle") rows.push('<li><span>∠'+n.join("")+'</span><b>'+fmt(hangle(o.p[1].z,o.p[0].z,o.p[2].z),1)+'°</b></li>');
      if(o.type==="triangle"){
        const A=o.p[0].z,B=o.p[1].z,Cc=o.p[2].z;
        const a=hangle(A,B,Cc), b=hangle(B,Cc,A), c=hangle(Cc,A,B), s=a+b+c;
        rows.push('<li class="tri"><span>Triangle '+n.join("")+'</span><b>'+fmt(s,1)+'°</b>'+
          '<small>∠'+n[0]+' '+fmt(a,1)+'° + ∠'+n[1]+' '+fmt(b,1)+'° + ∠'+n[2]+' '+fmt(c,1)+'°. Defect 180° − '+fmt(s,1)+'° = <b>'+fmt(180-s,1)+'°</b></small>'+
          '<span class="meter" aria-hidden="true"><i style="width:'+Math.max(0,Math.min(100,s/180*100)).toFixed(1)+'%"></i></span></li>');
      }
    });
    out.innerHTML = rows.length ? '<ul>'+rows.join("")+'</ul>' : '<p class="sb-empty">Measurements appear here. Use <b>Distance</b>, <b>Angle</b> or <b>Triangle</b>.</p>';
  }

  /* tools */
  const NEED={point:1,line:2,segment:2,circle:2,distance:2,angle:3,triangle:3};
  const HINT={move:"Drag any point. Tap empty space to deselect.",point:"Tap to place a point.",
    line:"Tap two points (or empty space) for the line through them.",segment:"Tap two points for a segment.",
    circle:"Tap the centre, then a point on the circle.",distance:"Tap two points to measure their hyperbolic distance.",
    angle:"Tap three points A, V, B to measure the angle at V.",triangle:"Tap three points: the triangle and its angle sum appear."};
  function setTool(t){
    tool=t; sel=[];
    root.querySelectorAll("[data-tool]").forEach(function(b){ b.setAttribute("aria-pressed", b.dataset.tool===t?"true":"false"); });
    const h=root.querySelector("[data-hint]"); if(h) h.textContent=HINT[t];
    draw();
  }
  function hit(x,y){
    let best=null, bd=18;
    pts.forEach(function(p){ const s=toScreen(p.z), d=Math.hypot(s.x-x,s.y-y); if(d<bd){bd=d;best=p;} });
    return best;
  }
  function pos(e){ const r=canvas.getBoundingClientRect(); return {x:e.clientX-r.left,y:e.clientY-r.top}; }
  canvas.addEventListener("pointerdown",function(e){
    const q=pos(e), p=hit(q.x,q.y);
    canvas.setPointerCapture(e.pointerId);
    if(tool==="move"){ if(p) drag=p; else { sel=[]; draw(); } return; }
    const target = p || newPoint(toModel(q.x,q.y));
    if(tool==="point"){ drag=target; draw(); return; }
    if(sel.indexOf(target)<0) sel.push(target);
    if(sel.length===NEED[tool]){
      objs.push({type:tool,p:sel.slice()}); sel=[];
    }
    draw();
  });
  canvas.addEventListener("pointermove",function(e){
    const q=pos(e);
    if(drag){ drag.z=toModel(q.x,q.y); draw(); e.preventDefault(); return; }
    const h=hit(q.x,q.y); if(h!==hover){ hover=h; canvas.style.cursor=h?(tool==="move"?"grab":"pointer"):"crosshair"; draw(); }
  });
  ["pointerup","pointercancel"].forEach(function(t){ canvas.addEventListener(t,function(){ drag=null; }); });

  /* buttons */
  root.querySelectorAll("[data-tool]").forEach(function(b){ b.addEventListener("click",function(){ setTool(b.dataset.tool); }); });
  root.querySelectorAll("[data-model]").forEach(function(b){ b.addEventListener("click",function(){
    model=b.dataset.model;
    root.querySelectorAll("[data-model]").forEach(function(x){ x.setAttribute("aria-pressed", x===b?"true":"false"); });
    draw();
  }); });
  function act(name,fn){ const b=root.querySelector('[data-act="'+name+'"]'); if(b) b.addEventListener("click",fn); }
  act("undo",function(){
    if(sel.length){ sel=[]; draw(); return; }
    if(objs.length){ objs.pop(); }
    else if(pts.length){ pts.pop(); nextLabel=Math.max(0,nextLabel-1); }
    draw();
  });
  act("clear",function(){ clear(); draw(); });
  function clear(){ objs=[]; pts=[]; sel=[]; nextLabel=0; }

  /* guided set-ups */
  const SCENES={
    triangle:function(){
      clear(); const A=newPoint(C(-0.35,-0.2)),B=newPoint(C(0.4,-0.25)),Cc=newPoint(C(0.05,0.4));
      objs.push({type:"triangle",p:[A,B,Cc]}); setTool("move");
    },
    parallels:function(){
      clear();
      const X=newPoint(C(-0.62,-0.45),"X"), Y=newPoint(C(0.62,-0.45),"Y"); objs.push({type:"line",p:[X,Y]});
      newPoint(C(0.0,0.35),"P"); nextLabel=0; setTool("line");
    },
    saccheri:function(){ clear(); buildSaccheri(); setTool("move"); }
  };
  function buildSaccheri(){
    const base=+(root.querySelector("#sb-base")||{value:1.6}).value, leg=+(root.querySelector("#sb-leg")||{value:1.2}).value;
    const a=Math.tanh(base/4);
    const A=newPoint(C(-a,-0.25),"A"), B=newPoint(C(a,-0.25),"B");
    // place AB symmetric about the imaginary axis at the chosen height: move the pair with an isometry
    const shift=C(0,-0.25);
    A.z=from0(shift,C(-a,0)); B.z=from0(shift,C(a,0));
    const nA=perpUp(A.z,B.z), nB=perpUp(B.z,A.z);
    const D=newPoint(along(A.z,nA,leg),"D"), Cc=newPoint(along(B.z,nB,leg),"C");
    objs.push({type:"segment",p:[A,B]},{type:"segment",p:[B,Cc]},{type:"segment",p:[Cc,D]},{type:"segment",p:[D,A]});
    objs.push({type:"angle",p:[B,A,D]},{type:"angle",p:[Cc,B,A]},{type:"angle",p:[A,D,Cc]},{type:"angle",p:[D,Cc,B]});
    objs.push({type:"distance",p:[A,D]},{type:"distance",p:[B,Cc]});
  }
  // unit direction at p perpendicular to the line p→q, on the side of +i
  function perpUp(p,q){ const t=toO(p,q), u=scl(t,1/abs(t)); let n=C(-u.y,u.x); if(q.x<p.x) n=C(u.y,-u.x); return n; }
  root.querySelectorAll("[data-scene]").forEach(function(b){ b.addEventListener("click",function(){
    SCENES[b.dataset.scene](); draw();
    const c=root.querySelector(".sb-stage"); if(c && c.getBoundingClientRect().top<0) c.scrollIntoView({block:"start",behavior:"smooth"});
  }); });
  ["sb-base","sb-leg"].forEach(function(id){ const s=root.querySelector("#"+id); if(s) s.addEventListener("input",function(){
    const v=root.querySelector('[data-val="'+id+'"]'); if(v) v.textContent=(+s.value).toFixed(1);
    clear(); buildSaccheri(); draw();
  }); });

  /* size */
  function resize(){
    const box=canvas.parentElement.getBoundingClientRect(); if(box.width<10) return;
    W=box.width; H=Math.min(W, 560); dpr=window.devicePixelRatio||1;
    canvas.style.width=W+"px"; canvas.style.height=H+"px"; canvas.width=Math.round(W*dpr); canvas.height=Math.round(H*dpr);
    draw();
  }
  if("ResizeObserver" in window) new ResizeObserver(resize).observe(canvas.parentElement);
  window.addEventListener("resize",resize);
  try{ window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change",draw); }catch(e){}

  SCENES.triangle(); setTool("move"); resize();
  return {redraw:resize};
}

window.Sandbox={mount:mount, _math:{hdist:hdist,hangle:hangle,toO:toO,from0:from0,C:C,along:along}};
})();
