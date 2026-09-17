// Hamara Bagh shared helpers — vanilla JS only, no build step.

// ---------------------------------------------------------------------------
// Client identity (no-login journal is keyed by a browser-generated id)
// ---------------------------------------------------------------------------
function getClientId() {
  let id = localStorage.getItem('greenmitra_client_id');
  if (!id) {
    id = 'client_' + Math.random().toString(36).slice(2) + Date.now();
    localStorage.setItem('greenmitra_client_id', id);
  }
  return id;
}

// ---------------------------------------------------------------------------
// Fetch wrapper — always JSON, throws with the API's error message
// ---------------------------------------------------------------------------
async function api(path, options = {}) {
  const res = await fetch(path, options);
  let data = null;
  try {
    data = await res.json();
  } catch (err) {
    /* some error pages have no JSON body */
  }
  if (!res.ok) {
    throw new Error((data && data.error) || 'Request failed (' + res.status + ')');
  }
  return data;
}

// ---------------------------------------------------------------------------
// Shared label / colour maps (kept in sync with the backend vocabulary)
// ---------------------------------------------------------------------------
const CATEGORY_META = {
  vegetable: { emoji: '🥬', tile: 'bg-leaf-50', text: 'text-leaf-700' },
  herb: { emoji: '🌿', tile: 'bg-sky-100', text: 'text-sky-600' },
  flower: { emoji: '🌸', tile: 'bg-blush-100', text: 'text-blush-600' },
  tree: { emoji: '🌳', tile: 'bg-leaf-100', text: 'text-leaf-800' },
  succulent: { emoji: '🌵', tile: 'bg-sun-100', text: 'text-[#8a6d1f]' },
  houseplant: { emoji: '🪴', tile: 'bg-terra-100', text: 'text-terra-700' },
  other: { emoji: '🌱', tile: 'bg-leaf-50', text: 'text-leaf-700' },
};

const PLANT_EMOJI = {
  'tomato': '🍅',
  'mint': '🌿',
  'aloe vera': '🪴',
  'money plant (pothos)': '🍃',
  'snake plant': '🪴',
  'marigold': '🌼',
  'chili pepper': '🌶️',
  'basil': '🌿',
  'rose': '🌹',
  'hibiscus': '🌺',
  'spinach': '🥬',
  'neem tree': '🌳',
  'bougainvillea': '🌸',
  'fenugreek (methi)': '🌿',
  'lemon tree': '🍋',
  'cactus (barrel/golden)': '🌵',
  'petunia': '🌸',
  'ficus (rubber plant)': '🪴',
  'curry leaf plant': '🌿',
  'zinnia': '🌸',
  'zz plant': '🪴',
  'okra (bhindi)': '🫛',
  'brinjal (baingan)': '🍆',
  'cucumber (kheera)': '🥒',
  'carrot (gajar)': '🥕',
  'peas (matar)': '🫛',
  'cauliflower (phool gobhi)': '🥦',
  'mustard greens (sarson)': '🥬',
  'capsicum (shimla mirch)': '🫑',
  'coriander (dhania)': '🌿',
  'lemongrass': '🌿',
  'tulsi (holy basil)': '🌿',
  'fennel (saunf)': '🌿',
  'dill (soya)': '🌿',
  'rosemary': '🌿',
  'jasmine (chambeli)': '💮',
  'chrysanthemum (gul-e-dawoodi)': '🏵️',
  'dahlia': '🌷',
  'sunflower': '🌻',
  'vinca (sadabahar)': '🌸',
  'guava (amrood)': '🍐',
  'papaya': '🥭',
  'areca palm': '🌴',
  'cabbage': '🥬',
  'onion (pyaaz)': '🧅',
  'gladiolus': '💐',
  // Reference-only plants that appear in city growing guides
  'apple': '🍎',
  'grape': '🍇',
  'peach': '🍑',
  'cherry': '🍒',
  'almond': '🌰',
  'coconut': '🥥',
  'potato': '🥔',
  'citrus': '🍊',
};

const VERDICT_META = {
  excellent_match: { label: 'Excellent match', badge: 'bg-leaf-600 text-white', bar: 'bg-leaf-600', text: 'text-leaf-700' },
  good_match: { label: 'Good match', badge: 'bg-leaf-100 text-leaf-800', bar: 'bg-leaf-400', text: 'text-leaf-700' },
  risky: { label: 'Risky', badge: 'bg-sun-100 text-[#8a6d1f]', bar: 'bg-sun-400', text: 'text-[#8a6d1f]' },
  not_recommended: { label: 'Not recommended', badge: 'bg-blush-100 text-blush-600', bar: 'bg-blush-500', text: 'text-blush-600' },
};

