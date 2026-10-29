/* OG VHS: progressive enhancement for the static archive. No external runtime. */
(() => {
  const base = document.body.dataset.base || '/';
  const to = (path = '') => base + path.replace(/^\/+|\/+$/g, '') + (path ? '/' : '');
  const content = document.getElementById('archive-data');
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function element(tag, cls, text) {
    const el = document.createElement(tag);
    if (cls) el.className = cls;
    if (text !== undefined) el.textContent = text;
    return el;
  }
  function createCard(v) {
    const card = element('article', 'vine-card');
    const cover = element('a');
    cover.href = to(`v/${v.vineId}`);
    cover.setAttribute('aria-label', `View clip ${v.vineId}`);
    const thumbnail = element('div', 'vine-thumb');
    if (v.videoUrl) {
      const vid = element('video');
      vid.muted = true;
      vid.loop = true;
      vid.playsInline = true;
      vid.preload = 'none';
      vid.dataset.previewSrc = v.videoUrl;
      vid.setAttribute('aria-label', `Preview of Vine ${v.vineId}`);
      if (v.thumbnailUrl) vid.poster = v.thumbnailUrl;
      thumbnail.append(vid);
    } else if (v.thumbnailUrl) {
      const img = element('img');
      img.src = v.thumbnailUrl;
      img.loading = 'lazy';
      img.alt = `Thumbnail for Vine ${v.vineId}`;
      thumbnail.append(img);
    } else {
      const missing = element('div', 'no-media', 'OG');
      missing.append(element('span', '', 'MEDIA PENDING'));
      thumbnail.append(missing);
    }
    thumbnail.append(element('span', 'thumb-id', v.vineId));
    thumbnail.append(element('span', 'thumb-play', '▶'));
    cover.append(thumbnail);
    const heading = element('h3');
    const label = element('a', '', (v.rawCaption || (v.idKind === 'archive' ? `Recovered video · ${v.sourceFilename || v.vineId}` : 'Caption not recovered')).replace(/\n/g, ' ').slice(0, 110));
    label.href = cover.href;
    heading.append(label);
    const meta = element('p', 'card-meta');
    meta.append(element('span', '', v.dateLabel));
    if (!v.rawCaption || !v.publishedAt) meta.append(element('span', 'status', '• Metadata pending'));
    card.append(cover, heading, meta);
    return card;
  }
  function activatePreviews(container) {
    // Hover is only available with a fine pointer. Browsers may prevent audio
    // until the visitor has interacted with the page; fall back to muted preview.
    if (!container || reduced || !matchMedia('(hover: hover) and (pointer: fine)').matches) return;
    container.querySelectorAll('video[data-preview-src]').forEach(video => {
      const card = video.closest('.vine-card');
      if (!card) return;
      video.loop = true;
      const soundButton = element('button', 'preview-audio', 'ENABLE SOUND');
      soundButton.type = 'button';
      soundButton.title = 'Your browser blocked hover audio. Click to enable sound.';
      soundButton.setAttribute('aria-label', 'Enable audio preview for this clip');
      soundButton.addEventListener('click', event => {
        event.preventDefault();
        event.stopPropagation();
        video.muted = false;
        video.play().then(() => soundButton.remove()).catch(() => {
          video.muted = true;
        });
      });
      card.addEventListener('pointerenter', () => {
        if (!video.src) video.src = video.dataset.previewSrc;
        video.muted = false;
        video.volume = 1;
        video.play().catch(() => {
          // Audio autoplay can be blocked by browser settings. Never break preview.
          if (!card.matches(':hover')) return;
          video.muted = true;
          card.append(soundButton);
          video.play().catch(() => {});
        });
      });
      card.addEventListener('pointerleave', () => {
        soundButton.remove();
        video.pause();
        video.muted = true;
        try { video.currentTime = 0; } catch (_) {}
      });
    });
  }

  if (content) {
    let all = [];
    try { all = JSON.parse(content.textContent); } catch (err) { console.error('Archive data not available.', err); }
    const input = document.getElementById('archive-search');
    const sort = document.getElementById('archive-sort');
    const results = document.getElementById('results');
    const count = document.getElementById('result-count');
    const empty = document.getElementById('empty-results');
    const more = document.getElementById('load-more');
    const tag = (document.getElementById('archive-mode')?.dataset.tag || '').toLowerCase();
    let showing = 24;
    let current = [];
    const params = new URLSearchParams(location.search);
    if (input && params.has('q')) input.value = params.get('q') || '';
    function sorted(vs) {
      const mode = sort?.value || 'newest';
      return [...vs].sort((a,b) => {
        if (mode === 'restored') {
          return (b.restoredAt || '').localeCompare(a.restoredAt || '') || a.vineId.localeCompare(b.vineId);
        }
        if (!a.publishedAt && !b.publishedAt) return a.vineId.localeCompare(b.vineId);
        if (!a.publishedAt) return 1;
        if (!b.publishedAt) return -1;
        const order = a.publishedAt.localeCompare(b.publishedAt);
        return (mode === 'oldest' ? order : -order) || a.vineId.localeCompare(b.vineId);
      });
    }
    function refresh(restart) {
      if (restart) showing = 24;
      const query = (input?.value || '').trim().toLowerCase().replace(/^#/, '');
      current = sorted(all.filter(v =>
        (!tag || v.tags.includes(tag)) &&
        (!query || [v.vineId, v.sourceFilename || '', v.rawCaption || '', ...v.tags].some(s => s.toLowerCase().includes(query)))
      ));
      count.textContent = `${current.length} RECORD${current.length === 1 ? '' : 'S'}`;
      results.replaceChildren(...current.slice(0, showing).map(createCard));
      activatePreviews(results);
      empty.style.display = current.length ? 'none' : 'block';
      empty.textContent = all.length ? 'No matching Vines. Try another search.' : 'No clips are cataloged yet. The vault will fill as original files are recovered.';
      more.style.display = showing < current.length ? 'block' : 'none';
    }
    let timer;
    input?.addEventListener('input', () => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        const p = new URLSearchParams(location.search);
        if (input.value.trim()) p.set('q', input.value.trim()); else p.delete('q');
        history.replaceState(null, '', location.pathname + (p.size ? '?' + p : ''));
        refresh(true);
      }, 140);
    });
    sort?.addEventListener('change', () => refresh(true));
    more?.addEventListener('click', () => { showing += 24; refresh(false); });
    refresh(true);
  } else {
    activatePreviews(document);
  }
  const copy = document.getElementById('copy-link');
  copy?.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(location.href);
      copy.textContent = 'LINK COPIED ✓';
    } catch (_) {
      const temp = document.createElement('input');
      temp.value = location.href;
      document.body.append(temp);
      temp.select();
      try { document.execCommand('copy'); copy.textContent = 'LINK COPIED ✓'; }
      catch (_) { copy.textContent = 'COPY URL FROM ADDRESS BAR'; }
      temp.remove();
    }
  });
  const loop = document.getElementById('toggle-loop');
  const player = document.getElementById('vine-player');
  if (player && loop) {
    player.loop = true;
    loop.setAttribute('aria-pressed', 'true');
    loop.textContent = 'LOOP ON ↻';
  }
  loop?.addEventListener('click', () => {
    const video = document.getElementById('vine-player');
    if (!video) return;
    video.loop = !video.loop;
    loop.setAttribute('aria-pressed', String(video.loop));
    loop.textContent = video.loop ? 'LOOP ON ↻' : 'LOOP OFF';
  });
})();
