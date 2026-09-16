(() => {
  "use strict";
  const widgets = [...document.querySelectorAll("[data-line11-widget]")];
  if (!widgets.length) return;
  const STORAGE_KEY = "suzano-aberta:line11:last:v1", REFRESH_MS = 90000, REQUEST_TIMEOUT_MS = 8000;
  const stationOrder = ["Calmon Viana", "Suzano", "Jundiapeba", "Estudantes"];
  const dateTime = new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" });

  function escapeHtml(value) { return String(value ?? "").replace(/[&<>'"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[c])); }
  function formatTime(value) { if(!value)return null;const d=new Date(value);return Number.isNaN(d.getTime())?String(value):dateTime.format(d); }
  function getStored(){try{const v=JSON.parse(localStorage.getItem(STORAGE_KEY)||"null");return v&&typeof v==="object"?v:null;}catch(_){return null;}}
  function store(payload){if(!payload||payload.availability==="unavailable")return;try{localStorage.setItem(STORAGE_KEY,JSON.stringify({saved_at:new Date().toISOString(),payload}));}catch(_){}}
  async function loadConfig(){const r=await fetch("./config.json",{cache:"no-cache"});if(!r.ok)throw new Error(`Configuração HTTP ${r.status}`);return r.json();}
  async function fetchStatus(){const config=await loadConfig(),base=String(config?.api_base||"").replace(/\/$/,"");if(!base)throw new Error("Backend de tempo real ainda não está configurado neste ambiente.");const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),REQUEST_TIMEOUT_MS);try{const r=await fetch(`${base}/v1/transit/line-11`,{cache:"no-store",headers:{Accept:"application/json"},signal:controller.signal});if(!r.ok)throw new Error(`Backend HTTP ${r.status}`);return r.json();}finally{clearTimeout(timer);}}
  function stateLabel(p){if(p.availability==="unavailable")return"Dados indisponíveis";if(p.stale||p.availability==="stale")return"Dado desatualizado";if(p.operation_normal)return"Operação normal";return p.status||"Alteração operacional";}
  function stationStrip(p){const affected=String(p.affected_segment||"").toLocaleLowerCase("pt-BR");return `<ol class="line11-stations" aria-label="Trecho acompanhado">${stationOrder.map(name=>{const classes=[name==="Suzano"?"is-focus":"",affected.includes(name.toLocaleLowerCase("pt-BR"))?"is-affected":""].filter(Boolean).join(" ");return `<li class="${classes}"><i aria-hidden="true"></i><span>${escapeHtml(name)}</span></li>`;}).join("")}</ol>`;}
  function sourceHtml(p){const s=p.source;if(!s)return"Fonte operacional não disponível no momento.";const name=escapeHtml(s.name||"Fonte oficial"),url=escapeHtml(s.url||"");return url?`<a href="${url}" target="_blank" rel="noopener noreferrer">${name}</a>`:name;}
  function updateText(p){const source=formatTime(p.source_updated_at),checked=formatTime(p.checked_at);if(source)return`Atualização informada pela fonte: ${source}`;if(checked)return`A fonte não informou horário próprio; consultada pelo Suzano Aberta em ${checked}`;return"Horário de atualização não informado pela fonte.";}
  function render(widget,p,{browserFallback=false}={}){
    const unavailable=p.availability==="unavailable",stale=Boolean(p.stale||p.availability==="stale"||browserFallback),occ=p.occurrence?.description||null,reason=p.reason||occ||null;
    const cls=unavailable?"is-unavailable":stale?"is-stale":p.operation_normal?"is-normal":"is-alert";
    const occurrenceText=unavailable?"Nenhuma ocorrência pode ser confirmada agora.":occ||(p.operation_normal?"Nenhuma ocorrência operacional informada pela fonte atual.":"A fonte atual não forneceu descrição detalhada da ocorrência.");
    const segment=p.affected_segment||(p.operation_normal?"Toda a extensão sem trecho afetado informado":"Trecho não informado pela fonte");
    const reasonText=reason||(p.operation_normal?"Nenhum motivo de alteração informado.":"Motivo não informado pela fonte.");
    widget.innerHTML=`<article class="line11-card ${cls}"><header class="line11-head"><div><span class="line11-kicker">Linha 11–Coral</span><h3>Estação Suzano e trecho leste</h3></div><span class="line11-state">${escapeHtml(stateLabel(p))}</span></header>${stationStrip(p)}<div class="line11-facts"><div><span>Status atual</span><strong>${escapeHtml(p.status||"Não informado")}</strong></div><div><span>Trecho afetado</span><strong>${escapeHtml(segment)}</strong></div><div><span>Ocorrência</span><strong>${escapeHtml(occurrenceText)}</strong></div><div><span>Motivo</span><strong>${escapeHtml(reasonText)}</strong></div></div><footer class="line11-foot"><div><strong>Fonte:</strong> ${sourceHtml(p)}<br><span>${escapeHtml(updateText(p))}${stale?" · dado exibido como desatualizado":""}</span></div><button type="button" class="line11-refresh" data-line11-refresh>Atualizar</button></footer></article>`;
    widget.querySelector("[data-line11-refresh]")?.addEventListener("click",()=>refreshWidget(widget,true));
  }
  function renderUnavailable(widget,message){const cached=getStored();if(cached?.payload){render(widget,{...cached.payload,availability:"stale",stale:true},{browserFallback:true});return;}render(widget,{line:"Linha 11-Coral",availability:"unavailable",stale:false,status:"Dados em tempo real indisponíveis",operation_normal:false,occurrence:null,affected_segment:null,reason:null,checked_at:new Date().toISOString(),source:null,client_error:message});}
  async function refreshWidget(widget,forced=false){if(widget.dataset.loading==="true")return;widget.dataset.loading="true";if(forced)widget.setAttribute("aria-busy","true");try{const p=await fetchStatus();store(p);render(widget,p);}catch(error){renderUnavailable(widget,error instanceof Error?error.message:String(error));}finally{widget.dataset.loading="false";widget.removeAttribute("aria-busy");}}
  widgets.forEach(widget=>refreshWidget(widget));const timer=setInterval(()=>widgets.forEach(widget=>refreshWidget(widget)),REFRESH_MS);addEventListener("pagehide",()=>clearInterval(timer),{once:true});
})();
