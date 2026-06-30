const canvas = document.querySelector('#game');
const ctx = canvas.getContext('2d');
const join = document.querySelector('#join');
const form = document.querySelector('#join-form');
const nameInput = document.querySelector('#name');
const styleInput = document.querySelector('#style');
const connection = document.querySelector('#connection');
const party = document.querySelector('#party');
const bossFill = document.querySelector('#boss-fill');
const bossName = document.querySelector('#boss-name');
const message = document.querySelector('#message');
const stats = document.querySelector('#stats');
const hpFill = document.querySelector('#hp-fill');
const hpText = document.querySelector('#hp-text');
const manaFill = document.querySelector('#mana-fill');
const manaText = document.querySelector('#mana-text');
const questStatus = document.querySelector('#quest-status');
const evolutionStatus = document.querySelector('#evolution-status');
const uniqueStatus = document.querySelector('#unique-status');
const echoPanel = document.querySelector('#echo-panel');
const echoReadiness = document.querySelector('#echo-readiness');
const characterPanel = document.querySelector('#character-panel');
const characterButton = document.querySelector('#character-button');
const characterClose = document.querySelector('#character-close');
const inventoryPanel = document.querySelector('#inventory-panel');
const inventoryButton = document.querySelector('#inventory-button');
const inventoryClose = document.querySelector('#inventory-close');

const WORLD = { width: 2880, height: 2112 };
const guardian = { x:1656, y:600, hp:850, maxHp:850, cleared:false, name:'Asterion, Skyglass Sentinel', floor:1, color:[66,215,228], shape:'sentinel', nextSpawn:0 };
const player = { id:null, name:'Ari', x:408, y:408, hp:100, maxHp:100, mana:40, maxMana:40, level:1, xp:0, xpNext:100, gold:0, kills:0, color:[116,214,255], combo:0, attackFlash:0 };
let players = [];
let monsters = [];
let loot = [];
let echo = {x:470,y:445,hp:90,max_hp:90};
let echoProgress = {overall:0,exploration:0,monsters:0,combat:0,boss:0,support:0,ready_for_content:false};
let echoLearning = {state:'waiting',action:'patrol',last_reward:0,total_reward:0,epsilon:.28,states_learned:0,decisions:0,updates:0,last_q_change:0,q_values:{}};
let uniqueEncounter = {name:'Grimveil Devourer',unlocked:false,defeated:false};
let npcs = [], chests = [];
let lastNoticeId = 0;
let lastInventorySignature = '';
let socket = null;
let connected = false;
let lastFrame = performance.now();
let lastSend = 0;
let lastAttack = 0;
const keys = new Set();

function resize(){ canvas.width = innerWidth * devicePixelRatio; canvas.height = innerHeight * devicePixelRatio; }
addEventListener('resize', resize); resize();
addEventListener('keydown', e => {
  keys.add(e.code);
  if(e.code==='Space'){e.preventDefault();attack();}
  if(e.code==='KeyE'&&!e.repeat){e.preventDefault();useManaSkill();}
  if(e.code==='KeyQ'&&!e.repeat){e.preventDefault();useDevourerSkill();}
  if(e.code==='KeyP'&&!e.repeat){echoPanel.classList.toggle('hidden');}
  if(e.code==='KeyC'&&!e.repeat){characterPanel.classList.toggle('hidden');}
  if(e.code==='KeyI'&&!e.repeat){inventoryPanel.classList.toggle('hidden');}
  if(e.code==='KeyF'&&!e.repeat){interact();}
  if(e.code==='Escape'){characterPanel.classList.add('hidden');inventoryPanel.classList.add('hidden');echoPanel.classList.add('hidden');}
});
addEventListener('keyup', e => keys.delete(e.code));
characterButton.addEventListener('click',()=>characterPanel.classList.toggle('hidden'));
characterClose.addEventListener('click',()=>characterPanel.classList.add('hidden'));
inventoryButton.addEventListener('click',()=>inventoryPanel.classList.toggle('hidden'));
inventoryClose.addEventListener('click',()=>inventoryPanel.classList.add('hidden'));