const WATER_LABEL = { very_low: 'Very low', low: 'Low', medium: 'Medium', high: 'High' };
const SUN_LABEL = { full_sun: 'Full sun', part_shade: 'Part shade', full_shade: 'Full shade' };
const DIFFICULTY_LABEL = { very_easy: 'Beginner-proof', easy: 'Easy', medium: 'Medium', hard: 'Challenging' };
const DIFFICULTY_BADGE = {
  very_easy: 'bg-leaf-100 text-leaf-800',
  easy: 'bg-sky-100 text-sky-600',
  medium: 'bg-sun-100 text-[#8a6d1f]',
  hard: 'bg-blush-100 text-blush-600',
};
const SEASON_LABEL = { rabi: 'Rabi (winter)', kharif: 'Kharif (summer)', rabi_and_kharif: 'Rabi & Kharif', perennial: 'Perennial' };
const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

// ---------------------------------------------------------------------------
// Tiny formatting helpers
// ---------------------------------------------------------------------------
function categoryMeta(category) {
  return CATEGORY_META[category] || CATEGORY_META.other;
}

function plantEmoji(plant) {
  const key = (plant.common_name || '').toLowerCase();
  return PLANT_EMOJI[key] || categoryMeta(plant.category).emoji;
}

function verdictMeta(verdict) {
  return VERDICT_META[verdict] || VERDICT_META.risky;
}

function esc(value) {
  return String(value == null ? '' : value).replace(/[&<>"']/g, function (ch) {
    return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch];
  });
}

function titleCase(str) {
  return String(str || '').replace(/_/g, ' ').replace(/\b\w/g, function (c) { return c.toUpperCase(); });
}

function chip(text, cls) {
  return '<span class="chip ' + cls + '">' + text + '</span>';
}

function setMetaTag(name, content, isProperty) {
  const sel = isProperty ? 'meta[property="' + name + '"]' : 'meta[name="' + name + '"]';
  const el = document.querySelector(sel);
  if (el) el.setAttribute('content', content);
}

function setMeta(title, description) {
  document.title = title;
  setMetaTag('description', description);
  setMetaTag('og:title', title, true);
  setMetaTag('og:description', description, true);
}

function timeAgo(iso) {
  if (!iso) return 'never';
  const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86400000);
  if (days <= 0) return 'today';
  if (days === 1) return 'yesterday';
  if (days < 30) return days + ' days ago';
  const months = Math.floor(days / 30);
  return months === 1 ? 'a month ago' : months + ' months ago';
}

// ---------------------------------------------------------------------------
// Plant name -> id lookup (cached; drives clickable "star plant" chips)
// ---------------------------------------------------------------------------
let _plantsByNamePromise = null;

function plantIdByName(name) {
  if (_plantsByNamePromise === null) {
    _plantsByNamePromise = api('/api/plants?max_results=200').then(function (data) {
      const map = {};
      (data.results || []).forEach(function (p) { map[p.common_name.toLowerCase()] = p.id; });
      return map;
    }).catch(function () { return {}; });
  }
  return _plantsByNamePromise.then(function (map) {
    return map[String(name).toLowerCase()] || null;
  });
}

// ---------------------------------------------------------------------------
// Plant detail modal (markup lives in base.html, available on every page)
// ---------------------------------------------------------------------------
async function openPlantModal(plantId) {
  const modal = document.getElementById('plant-detail-modal');
  if (!modal) return;
  const loading = document.getElementById('pd-loading');
  const content = document.getElementById('pd-content');
  const errorBox = document.getElementById('pd-error');

  loading.classList.remove('hidden');
  content.classList.add('hidden');
  errorBox.classList.add('hidden');
  modal.showModal();

  try {
    const data = await api('/api/plants/' + plantId + '?enrich=1&community=1');
    renderPlantModal(data);
    loading.classList.add('hidden');
    content.classList.remove('hidden');
  } catch (err) {
    loading.classList.add('hidden');
    errorBox.textContent = err.message;
    errorBox.classList.remove('hidden');
  }
}

