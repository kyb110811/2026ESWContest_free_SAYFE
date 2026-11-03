const $ = id => document.getElementById(id);
const cards = new Map();
let lastSnapshot = null;
let connected = false;
const percent = value => `${(value * 100).toFixed(1)}%`;
const stateText = state => ({DANGER:'위험 소리 감지',CLEAR:'현재 위험 소리 없음',UNKNOWN:'판정 대기 / 입력 확인'})[state] || state;

function scoreRow(label, score, active = false) {
  const row = document.createElement('div');
  row.className = `score${active ? ' active' : ''}`;
  row.style.setProperty('--score', percent(score));
  const name = document.createElement('span'); name.className='name'; name.textContent=label;
  const number = document.createElement('span'); number.className='number'; number.textContent=percent(score);
  row.append(name,number);
  return row;
}

function renderAll(card, camera) {
  const container = card.querySelector('.all-scores');
  if (!connected) {container.replaceChildren();return;}
  if (!card.querySelector('details').open) return;
  const filter = card.querySelector('.filter').value.trim().toLocaleLowerCase();
  const rows = (lastSnapshot?.labels || []).map((label,index) => ({label,score:camera.result?.scores[index]}))
    .filter(row => row.label.toLocaleLowerCase().includes(filter));
  rows.sort((a,b)=>(b.score??-1)-(a.score??-1));
  const fragment = document.createDocumentFragment();
  for (const row of rows) {
    if (row.score != null) fragment.append(scoreRow(row.label,row.score));
  }
  container.replaceChildren(fragment);
}

function render(snapshot) {
  lastSnapshot=snapshot; connected=true;
  $('overall').textContent=stateText(snapshot.state); $('overall').dataset.state=snapshot.state;
  $('model-info').textContent=snapshot.model_status === 'READY' ?
    `${snapshot.model.model_name} · 전체 ${snapshot.labels.length}개 클래스 · ${snapshot.model.device.toUpperCase()} · ${snapshot.settings.window_seconds}초 문맥 / 최근 ${snapshot.settings.decision_seconds}초 판정 · 감지 기준: ${percent(snapshot.settings.danger_threshold)} 이상 또는 1위이면서 ${percent(snapshot.settings.top1_min_score)} 이상` :
    `모델 ${snapshot.model_status}${snapshot.model_error ? ' · '+snapshot.model_error : ''}`;
  if (snapshot.recording_error) $('model-info').textContent+=' · 이벤트 기록 오류: '+snapshot.recording_error;
  for (const camera of snapshot.cameras) {
    if (!cards.has(camera.id)) {
      const card=$('camera-template').content.firstElementChild.cloneNode(true);
      $('cameras').append(card); cards.set(camera.id,card);
      card.querySelector('details').addEventListener('toggle',()=>renderAll(card,lastSnapshot.cameras.find(c=>c.id===camera.id)));
      card.querySelector('.filter').addEventListener('input',()=>renderAll(card,lastSnapshot.cameras.find(c=>c.id===camera.id)));
    }
    const card=cards.get(camera.id), result=camera.result;
    card.dataset.state=camera.state;
    card.querySelector('.camera-name').textContent=`${camera.id} · ${camera.name}`;
    card.querySelector('.device').textContent=camera.alsa_device;
    card.querySelector('.status').textContent=stateText(camera.state);
    card.querySelector('.error').textContent=camera.error || '';
    card.querySelector('.error').hidden=!camera.error;
    card.querySelector('.count').textContent=`(${snapshot.labels.length})`;
    card.querySelector('.metrics').textContent=result ?
      `입력 ${result.rms_dbfs.toFixed(1)} dBFS · 추론 ${result.inference_ms.toFixed(0)}ms · 결과 나이 ${camera.result_age_seconds.toFixed(1)}초 · 누적 ${camera.inference_count}회` :
      `${camera.capture_status} · 마이크 입력과 최신 추론 결과를 기다립니다.`;
    card.querySelector('.meter span').style.width=result ? `${Math.max(0,Math.min(100,(result.rms_dbfs+70)/70*100))}%` : '0%';
    const hazards=document.createDocumentFragment(), top=document.createDocumentFragment();
    for (const item of result?.hazards || []) {
      if (item.label === 'Explosion') hazards.append(scoreRow(`${item.label}${item.active?' · 감지':''}${item.top1?' · 1위':''}`,item.score,item.active));
    }
    if (!result) hazards.append(document.createTextNode('최신 입력 판정 없음'));
    for (const item of result?.top || []) top.append(scoreRow(item.label,item.score));
    card.querySelector('.hazards').replaceChildren(hazards);
    card.querySelector('.top').replaceChildren(top);
    renderAll(card,camera);
  }
  const events=snapshot.events.filter(e=>e.label==='Explosion' && (e.kind==='audio_danger_started'||e.kind==='audio_danger_ended'));
  const fragment=document.createDocumentFragment();
  for (const event of [...events].reverse()) {
    const row=document.createElement('tr');row.dataset.danger=String(event.kind==='audio_danger_started');
    for (const value of [new Date(event.time).toLocaleTimeString(),event.camera_id,event.kind==='audio_danger_started'?'감지 시작':'감지 해제',event.label,percent(event.score),event.trigger==='top1'?'1위':event.trigger==='threshold'?'임계값':'해제']) {
      const cell=document.createElement('td');cell.textContent=value;row.append(cell);
    }
    fragment.append(row);
  }
  $('events').replaceChildren(fragment);$('no-events').hidden=events.length>0;
}

async function poll() {
  const controller=new AbortController(), timeout=setTimeout(()=>controller.abort(),3000);
  try {
    const response=await fetch('/api/status',{cache:'no-store',signal:controller.signal});
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    render(await response.json());$('connection').hidden=true;
  } catch (error) {
    connected=false;
    $('overall').textContent='연결 끊김';$('overall').dataset.state='UNKNOWN';
    $('connection').textContent=`오디오 서버 연결을 확인하세요. ${error.message}`;$('connection').hidden=false;
    for (const card of cards.values()) {
      card.dataset.state='UNKNOWN';card.querySelector('.status').textContent='최신 판정 확인 불가';
      card.querySelector('.top').replaceChildren();card.querySelector('.hazards').replaceChildren();
      card.querySelector('.all-scores').replaceChildren();card.querySelector('.metrics').textContent='서버 응답 없음';
    }
  } finally {clearTimeout(timeout);setTimeout(poll,500);}
}
poll();