function wsUrl(){
  const custom = new URLSearchParams(location.search).get('ws');
  if(custom) return custom;
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${location.host}/ws`;
}

form.addEventListener('submit', e => {
  e.preventDefault();
  player.name = nameInput.value.trim() || 'Adventurer';
  connection.textContent = 'Connecting…';
  socket = new WebSocket(wsUrl());
  socket.addEventListener('open', () => socket.send(JSON.stringify({type:'join',name:player.name,style:styleInput.value})));
  socket.addEventListener('message', event => {
    const data = JSON.parse(event.data);
    if(data.type === 'error'){ connection.textContent = data.message; return; }
    if(data.type === 'welcome'){
      player.id = data.player_id; connected = true; join.classList.add('hidden');
      applySnapshot(data.snapshot); flash('Connected to Floor 1');
    } else if(data.type === 'snapshot') applySnapshot(data);
  });
  socket.addEventListener('close', () => { connected=false; join.classList.remove('hidden'); connection.textContent='Disconnected. Start the server and try again.'; });
  socket.addEventListener('error', () => connection.textContent='Could not reach the game server.');
});

function applySnapshot(data){
  players = data.players || [];
  const me = players.find(p => p.id === player.id);
  if(me){
    player.color=me.color; player.hp=me.hp; player.maxHp=me.max_hp; player.level=me.level;
    player.mana=me.mana??40; player.maxMana=me.max_mana??40;
    player.xp=me.xp||0; player.xpNext=me.xp_next||100; player.gold=me.gold||0; player.kills=me.kills||0; player.floorsCleared=me.floors_cleared||0;
    player.questKills=me.quest_kills||0;player.questTarget=me.quest_target||5;player.questCompletions=me.quest_completions||0;
    player.evolutionPoints=me.evolution_points||0;player.evolutionRank=me.evolution_rank||'Reborn Wanderer';
    player.devourerUnlocked=!!me.devourer_unlocked;player.essences=me.essences||{};
    player.style=me.style||'Vanguard';player.inventory=me.inventory||[];player.equipment=me.equipment||{};
    player.attackBonus=me.attack_bonus||0;player.defense=me.defense||0;player.dungeonChests=me.dungeon_chests||0;
    player.storyChapter=me.story_chapter||'Chapter 1';player.storyObjective=me.story_objective||'';
    if((me.notice_id||0)>lastNoticeId){lastNoticeId=me.notice_id||0;if(me.notice)flash(me.notice);}
    if(Math.hypot(player.x-me.x,player.y-me.y)>180){player.x=me.x;player.y=me.y;}
  }
  monsters=data.monsters||[]; loot=data.loot||[]; if(data.echo) echo=data.echo;if(data.echo_progress) echoProgress=data.echo_progress;
  if(data.echo_learning)echoLearning=data.echo_learning;
  npcs=data.npcs||[];chests=data.chests||[];
  if(data.unique_encounter){
    const justAwakened=!uniqueEncounter.unlocked&&data.unique_encounter.unlocked;
    uniqueEncounter=data.unique_encounter;
    if(justAwakened)flash(`UNIQUE ENCOUNTER AWAKENED: ${uniqueEncounter.name}`);
  }
  if(data.guardian){
    guardian.hp=data.guardian.hp; guardian.maxHp=data.guardian.max_hp; guardian.cleared=data.guardian.cleared;
    guardian.x=data.guardian.x;guardian.y=data.guardian.y;guardian.name=data.guardian.name;guardian.floor=data.guardian.floor;
    guardian.color=data.guardian.color;guardian.shape=data.guardian.shape;guardian.nextSpawn=data.guardian.next_spawn_seconds||0;
    guardian.phase=data.guardian.phase||1;guardian.specialWarning=!!data.guardian.special_warning;guardian.specialSeconds=data.guardian.special_seconds||0;
  }
  party.textContent = `Party ${players.length}/4`;
  hpFill.style.width=`${Math.max(0,player.hp/player.maxHp*100)}%`;
  manaFill.style.width=`${Math.max(0,player.mana/player.maxMana*100)}%`;
  hpText.textContent=`HP ${Math.ceil(player.hp)} / ${player.maxHp}`;
  manaText.textContent=`Mana ${Math.floor(player.mana)} / ${player.maxMana}`;
  stats.textContent=`Level ${player.level} · XP ${player.xp}/${player.xpNext} · Gold ${player.gold} · Kills ${player.kills} · Floors ${player.floorsCleared||0}`;
  questStatus.textContent=`Hunt Quest ${player.questCompletions||0}: Defeat monsters ${player.questKills||0} / ${player.questTarget||5}`;
  evolutionStatus.textContent=`${player.evolutionRank} · Essence ${player.evolutionPoints||0} · Q ${player.devourerUnlocked?'READY':'LOCKED AT 5'}`;
  uniqueStatus.textContent=uniqueEncounter.defeated?`Unique Defeated: ${uniqueEncounter.name}`:uniqueEncounter.unlocked?`Unique Active: ${uniqueEncounter.name}`:'Unique Encounter: Locked (complete 2 quests)';
  document.querySelector('#story-chapter').textContent=player.storyChapter||'CHAPTER 1';
  document.querySelector('#story-objective').textContent=player.storyObjective||'Explore Everdawn.';
  updateCharacterPanel();
  updateInventoryPanel();
  updateEchoPanel();
  bossFill.style.width = `${Math.max(0,guardian.hp/guardian.maxHp*100)}%`;
  bossName.textContent=guardian.cleared?`FLOOR ${guardian.floor} CLEARED · NEXT GUARDIAN IN ${guardian.nextSpawn.toFixed(1)}s`:`FLOOR ${guardian.floor} · PHASE ${guardian.phase} · ${guardian.name.toUpperCase()}`;
  if(guardian.cleared&&guardian.nextSpawn>7.7) flash(`FLOOR ${guardian.floor} CLEARED · ASCENDING`);
}

function attack(){
  if(!connected) return;
  const now=performance.now(); if(now-lastAttack<220) return; lastAttack=now;
  const targets=monsters.filter(m=>m.active).map(m=>({id:m.id,x:m.x,y:m.y,range:125}));
  if(!guardian.cleared) targets.push({id:'guardian',x:guardian.x,y:guardian.y,range:190});
  targets.sort((a,b)=>Math.hypot(player.x-a.x,player.y-a.y)-Math.hypot(player.x-b.x,player.y-b.y));
  const target=targets[0];
  if(!target || Math.hypot(player.x-target.x,player.y-target.y)>target.range){ flash('No enemy in sword range'); return; }
  player.combo=Math.min(5,player.combo+1); player.attackFlash=.18;
  socket.send(JSON.stringify({type:'attack',target_id:target.id,damage:18+player.combo*3}));
}

function useManaSkill(){
  if(!connected||socket.readyState!==WebSocket.OPEN)return;
  if(player.mana<15){flash('Not enough Mana');return;}
  socket.send(JSON.stringify({type:'skill'}));player.attackFlash=.42;flash('ASCENSION BURST');
}

function useDevourerSkill(){
  if(!connected||socket.readyState!==WebSocket.OPEN)return;
  if(!player.devourerUnlocked){flash('Absorb 5 Essence to unlock Devourer Pulse');return;}
  if(player.mana<25){flash('Devourer Pulse needs 25 Mana');return;}
  socket.send(JSON.stringify({type:'devourer_skill'}));player.attackFlash=.65;flash('DEVOURER PULSE');
}

function interact(){
  if(connected&&socket.readyState===WebSocket.OPEN)socket.send(JSON.stringify({type:'interact'}));
}

function updateInventoryPanel(){
  const equipment=player.equipment||{};
  const signature=JSON.stringify({inventory:(player.inventory||[]).map(item=>item.id),equipment:Object.fromEntries(Object.entries(equipment).map(([slot,item])=>[slot,item?.id||null])),attack:player.attackBonus,defense:player.defense});
  if(signature===lastInventorySignature)return;
  lastInventorySignature=signature;
  for(const slot of ['weapon','armor','charm']){
    const item=equipment[slot];
    document.querySelector(`#slot-${slot}`).textContent=item?`${item.rarity} ${item.name}`:'Empty';
  }
  document.querySelector('#gear-summary').textContent=`${player.style||'Vanguard'} · Attack +${player.attackBonus||0} · Defense ${player.defense||0} · ${player.inventory?.length||0}/24 items`;
  const list=document.querySelector('#inventory-list');list.replaceChildren();
  if(!player.inventory?.length){const empty=document.createElement('p');empty.textContent='Defeat monsters, explore dungeon vaults, or visit Bram for equipment.';list.append(empty);return;}
  for(const item of player.inventory){
    const row=document.createElement('div');row.className='inventory-item';row.style.borderColor=`rgb(${item.color||[150,170,180]})`;
    const info=document.createElement('div');const title=document.createElement('strong');title.textContent=`${item.rarity} ${item.name}`;title.style.color=`rgb(${item.color||[220,230,240]})`;
    const details=document.createElement('span');details.textContent=`${item.slot.toUpperCase()} · ATK +${item.attack||0} · DEF +${item.defense||0} · HP +${item.hp||0}`;info.append(title,details);
    const button=document.createElement('button');button.textContent='EQUIP';button.onclick=()=>{button.textContent='EQUIPPING...';button.disabled=true;socket.send(JSON.stringify({type:'equip',item_id:item.id}));};row.append(info,button);list.append(row);
  }
}