function factTile(icon, label, value) {
  return (
    '<div class="rounded-2xl border border-leaf-100 bg-white px-3 py-2">' +
    '<div class="flex items-center gap-1.5 text-xs text-ink-500">' + iconSvg(icon, 'h-3.5 w-3.5 text-leaf-600') + label + '</div>' +
    '<div class="mt-0.5 text-sm font-semibold text-ink-900">' + esc(value) + '</div>' +
    '</div>'
  );
}

function renderPlantModal(d) {
  const meta = categoryMeta(d.category);

  const emojiEl = document.getElementById('pd-emoji');
  emojiEl.className = 'tile h-16 w-16 text-3xl ' + meta.tile;
  emojiEl.textContent = plantEmoji(d);

  document.getElementById('pd-name').textContent = d.common_name || 'Plant';
  document.getElementById('pd-sci').textContent = d.scientific_name || '';

  const badges = [];
  badges.push(chip(meta.emoji + ' ' + esc(titleCase(d.category || 'other')), meta.tile + ' ' + meta.text));
  if (d.difficulty) {
    badges.push(chip(iconSvg('target', 'h-3.5 w-3.5') + (DIFFICULTY_LABEL[d.difficulty] || esc(d.difficulty)), DIFFICULTY_BADGE[d.difficulty] || 'bg-leaf-50 text-leaf-700'));
  }
  if (d.pollution_tolerant) badges.push(chip(iconSvg('wind', 'h-3.5 w-3.5') + 'Smog-tolerant', 'bg-leaf-50 text-leaf-700'));
  if (d.container_friendly) badges.push(chip(iconSvg('pot', 'h-3.5 w-3.5') + 'Great in pots', 'bg-sky-100 text-sky-600'));
  if (d.toxic_to_pets) badges.push(chip(iconSvg('paw', 'h-3.5 w-3.5') + 'Toxic to pets', 'bg-blush-100 text-blush-600'));
  document.getElementById('pd-badges').innerHTML = badges.join('');

  document.getElementById('pd-desc').textContent = d.description || '';

  const facts = [];
  if (d.min_temp_c != null && d.max_temp_c != null) {
    facts.push(factTile('thermometer', 'Survives', d.min_temp_c + '° to ' + d.max_temp_c + 'C'));
  }
  if (d.ideal_temp_min_c != null && d.ideal_temp_max_c != null) {
    facts.push(factTile('thermometer', 'Ideal range', d.ideal_temp_min_c + '°–' + d.ideal_temp_max_c + 'C'));
  }
  if (d.water_need) facts.push(factTile('droplet', 'Water need', WATER_LABEL[d.water_need] || titleCase(d.water_need)));
  if (d.sunlight) facts.push(factTile('sun', 'Sunlight', SUN_LABEL[d.sunlight] || titleCase(d.sunlight)));
  if (d.season) facts.push(factTile('sprout', 'Season', SEASON_LABEL[d.season] || titleCase(d.season)));
  if (d.sow_months && d.sow_months.length) {
    facts.push(factTile('calendar', 'Sow in', d.sow_months.map(function (m) { return MONTHS[m - 1].slice(0, 3); }).join(', ')));
  }
  if (d.days_to_maturity) facts.push(factTile('clock', 'Matures in', '~' + d.days_to_maturity + ' days'));
  if (d.humidity_pref) facts.push(factTile('cloud', 'Humidity', titleCase(d.humidity_pref)));
  document.getElementById('pd-facts').innerHTML = facts.join('');

  const tipsWrap = document.getElementById('pd-tips-wrap');
  if (d.care_tips) {
    tipsWrap.classList.remove('hidden');
    document.getElementById('pd-tips').textContent = d.care_tips;
  } else {
    tipsWrap.classList.add('hidden');
  }

  const communityWrap = document.getElementById('pd-community-wrap');
  const summary = d.community && d.community.summary;
  if (summary && summary.total > 0) {
    const confidence = { high: 'strong signal', medium: 'growing signal', low: 'early signal' }[summary.confidence] || '';
    communityWrap.innerHTML =
      '<h4 class="flex items-center gap-1.5 text-sm font-semibold text-ink-900">' + iconSvg('users', 'h-4 w-4 text-leaf-600') + 'Community results' + (d.community.city ? ' · ' + esc(d.community.city) : ' · all cities') + '</h4>' +
      '<div class="mt-2 flex flex-wrap gap-2">' +
      chip(iconSvg('sprout', 'h-3.5 w-3.5') + 'Thrived × ' + summary.counts.thrived, 'bg-leaf-100 text-leaf-800') +
      chip(iconSvg('alert', 'h-3.5 w-3.5') + 'Struggled × ' + summary.counts.struggled, 'bg-sun-100 text-[#8a6d1f]') +
      chip(iconSvg('xCircle', 'h-3.5 w-3.5') + 'Died × ' + summary.counts.died, 'bg-blush-100 text-blush-600') +
      (confidence ? chip(confidence, 'bg-white border border-leaf-200 text-ink-500') : '') +
      '</div>';
  } else {
    communityWrap.innerHTML =
      '<h4 class="flex items-center gap-1.5 text-sm font-semibold text-ink-900">' + iconSvg('users', 'h-4 w-4 text-leaf-600') + 'Community results</h4>' +
      '<p class="mt-1 text-sm text-ink-500">No community reports yet — grow it and be the first to tell everyone how it went.</p>';
  }

  const wikiWrap = document.getElementById('pd-wiki-wrap');
  const wiki = d.external && d.external.wikipedia;
  if (wiki && wiki.found) {
    const extract = wiki.extract || '';
    const gbif = d.external && d.external.gbif && d.external.gbif.data;
    const gbifLink = gbif && gbif.usageKey
      ? ' · <a href="https://www.gbif.org/species/' + gbif.usageKey + '" target="_blank" rel="noopener" class="text-leaf-700 underline">GBIF record ↗</a>'
      : '';
    wikiWrap.innerHTML =
      '<div class="flex gap-4">' +
      (wiki.thumbnail ? '<img src="' + esc(wiki.thumbnail) + '" alt="" class="h-20 w-20 rounded-2xl border border-leaf-100 object-cover">' : '') +
      '<div class="text-sm text-ink-700">' +
      '<p>' + esc(extract.slice(0, 320)) + (extract.length > 320 ? '…' : '') + '</p>' +
      (wiki.page_url ? '<div class="mt-2"><a href="' + esc(wiki.page_url) + '" target="_blank" rel="noopener" class="text-leaf-700 underline">Read on Wikipedia ↗</a>' + gbifLink + '</div>' : '') +
      '</div></div>';
    wikiWrap.classList.remove('hidden');
  } else {
    wikiWrap.classList.add('hidden');
    wikiWrap.innerHTML = '';
  }
}

