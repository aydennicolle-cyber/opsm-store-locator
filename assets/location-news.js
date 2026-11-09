(function (root) {
  'use strict';
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const safeUrl = value => { try { const u = new URL(value); return u.protocol === 'https:' ? escape(u.href) : '#'; } catch { return '#'; } };
  const dateLabel = value => {
    if (!value) return 'Publication date unknown';
    if (value.length === 4) return value;
    return new Intl.DateTimeFormat('en-AU', value.length === 7 ? {month:'long',year:'numeric',timeZone:'UTC'} : {day:'numeric',month:'short',year:'numeric',timeZone:'UTC'}).format(new Date(value.length === 7 ? value + '-01T00:00:00Z' : value + 'T00:00:00Z'));
  };
  const orderedVersions = event => [...event.versions].reverse().sort((a,b) => b.recorded_at.localeCompare(a.recorded_at) || (b.published_on || '').localeCompare(a.published_on || ''));
  const latest = event => orderedVersions(event)[0];
  const storyDate = event => event.versions.map(v=>v.published_on || "").sort().at(-1) || null;
  const kinds = {news:'News', background:'Background', unchanged:'Existing record', unresolved:'Unresolved lead'};
  function select(data, subject = {}) {
    const selected = (data?.events || []).map(event => {
      const relations = subject.all ? event.relations : event.relations.filter(r => r.entity_id === subject.store_id || r.entity_id === subject.place_id);
      return {event, relations, area: relations.length > 0 && relations.every(r => r.kind.startsWith('area_'))};
    }).filter(x => subject.all || x.relations.length);
    // A local branch announcement carries the relevant detail of its network parent.
    const parents = new Set(selected.map(x => x.event.parent_event_id).filter(Boolean));
    return selected.filter(x => subject.all || !parents.has(x.event.event_id)).sort((a,b) =>
      (storyDate(b.event) || '').localeCompare(storyDate(a.event) || '') || a.event.event_id.localeCompare(b.event.event_id));
  }
  function facts(version) {
    return version.statements.map(s => `<p>${s.kind === 'dataset_observation' ? '<span class="news-label">Database observation</span> ' : s.kind === 'context' ? '<span class="news-label">Context</span> ' : ''}${escape(s.text)}</p>`).join('');
  }
  function sources(version) {
    return `<ul class="news-sources">${version.sources.map(s => `<li><a href="${safeUrl(s.url)}" target="_blank" rel="noopener noreferrer">${escape(/^https?:\/\//.test(s.title) ? 'Source document' : s.title)} ↗</a></li>`).join('')}</ul>`;
  }
  function evidence(item, checks) {
    const {event, relations} = item, v = latest(event), history = orderedVersions(event).slice(1);
    const urls = new Set(v.sources.map(s => s.url));
    const attempts = checks.filter(c => urls.has(c.source_url));
    const checkByUrl = new Map();
    attempts.sort((a,b) => a.attempted_at.localeCompare(b.attempted_at)).forEach(c => checkByUrl.set(c.source_url, c));
    const unresolved = [...checkByUrl.values()].filter(c => c.status !== 'retrieved');
    const metrics = v.metrics.map(m => `<li><strong>${escape(m.name)}: ${escape(m.value)} ${escape(m.currency || '')} ${escape(m.unit)}</strong><small>${escape(m.period)} · ${escape(m.definition)} ${escape(m.uncertainty)}</small></li>`).join('');
    return `${facts(v)}
        ${v.timing ? `<p><strong>Timing</strong> ${escape(v.timing)}</p>` : ''}
        ${v.uncertainty ? `<p class="news-note">${escape(v.uncertainty)}</p>` : ''}
        ${relations.map(r=>`<p class="news-note">${escape(r.basis)} ${r.source_urls?.filter(url=>!urls.has(url)).map(url=>`<a href="${safeUrl(url)}" target="_blank" rel="noopener noreferrer">Location evidence ↗</a>`).join(' ') || ''}</p>`).join('')}
        ${metrics ? `<ul class="news-metrics">${metrics}</ul>` : ''}${sources(v)}
        <p class="news-note">Recorded ${escape(dateLabel(v.recorded_at.slice(0,10)))}. ${escape(v.date_basis)}</p>
        ${unresolved.map(c=>`<p class="news-note">Source check ${escape(c.status)} on ${escape(c.attempted_at.slice(0,10))}. ${escape(c.note)}${c.last_success_at ? ` Last successful read: ${escape(c.last_success_at.slice(0,10))}.` : ''}</p>`).join('')}
        ${history.length ? `<div class="news-history"><h5>Earlier evidence</h5>${history.map(h=>`<section><strong>${escape(dateLabel(h.published_on))} · ${escape(h.title)}</strong>${facts(h)}${sources(h)}</section>`).join('')}</div>` : ''}
    `;
  }

  // Group only dated reporting with a shared source and identical geographic scope.
  // These are display groups: event IDs and their evidence histories stay independent.
  function groupStories(items) {
    const buckets = new Map();
    for (const item of items) {
      const v = latest(item.event), date = storyDate(item.event);
      if (item.event.kind !== 'news' || !/^\d{4}-\d{2}-\d{2}$/.test(date || '') || v.published_on !== date ||
          v.metrics.length || v.statements.some(s => s.kind !== 'source_report')) continue;
      const geography = item.relations.map(r => `${r.kind}:${r.entity_id}`).sort().join('|');
      if (!geography) continue;
      for (const source of v.sources) {
        let url;
        try { url = new URL(source.url); } catch { continue; }
        if (url.protocol !== 'https:' || !source.title || /^https?:/.test(source.title) ||
            /^\/(?:news|newsroom|media|stores|venues|locations)?\/?$/i.test(url.pathname) ||
            !v.statements.some(s => s.source_ids?.includes(source.source_id))) continue;
        const key = JSON.stringify([source.url, date, item.event.scope, geography]);
        if (!buckets.has(key)) buckets.set(key, {source, members:[]});
        buckets.get(key).members.push(item);
      }
    }
    const assigned = new Map();
    for (const bucket of [...buckets.values()].sort((a,b) => b.members.length - a.members.length)) {
      const members = bucket.members.filter(item => !assigned.has(item));
      if (members.length < 2) continue;
      const group = {members, source:bucket.source};
      members.forEach(item => assigned.set(item, group));
    }
    const seen = new Set();
    return items.flatMap(item => {
      const group = assigned.get(item) || {members:[item], source:null};
      if (seen.has(group)) return [];
      seen.add(group);
      return [group];
    });
  }

  const normalise = value => value.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
  function compactHeading(version) {
    const text = version.statements[0].text;
    const repeated = normalise(text).startsWith(normalise(version.title));
    return {title: repeated ? text : version.title, body: repeated ? '' : text};
  }
  function sourceLabel(source) {
    const parts = source.title.split(/\s+\|\s+/);
    if (parts.length > 1) return parts.at(-1);
    try { return new URL(source.url).hostname.replace(/^www\./, ''); } catch { return 'Source'; }
  }
  function groupedStatement(item, source) {
    const text = latest(item.event).statements[0].text;
    const publisher = sourceLabel(source);
    // Remove repeated attribution only when it is an exact prefix; keep status wording.
    if (text.startsWith(publisher + ' ')) {
      const match = text.slice(publisher.length + 1).match(/^(?:reported|described|reports|describes) (.+?) as (.+)$/);
      if (match) return `<strong>${escape(match[1])}</strong> — ${escape(match[2])}`;
    }
    return escape(text);
  }
  function card(group, checks, index) {
    const item = group.members[0], {event, relations, area} = item, v = latest(event);
    const grouped = group.members.length > 1;
    const heading = grouped ? {title:group.source.title.split(/\s+\|\s+/)[0], body:''} : compactHeading(v);
    const search = group.members.map(x => {
      const version = latest(x.event);
      return version.title + ' ' + version.statements.map(s=>s.text).join(' ');
    }).join(' ').toLowerCase();
    const historyCount = group.members.reduce((n,x) => n + x.event.versions.length - 1, 0);
    const source = group.source || v.sources[0];
    return `<article class="news-item" data-news-index="${index}" data-news-kind="${escape(event.kind)}" data-news-area="${area}" data-news-search="${escape(search)}">
      <div class="news-meta"><span>${area ? 'Area news' : kinds[event.kind]}</span><time>${grouped ? 'Reported ' : ''}${escape(dateLabel(storyDate(event)))}</time></div>
      <h4>${escape(heading.title)}</h4>
      ${source ? `<a class="news-attribution" href="${safeUrl(source.url)}" target="_blank" rel="noopener noreferrer">${escape(sourceLabel(source))} ↗</a>` : ''}
      ${grouped ? `<ul class="news-digest">${group.members.map(x=>`<li>${groupedStatement(x,group.source)}</li>`).join('')}</ul>` : heading.body ? `<p>${escape(heading.body)}</p>` : ''}
      ${area ? `<p class="news-connection">${escape([...new Set(relations.map(r => r.label + (r.distance_km != null ? ` · ${r.distance_km.toFixed(2)} km straight-line` : '')))].join(' / '))}</p>` : !relations.length && event.scope === 'geography_review' ? '<p class="news-connection">Area link under review · retained in the wider feed</p>' : ''}
      <details><summary>Sources & history${historyCount ? ` · ${historyCount} earlier update${historyCount === 1 ? '' : 's'}` : ''}</summary>
        ${group.members.map(x=>`<section class="news-evidence">${grouped ? `<h5>${escape(latest(x.event).title)}</h5>` : ''}${evidence(x,checks)}</section>`).join('')}
      </details>
    </article>`;
  }
  let renderId = 0;
  function render(data, subject = {}) {
    if (!data) return '<section class="location-news"><h3>News & history</h3><p>News could not be loaded. Reload to try again.</p></section>';
    const groups = groupStories(select(data, subject)), compact = !subject.all;
    const count = `${groups.length} ${groups.length === 1 ? 'story' : 'stories'}`;
    const feedId = `news-feed-${++renderId}`;
    const heading = `<span class="news-heading"><span class="news-eyebrow">Location intelligence</span><span class="news-title">${subject.all ? 'Retail news & history' : 'News & history'}</span></span><span class="news-count">${count}</span>`;
    return `<section class="location-news${compact ? ' news-collapsible' : ''}" aria-label="News and history" data-news-expanded="${!compact}">
      ${compact && groups.length ? `<button type="button" class="news-toggle" data-news-toggle aria-expanded="false" aria-controls="${feedId}" aria-label="Expand news and history">${heading}<span class="news-chevron" aria-hidden="true">⌄</span></button>` : `<header>${heading}</header>`}
      ${groups.length ? `<div id="${feedId}"><div class="news-controls"><label>Show<select data-news-filter><option value="all">All history</option><option value="news">News</option><option value="background">Background & existing records</option><option value="area">Area news</option></select></label><label>Find in history<input type="search" data-news-query placeholder="Search stories"></label></div><div class="news-feed">${groups.map((x,i)=>card(x,data.checks || [],i)).join('')}</div><p class="news-filter-empty" hidden>No stories match these filters.</p></div>${compact ? `<button type="button" class="news-expand-link" data-news-toggle aria-expanded="false" aria-controls="${feedId}">Show all ${count}</button>` : ''}` : '<p class="news-empty">No linked news is recorded yet. This does not establish that nothing has changed.</p>'}
    </section>`;
  }
  function filter(section) {
    const mode = section.querySelector('[data-news-filter]').value, query = section.querySelector('[data-news-query]').value.trim().toLowerCase();
    let count = 0;
    section.querySelectorAll('.news-item').forEach(item => {
      const matches = mode === 'all' || mode === 'area' && item.dataset.newsArea === 'true' || mode === 'news' && item.dataset.newsKind === 'news' || mode === 'background' && ['background','unchanged'].includes(item.dataset.newsKind);
      item.hidden = !matches || !item.dataset.newsSearch.includes(query);
      if (!item.hidden) count++;
    });
    section.querySelector('.news-filter-empty').hidden = count > 0;
    section.querySelector('.news-count').textContent = `${count} ${count === 1 ? 'story' : 'stories'}`;
  }
  function toggle(section) {
    const expanded = section.dataset.newsExpanded !== 'true';
    section.dataset.newsExpanded = String(expanded);
    section.querySelectorAll('[data-news-toggle]').forEach(button => button.setAttribute('aria-expanded', String(expanded)));
    section.querySelector('.news-toggle').setAttribute('aria-label', `${expanded ? 'Collapse' : 'Expand'} news and history`);
    const count = section.querySelectorAll('.news-item').length;
    section.querySelector('.news-expand-link').textContent = expanded ? 'Show latest only' : `Show all ${count} ${count === 1 ? 'story' : 'stories'}`;
    if (!expanded) {
      section.querySelector('[data-news-filter]').value = 'all';
      section.querySelector('[data-news-query]').value = '';
      filter(section);
      section.querySelectorAll('.news-item details').forEach(detail => { detail.open = false; });
    }
  }
  root.LocationNews = {render, select, groupStories, compactHeading, latest, dateLabel};
  if (typeof module !== 'undefined') module.exports = root.LocationNews;
  if (typeof document !== 'undefined') document.addEventListener('click', e => {
    const button = e.target.closest('[data-news-toggle]');
    if (button) toggle(button.closest('.location-news'));
  });
  if (typeof document !== 'undefined') ['input','change'].forEach(type => document.addEventListener(type, e => {
    if (e.target.matches('[data-news-query],[data-news-filter]')) filter(e.target.closest('.location-news'));
  }));
})(typeof window === 'undefined' ? globalThis : window);