function updateEchoPanel(){
  for(const key of ['exploration','monsters','combat','boss','support']){
    const value=Math.max(0,Math.min(1,echoProgress[key]||0));
    document.querySelector(`#echo-${key}`).style.width=`${value*100}%`;
    document.querySelector(`#echo-${key}-text`).textContent=`${Math.round(value*100)}%`;
  }
  document.querySelector('#echo-overall').textContent=`${Math.round((echoProgress.overall||0)*100)}%`;
  echoReadiness.textContent=echoProgress.ready_for_content?'Echo has mastered this content. It is time to add more!':'Echo is still learning the current floors and combat systems.';
  document.querySelector('#echo-ml-state').textContent=echoLearning.state||'waiting';
  document.querySelector('#echo-ml-action').textContent=echoLearning.action||'patrol';
  document.querySelector('#echo-ml-reward').textContent=Number(echoLearning.last_reward||0).toFixed(3);
  document.querySelector('#echo-ml-total').textContent=Number(echoLearning.total_reward||0).toFixed(2);
  document.querySelector('#echo-ml-epsilon').textContent=Number(echoLearning.epsilon||0).toFixed(3);
  document.querySelector('#echo-ml-states').textContent=echoLearning.states_learned||0;
  document.querySelector('#echo-ml-decisions').textContent=`${echoLearning.decisions||0} / ${echoLearning.updates||0}`;
  document.querySelector('#echo-ml-change').textContent=Number(echoLearning.last_q_change||0).toFixed(4);
  const values=document.querySelector('#echo-q-values');values.replaceChildren();
  const entries=Object.entries(echoLearning.q_values||{}).sort((a,b)=>b[1]-a[1]);
  if(!entries.length){values.textContent='No values learned yet.';}else for(const [action,value] of entries){const item=document.createElement('b');item.textContent=`${action}: ${Number(value).toFixed(3)}`;values.append(item);}
}