// ---------------------------------------------------------------------------
// v2 chrome: header shadow, sleek stroke icon set
// ---------------------------------------------------------------------------
(function initChrome() {
  const header = document.querySelector('body > header');
  if (header) {
    const onScroll = function () { header.classList.toggle('scrolled', window.scrollY > 10); };
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
  }
})();

// Minimal line-icon set (feather style) for dynamic cards and banners —
// replaces the old emoji glyphs in stat tiles and season banners.
const ICONS = {
  globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18"/><path d="M12 3c2.5 2.4 4 5.6 4 9s-1.5 6.6-4 9c-2.5-2.4-4-5.6-4-9s1.5-6.6 4-9z"/>',
  thermometer: '<path d="M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4.5 4.5 0 1 0 5 0z"/>',
  droplet: '<path d="M12 2.7l5.66 5.66a8 8 0 1 1-11.31 0z"/>',
  wind: '<path d="M9.59 4.59A2 2 0 1 1 11 8H2"/><path d="M12.59 19.41A2 2 0 1 0 14 16H2"/><path d="M17.73 7.73A2.5 2.5 0 1 1 19.5 12H2"/>',
  calendar: '<rect x="3" y="4" width="18" height="17" rx="2.5"/><path d="M16 2.5v4M8 2.5v4M3 9.5h18"/>',
  target: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.2" fill="currentColor" stroke="none"/>',
  activity: '<path d="M22 12h-4l-3 8L9 4l-3 8H2"/>',
  scales: '<path d="M12 4v17"/><path d="M5 21h14"/><path d="M12 6L5 7l-2 5a3.2 3.2 0 0 0 6.4 0z"/><path d="M12 6l7 1 2 5a3.2 3.2 0 0 1-6.4 0z"/>',
  users: '<path d="M16.5 21v-1.8a4 4 0 0 0-4-4h-5a4 4 0 0 0-4 4V21"/><circle cx="10" cy="7.5" r="3.5"/><path d="M21.5 21v-1.8a4 4 0 0 0-3-3.87"/><path d="M15.5 4.1a3.5 3.5 0 0 1 0 6.8"/>',
  sun: '<circle cx="12" cy="12" r="4.2"/><path d="M12 2.8v2M12 19.2v2M2.8 12h2M19.2 12h2M5.5 5.5l1.4 1.4M17.1 17.1l1.4 1.4M18.5 5.5l-1.4 1.4M6.9 17.1l-1.4 1.4"/>',
  snow: '<path d="M12 2.5v19"/><path d="M4.2 7l15.6 9M19.8 7L4.2 16"/><path d="M9.2 4.8L12 7.5l2.8-2.7M9.2 19.2L12 16.5l2.8 2.7"/>',
  sprout: '<path d="M12 21v-7.5"/><path d="M12 13.5c0-4 3-7.2 8-7.2-.4 4.6-3.2 7.2-8 7.2z"/><path d="M12 13.5c0-3.4-2.5-6-7-6 .4 4 2.8 6 7 6z"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7.5V12l3 2"/>',
  star: '<path d="M12 2.8l2.9 5.9 6.5 1-4.7 4.6 1.1 6.5L12 17.7l-5.8 3.1 1.1-6.5-4.7-4.6 6.5-1z"/>',
  alert: '<path d="M10.3 3.9 1.9 18.3a2 2 0 0 0 1.7 3h16.8a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
  refresh: '<path d="M22 4.5v5h-5"/><path d="M2 19.5v-5h5"/><path d="M3.5 9.5a9 9 0 0 1 14.9-3.4L22 9.5"/><path d="M20.5 14.5a9 9 0 0 1-14.9 3.4L2 14.5"/>',
  check: '<path d="M21.8 11v1a10 10 0 1 1-4.6-8.4"/><path d="M22 4.5 12 14.5l-3-3"/>',
  home: '<path d="M3 9.5 12 2.5l9 7V20a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M9 22v-9h6v9"/>',
  pot: '<path d="M6.5 10.5h11l-1.1 8.2a2 2 0 0 1-2 1.8h-4.8a2 2 0 0 1-2-1.8z"/><path d="M12 10.5v-3"/><path d="M12 7.5c0-1.8 1.4-3.2 3.2-3.2-.2 1.8-1.4 3.2-3.2 3.2z"/><path d="M12 9c0-1.4-1.1-2.7-2.7-2.7.2 1.5 1.2 2.7 2.7 2.7z"/>',
  paw: '<circle cx="6.8" cy="8.2" r="1.7"/><circle cx="10.4" cy="5.4" r="1.7"/><circle cx="15" cy="5.4" r="1.7"/><circle cx="18.6" cy="8.2" r="1.7"/><path d="M12.7 11.5c-2.9 0-5.7 2-5.7 4.8 0 1.9 1.6 3.2 3.6 2.8 1.4-.3 3-.3 4.4 0 2 .4 3.6-.9 3.6-2.8 0-2.8-2.8-4.8-5.9-4.8z"/>',
  award: '<circle cx="12" cy="8.5" r="5.5"/><path d="M15.4 13.6 17 22.5l-5-3-5 3 1.6-8.9"/>',
  xCircle: '<circle cx="12" cy="12" r="9"/><path d="M15 9l-6 6M9 9l6 6"/>',
  cloud: '<path d="M18 10h-1.3A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/>',
  mapPin: '<path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 0 1 16 0z"/><circle cx="12" cy="10" r="3"/>',
  camera: '<path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m20.5 20.5-3.8-3.8"/>',
  filter: '<path d="M4 5.5h16"/><path d="M7 12h10"/><path d="M10 18.5h4"/>',
  bookOpen: '<path d="M2 3.5h6a4 4 0 0 1 4 4V21a3 3 0 0 0-3-3H2z"/><path d="M22 3.5h-6a4 4 0 0 0-4 4V21a3 3 0 0 1 3-3h7z"/>',
  compass: '<circle cx="12" cy="12" r="9"/><path d="m15.7 8.3-2.1 5.3-5.3 2.1 2.1-5.3z"/>',
  arrowRight: '<path d="M4 12h15"/><path d="m13 6 6 6-6 6"/>',
};

function iconSvg(name, cls) {
  const inner = ICONS[name];
  if (!inner) return '';
  return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" class="' + (cls || 'h-5 w-5') + '" aria-hidden="true">' + inner + '</svg>';
}

// Seasonal stroke-icon picks (rabi = cold months, kharif = hot, transition = in between)
const SEASON_ICON = { rabi: 'snow', kharif: 'sun', transition: 'sprout' };

function seasonIcon(key) {
  return SEASON_ICON[key] || 'sprout';
}
