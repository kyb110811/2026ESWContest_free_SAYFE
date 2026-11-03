const labels={explosion:'폭발음'};
const byId=id=>document.getElementById(id);
const text=(tag,value,className)=>{const node=document.createElement(tag);node.textContent=value;if(className)node.className=className;return node;};
const percent=value=>`${Math.round((value||0)*100)}%`;
const renderSounds=(list,items)=>{
  const sounds=items.map(item=>{
    const row=text('div','', 'sound-row');row.append(text('b',item.label),text('span',`${item.camera_id} · ${percent(item.score)}`));return row;
  });
  list.replaceChildren(...(sounds.length?sounds:[text('span','최신 소리 판정이 없습니다.')]));
};

function render(data){
  byId('connection').dataset.state='live';byId('connection').textContent='● 실시간 연결';
  const active=[];
  for(const zone of data.zones){
    const card=document.querySelector(`.zone[data-zone="${zone.id}"]`);
    const explosions=zone.hazards.filter(hazard=>hazard.kind==='explosion');
    const zoneCameras=data.cameras.filter(camera=>camera.zone===zone.id);
    const state=explosions.length?'DANGER':zoneCameras.length&&zoneCameras.every(camera=>camera.state!=='UNKNOWN')?'CLEAR':'UNKNOWN';
    card.dataset.state=state;
    card.querySelector('.zone-state').textContent=state==='DANGER'?'위험 소리 감지':state==='CLEAR'?'관측 정상':'입력 확인 중';
    if(zone.id==='A'){
      for(const column of card.querySelectorAll('.sound-column')){
        renderSounds(column.querySelector('.sound-list'),zone.sounds.filter(item=>item.camera_id===column.dataset.camera).slice(0,3));
      }
    }else{
      renderSounds(card.querySelector('.sound-list'),zone.sounds.slice(0,5));
    }
    const found=new Map();
    for(const hazard of explosions){
      const prior=found.get(hazard.kind);
      if(!prior||hazard.score>prior.score)found.set(hazard.kind,hazard);
    }
    for(const [kind,hazard] of found)active.push({zone:zone.id,kind,...hazard});
  }
  const alertNodes=active.length?active.map(item=>{
    const card=text('div','', 'alert danger');
    card.append(text('b',`${item.zone}구역 ${labels[item.kind]} 감지됨`),
      text('small',`${item.camera_id} 마이크 · ${item.label} · ${percent(item.score)}`));return card;
  }):[(()=>{const card=text('div','','alert');card.append(text('b','현재 위험 소리 감지 없음'),text('small','폭발음 감지 시 구역과 함께 빨간색으로 표시됩니다.'));return card;})()];
  byId('alerts').replaceChildren(...alertNodes);
  byId('summary').textContent=active.length?`${active.length}건 감지 중 · A/B 구역 확인 필요`:
    [...document.querySelectorAll('.zone')].every(card=>card.dataset.state==='CLEAR')?'A/B 구역 관측 정상':'일부 입력 확인 중';
  byId('camera3-message').textContent=data.camera3.state==='LIVE'?'':
    data.camera3.error||'CAM3 영상 입력을 기다리고 있습니다.';
  const events=data.events.filter(event=>event.kind==='explosion').map(event=>{
    const row=text('div','','event'+(event.active?' active':''));
    row.append(text('time',new Date(event.time).toLocaleTimeString('ko-KR',{hour12:false})),
      text('span',`${event.zone}구역`),
      text('strong',`${labels[event.kind]} ${event.active?'감지됨':'감지 해제'} · ${event.camera_id}`),
      text('small',percent(event.score)));return row;
  });
  byId('events').replaceChildren(...(events.length?events:[text('p','아직 감지 기록이 없습니다.','empty')]));
}

async function poll(){
  const controller=new AbortController();const timeout=setTimeout(()=>controller.abort(),4000);
  try{
    const response=await fetch('/api/status',{cache:'no-store',signal:controller.signal});
    if(!response.ok)throw Error(`HTTP ${response.status}`);
    render(await response.json());
  }catch(error){byId('connection').dataset.state='error';byId('connection').textContent=`● 서버 연결 확인 · ${error.message}`;}
  finally{clearTimeout(timeout);setTimeout(poll,1000);}
}
poll();