function updateCharacterPanel(){
  const essenceEntries=Object.entries(player.essences||{}).sort((a,b)=>b[1]-a[1]);
  const essenceText=essenceEntries.length?essenceEntries.map(([name,count])=>`${name} ×${count}`).join(' · '):'None yet';
  document.querySelector('#character-name').textContent=player.name||'Adventurer';
  document.querySelector('#character-rank').textContent=`${player.evolutionRank||'Reborn Wanderer'} · ${player.evolutionPoints||0} Evolution Points`;
  document.querySelector('#stat-level').textContent=player.level;
  document.querySelector('#stat-xp').textContent=`${player.xp} / ${player.xpNext}`;
  document.querySelector('#stat-hp').textContent=`${Math.ceil(player.hp)} / ${player.maxHp}`;
  document.querySelector('#stat-mana').textContent=`${Math.floor(player.mana)} / ${player.maxMana}`;
  document.querySelector('#stat-kills').textContent=player.kills||0;
  document.querySelector('#stat-gold').textContent=player.gold||0;
  document.querySelector('#stat-floors').textContent=player.floorsCleared||0;
  document.querySelector('#stat-quests').textContent=player.questCompletions||0;
  document.querySelector('#stat-essence').textContent=essenceText;
  document.querySelector('#stat-abilities').textContent=player.devourerUnlocked?'Sword Strike · Ascension Burst · Devourer Pulse':'Sword Strike · Ascension Burst · Devourer Pulse locked at 5 Essence';
  document.querySelector('#stat-unique').textContent=uniqueEncounter.defeated?`${uniqueEncounter.name} defeated`:uniqueEncounter.unlocked?`${uniqueEncounter.name} active`:'Locked · complete 2 Hunt Quests';
}

