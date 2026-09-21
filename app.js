'use strict';
const CONFIG = [
  {id:'24311',name:'西安万达影城（高新万达广场店）',format:'杜比影院'},
  {id:'39869',name:'寰映影城（西安荟聚激光IMAX店）',format:'激光 IMAX'}
];
let snapshot = null;
const weekday = date => '周' + '日一二三四五六'[new Date(date + 'T12:00:00+08:00').getUTCDay()];
const normalized = text => text.normalize('NFKC').replace(/\s/g,'').toUpperCase();
function allowed(id, hall) {
  const h = normalized(hall);
  return id === '24311' ? (h.includes('杜比影院') || h.includes('DOLBYCINEMA')) : id === '39869' && h.includes('IMAX') && (h.includes('激光') || h.includes('LASER'));
}
function avengers(name) {return /复仇者联盟4|复联4|AVENGERS:ENDGAME/.test(normalized(name));}
function el(tag, text, cls) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (cls) node.className = cls;
  return node;
}
function render() {
  const app = document.getElementById('app');
  app.replaceChildren();
  for (const config of CONFIG) {
    const cinema = snapshot?.cinemas?.find(c => c.id === config.id);
    const panel = el('section', undefined, 'cinema' + (config.id === '39869' ? ' imax' : ''));
    panel.append(el('div', config.format + ' · 专属影厅', 'format'), el('h2',config.name));
    const link = el('a','猫眼购票 ↗','buy');
    link.href = 'https://www.maoyan.com/cinema/' + config.id;
    link.target = '_blank'; link.rel = 'noopener noreferrer';
    panel.append(link);
    if (cinema?.updated_at) {
      const date = new Date(cinema.updated_at);
      panel.append(el('p','最近成功更新：' + date.toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',hour12:false}), 'meta'));
      if (Date.now() - date.getTime() > 90 * 60000) panel.append(el('p','数据超过 90 分钟未更新，请以购票页为准。','warning meta'));
    }
    if (cinema?.error) panel.append(el('p',cinema.error,'warning meta'));
    if (!cinema?.updated_at) panel.append(el('p','尚未取得排片，请等待后台成功更新。','empty'));
    else {
      const slots = cinema.slots.filter(s => allowed(config.id,s.hall) && new Date(s.start).getTime() > Date.now()
        && (!document.getElementById('saturday').checked || weekday(s.date) === '周六')
        && (!document.getElementById('avengers').checked || avengers(s.movie)))
        .sort((a,b) => a.start.localeCompare(b.start));
      const days = new Map();
      for (const s of slots) {
        if (!days.has(s.date)) days.set(s.date,new Map());
        const movies = days.get(s.date);
        if (!movies.has(s.movie)) movies.set(s.movie,[]);
        movies.get(s.movie).push(s);
      }
      if (!slots.length) panel.append(el('p',cinema.error ? '缓存中没有符合条件的场次，当前排片尚未确认。' : '暂无符合条件的排片。','empty'));
      for (const [date,movies] of days) {
        const day = el('div',undefined,'day');
        day.append(el('h3',date + ' · ' + weekday(date)));
        for (const [name,shows] of movies) {
          const movie = el('article',undefined,'movie');
          if (weekday(date) === '周六' && avengers(name)) movie.append(el('div','特别关注 · 周六《复联4》','focus'));
          movie.append(el('h4',name));
          const grid = el('div',undefined,'times');
          for (const s of shows) {
            const chip = el('div',undefined,'slot');
            chip.append(el('div',s.time,'time'),el('div',s.hall,'hall'));
            if (!s.bookable) chip.append(el('div','开售状态待确认','hall'));
            grid.append(chip);
          }
          movie.append(grid); day.append(movie);
        }
        panel.append(day);
      }
    }
    app.append(panel);
  }
}
async function refresh() {
  const button = document.getElementById('refresh');
  button.disabled = true;
  try {
    const response = await fetch('schedules.json?t=' + Date.now(),{cache:'no-store'});
    if (!response.ok) throw new Error('HTTP ' + response.status);
    const data = await response.json();
    if (!Array.isArray(data.cinemas) || data.cinemas.some(c => !Array.isArray(c.slots))) throw new Error('排片数据格式错误');
    snapshot = data;
    document.getElementById('status').textContent = '显示两家影院 · 北京时间 · ' + new Date(data.generated_at).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',hour12:false});
  } catch (error) {
    document.getElementById('status').textContent = '读取排片失败：' + error.message + (snapshot ? '；保留上次显示的数据。' : '；请稍后刷新。');
  } finally {
    render(); button.disabled = false;
  }
}
document.getElementById('saturday').addEventListener('change',render);
document.getElementById('avengers').addEventListener('change',render);
document.getElementById('refresh').addEventListener('click',refresh);
render(); refresh(); setInterval(refresh,5 * 60 * 1000);