function update(dt, now){
  let dx=(keys.has('KeyD')||keys.has('ArrowRight')?1:0)-(keys.has('KeyA')||keys.has('ArrowLeft')?1:0);
  let dy=(keys.has('KeyS')||keys.has('ArrowDown')?1:0)-(keys.has('KeyW')||keys.has('ArrowUp')?1:0);
  const length=Math.hypot(dx,dy)||1; const speed=keys.has('ShiftLeft')||keys.has('ShiftRight')?280:190;
  player.x=Math.max(0,Math.min(WORLD.width,player.x+dx/length*speed*dt));
  player.y=Math.max(0,Math.min(WORLD.height,player.y+dy/length*speed*dt));
  player.attackFlash=Math.max(0,player.attackFlash-dt);
  if(connected && now-lastSend>80 && socket.readyState===WebSocket.OPEN){
    lastSend=now; socket.send(JSON.stringify({type:'state',x:player.x,y:player.y,hp:player.hp,max_hp:player.maxHp,level:player.level}));
  }
}

function draw(){
  const scale=devicePixelRatio; ctx.setTransform(scale,0,0,scale,0,0);
  const w=innerWidth,h=innerHeight; const camX=player.x-w/2,camY=player.y-h/2;
  drawWorld(camX,camY,w,h);
  drawSafeZone(408-camX,408-camY);
  for(const npc of npcs)drawNpc(npc.x-camX,npc.y-camY,npc);
  for(const chest of chests)drawChest(chest.x-camX,chest.y-camY);
  for(const item of loot) drawLoot(item.x-camX,item.y-camY,item.kind);
  for(const monster of monsters){if(monster.active) drawMonster(monster.x-camX,monster.y-camY,monster);}
  if(!guardian.cleared){
    if(guardian.specialWarning){ctx.fillStyle='#ff365533';ctx.strokeStyle='#ff6688';ctx.lineWidth=4;ctx.beginPath();ctx.arc(guardian.x-camX,guardian.y-camY,175+(guardian.phase||1)*35,0,Math.PI*2);ctx.fill();ctx.stroke();}
    drawGuardian(guardian.x-camX,guardian.y-camY);
  }
  drawEcho(echo.x-camX,echo.y-camY);
  for(const p of players){ if(p.id!==player.id) drawPlayer(p.x-camX,p.y-camY,p.color,p.name); }
  drawPlayer(w/2,h/2,player.color,player.name,true);
}

function tileType(tx,ty){
  if(tx<1||ty<1||tx>58||ty>42) return 'water';
  if(tx>=46&&tx<=57&&ty>=24&&ty<=40) return (tx===46||tx===57||ty===24||ty===40)?'stone':'dungeon';
  if(tx>=40&&ty>=20) return ((tx+ty)%4===0)?'ash':'corruption';
  if(tx>=16&&tx<40&&ty>=3&&ty<19) return ((tx+ty)%5===0)?'tower':'skyfield';
  if(tx>=4&&tx<14&&ty>=5&&ty<12) return ((tx+ty)%4===0)?'path':'village';
  if(ty===9||tx===28) return 'path';
  const noise=Math.sin(tx*.31)+Math.cos(ty*.27)+Math.sin((tx+ty)*.16);
  if(noise<-2.0) return 'water'; if(noise>1.65) return 'forest';
  if(((tx*31+ty*17)%47)===0) return 'stone'; return 'grass';
}

function drawWorld(camX,camY,w,h){
  ctx.fillStyle='#173a2c';ctx.fillRect(0,0,w,h);
  const size=48,startX=Math.max(0,Math.floor(camX/size)),startY=Math.max(0,Math.floor(camY/size));
  const endX=Math.min(60,Math.ceil((camX+w)/size)+1),endY=Math.min(44,Math.ceil((camY+h)/size)+1);
  const colors={grass:'#34794d',water:'#23658e',forest:'#184c34',stone:'#59616e',village:'#ae824f',path:'#90784e',skyfield:'#458b84',tower:'#74809a',corruption:'#5c306a',ash:'#544e55',dungeon:'#302b3b'};
  for(let ty=startY;ty<endY;ty++)for(let tx=startX;tx<endX;tx++){
    const type=tileType(tx,ty),x=tx*size-camX,y=ty*size-camY;ctx.fillStyle=colors[type];ctx.fillRect(x,y,size+1,size+1);
    if(type==='grass'&&(tx*17+ty*13)%5===0){ctx.fillStyle='#4b9860';ctx.fillRect(x+7,y+10,3,3);ctx.fillRect(x+30,y+29,3,3);}
    if(type==='water'){ctx.strokeStyle='#52a2c7';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(x+8,y+17+(tx+ty)%3*7);ctx.lineTo(x+40,y+17+(tx+ty)%3*7);ctx.stroke();}
    if(type==='forest'){ctx.fillStyle='#6b4b2b';ctx.fillRect(x+21,y+25,6,16);ctx.fillStyle='#227143';ctx.beginPath();ctx.arc(x+24,y+19,16,0,Math.PI*2);ctx.fill();}
    if(type==='stone'){ctx.fillStyle='#858f9e';ctx.beginPath();ctx.moveTo(x+24,y+8);ctx.lineTo(x+42,y+40);ctx.lineTo(x+7,y+41);ctx.closePath();ctx.fill();}
    if(type==='village'&&(tx+ty)%3===0){ctx.fillStyle='#6f4930';ctx.fillRect(x+8,y+17,32,24);ctx.fillStyle='#d9954a';ctx.beginPath();ctx.moveTo(x+5,y+18);ctx.lineTo(x+24,y+4);ctx.lineTo(x+43,y+18);ctx.fill();}
    if(type==='path'){ctx.fillStyle='#b09660';ctx.fillRect(x+8+(tx*7+ty*3)%25,y+9+(tx*5+ty*11)%28,4,3);}
    if(type==='skyfield'){ctx.fillStyle='#7dd7c9';ctx.beginPath();ctx.moveTo(x+24,y+13);ctx.lineTo(x+30,y+25);ctx.lineTo(x+24,y+34);ctx.lineTo(x+18,y+25);ctx.fill();}
    if(type==='tower'){ctx.strokeStyle='#a8b6d1';ctx.lineWidth=2;ctx.strokeRect(x+1,y+1,size-2,size-2);}
    if(type==='corruption'){ctx.fillStyle='#8f4fa0';ctx.beginPath();ctx.arc(x+24,y+24,5,0,Math.PI*2);ctx.fill();}
    if(type==='ash'){ctx.strokeStyle='#756d78';ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(x+48,y+48);ctx.stroke();}
    if(type==='dungeon'){ctx.strokeStyle='#4d455b';ctx.strokeRect(x+1,y+1,46,46);}
  }
  drawPortal(720-camX,456-camY);
}

function drawPortal(x,y){ctx.save();ctx.shadowColor='#72efff';ctx.shadowBlur=24;ctx.strokeStyle='#83f3ff';ctx.lineWidth=5;ctx.beginPath();ctx.ellipse(x,y,24,42,0,0,Math.PI*2);ctx.stroke();ctx.fillStyle='#7deeff22';ctx.fill();ctx.restore();}

function drawSafeZone(x,y){ctx.fillStyle='#64e5bd18';ctx.strokeStyle='#73f6d0aa';ctx.lineWidth=3;ctx.beginPath();ctx.arc(x,y,150,0,Math.PI*2);ctx.fill();ctx.stroke();ctx.fillStyle='#a9ffe7';ctx.font='12px Segoe UI';ctx.textAlign='center';ctx.fillText('SAFE ZONE',x,y-165);}
function drawPlayer(x,y,color,name,local=false){const c=`rgb(${color})`;ctx.save();ctx.fillStyle='#07131e88';ctx.beginPath();ctx.ellipse(x,y+17,18,7,0,0,Math.PI*2);ctx.fill();ctx.shadowColor=c;ctx.shadowBlur=local?20:10;ctx.fillStyle=c;ctx.beginPath();ctx.arc(x,y-8,9,0,Math.PI*2);ctx.fill();ctx.fillRect(x-10,y,20,22);ctx.fillStyle='#dcefff';ctx.fillRect(x-12,y+21,8,12);ctx.fillRect(x+4,y+21,8,12);ctx.strokeStyle='#f5ffff';ctx.lineWidth=2;ctx.strokeRect(x-10,y,20,22);ctx.strokeStyle='#b8f8ff';ctx.lineWidth=3;ctx.beginPath();ctx.moveTo(x+10,y+4);ctx.lineTo(x+27,y-17);ctx.stroke();ctx.restore();ctx.fillStyle='#fff';ctx.font='12px Segoe UI';ctx.textAlign='center';ctx.fillText(name,x,y-31);if(local&&player.attackFlash>0){ctx.strokeStyle='#9dfff4';ctx.lineWidth=5;ctx.beginPath();ctx.arc(x,y,42,-1.3,1.1);ctx.stroke();}}
function drawGuardian(x,y){const color=`rgb(${guardian.color})`;ctx.save();ctx.shadowColor=color;ctx.shadowBlur=34;ctx.fillStyle=color;ctx.strokeStyle='#fff';ctx.lineWidth=3;ctx.beginPath();if(guardian.shape==='wyrm'){ctx.ellipse(x,y,48,26,-.25,0,Math.PI*2);ctx.moveTo(x+35,y-9);ctx.lineTo(x+61,y-25);ctx.lineTo(x+51,y+3);}else if(guardian.shape==='knight'){ctx.moveTo(x,y-48);ctx.lineTo(x+34,y-15);ctx.lineTo(x+27,y+43);ctx.lineTo(x-27,y+43);ctx.lineTo(x-34,y-15);ctx.closePath();}else{ctx.moveTo(x,y-42);ctx.lineTo(x+37,y+27);ctx.lineTo(x,y+43);ctx.lineTo(x-37,y+27);ctx.closePath();}ctx.fill();ctx.stroke();ctx.restore();ctx.fillStyle='#eaffff';ctx.font='bold 12px Segoe UI';ctx.textAlign='center';ctx.fillText(guardian.name,x,y-56);}
function drawMonster(x,y,m){const color=`rgb(${m.color})`,size=m.unique?28:15+(m.max_hp>100?4:0);ctx.save();ctx.shadowColor=color;ctx.shadowBlur=m.unique?30:12;ctx.fillStyle=color;ctx.strokeStyle=m.unique?'#fff':'transparent';ctx.lineWidth=3;ctx.beginPath();if(m.unique){for(let i=0;i<10;i++){const a=-Math.PI/2+i*Math.PI/5,r=i%2?15:size,px=x+Math.cos(a)*r,py=y+Math.sin(a)*r;i?ctx.lineTo(px,py):ctx.moveTo(px,py);}ctx.closePath();}else if(m.kind.includes('Wisp')||m.kind.includes('Mage')){ctx.moveTo(x,y-18);ctx.lineTo(x+17,y+14);ctx.lineTo(x-17,y+14);}else{ctx.arc(x,y,size,0,Math.PI*2);}ctx.fill();ctx.stroke();ctx.restore();const bar=m.unique?70:40;ctx.fillStyle='#08131c';ctx.fillRect(x-bar/2,y-38,bar,6);ctx.fillStyle=m.unique?'#ff48b0':'#ef5f70';ctx.fillRect(x-bar/2,y-38,bar*m.hp/m.max_hp,6);ctx.fillStyle=m.unique?'#ffb5df':'#eefcff';ctx.font=m.unique?'bold 12px Segoe UI':'11px Segoe UI';ctx.textAlign='center';ctx.fillText(m.unique?`UNIQUE · ${m.kind}`:m.kind,x,y-46);}
function drawLoot(x,y,kind){const color=kind==='potion'?'#ff6f9c':kind==='gear'?'#8be9ff':'#ffd35b';ctx.save();ctx.shadowColor=color;ctx.shadowBlur=18;ctx.fillStyle=color;ctx.fillRect(x-7,y-7,14,14);ctx.restore();}
function drawNpc(x,y,npc){const near=Math.hypot(player.x-npc.x,player.y-npc.y)<95;ctx.save();ctx.fillStyle=`rgb(${npc.color})`;ctx.shadowColor=ctx.fillStyle;ctx.shadowBlur=12;ctx.beginPath();ctx.arc(x,y-8,9,0,Math.PI*2);ctx.fill();ctx.fillRect(x-9,y,18,24);ctx.restore();ctx.fillStyle='#fff';ctx.font='bold 11px Segoe UI';ctx.textAlign='center';ctx.fillText(`${npc.name} · ${npc.role}`,x,y-28);if(near){ctx.fillStyle='#ffe58f';ctx.fillText('F · INTERACT',x,y+43);}}
function drawChest(x,y){const near=Math.hypot(player.x-(x+(player.x-innerWidth/2)),player.y-(y+(player.y-innerHeight/2)))<95;ctx.save();ctx.fillStyle='#c89343';ctx.strokeStyle='#ffe393';ctx.lineWidth=2;ctx.shadowColor='#ffd35b';ctx.shadowBlur=18;ctx.fillRect(x-17,y-11,34,22);ctx.strokeRect(x-17,y-11,34,22);ctx.restore();if(near){ctx.fillStyle='#ffe58f';ctx.font='11px Segoe UI';ctx.textAlign='center';ctx.fillText('F · OPEN VAULT',x,y-25);}}
function drawEcho(x,y){const action=echo.current_action||'patrol',combat=['strike','circle','power'].includes(action);ctx.save();ctx.shadowColor='#c27dff';ctx.shadowBlur=combat?28:18;ctx.fillStyle='#bd7cff';ctx.beginPath();ctx.arc(x,y,14,0,Math.PI*2);ctx.fill();ctx.strokeStyle='#f6eaff';ctx.lineWidth=2;ctx.stroke();if(combat){const pulse=18+(echo.attack_pulse%8);ctx.strokeStyle='#ffb4fa99';ctx.beginPath();ctx.arc(x,y,pulse,0,Math.PI*2);ctx.stroke();}ctx.restore();ctx.fillStyle='#ead7ff';ctx.font='11px Segoe UI';ctx.textAlign='center';const target=echo.target_name?` · ${echo.target_name}`:'';ctx.fillText(`Echo [AI] · ${action.toUpperCase()}${target}`,x,y-25);ctx.fillStyle='#101522';ctx.fillRect(x-24,y+23,48,4);ctx.fillStyle='#f2b84b';ctx.fillRect(x-24,y+23,48*Math.max(0,echo.energy||0)/(echo.max_energy||60),4);}
function flash(text){message.textContent=text;message.classList.add('show');clearTimeout(flash.timer);flash.timer=setTimeout(()=>message.classList.remove('show'),1800);}
function loop(now){const dt=Math.min(.05,(now-lastFrame)/1000);lastFrame=now;update(dt,now);draw();requestAnimationFrame(loop);} requestAnimationFrame(loop);
