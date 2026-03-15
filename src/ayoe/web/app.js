'use strict';

// ── State ─────────────────────────────────────────────────────────────────────
const STATE = {
  mode: 'loading',          // 'live' (ayoe serve) | 'static' (precomputed demo data)
  meta: null,
  demo: null,
  base: 'baseline',
  beam: {},                 // current slider values (absolute)
  stageMultipliers: {},
  volatility: 1,
  runs: 400,
  seed: 42,
  sim: null,
  sens: null,
  scen: null,
  sample: 'median',
  inFlight: false,
  queued: false,
};

const $ = (selector) => document.querySelector(selector);
const REGIME_COLORS = { favourable: '#3ddc97', nominal: '#38e1ff', stressed: '#ffb547', unstable: '#ff6b5b' };
const SUPERSCRIPT = { '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴', '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹', '-': '⁻' };

// ── Formatting ────────────────────────────────────────────────────────────────
function sci(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(value)) return '–';
  const tiny = value !== 0 && Math.abs(value) < 1e-3;
  if (!tiny && Math.abs(value) < 1e5) return Math.round(value).toLocaleString('en-US');
  const exponent = Math.floor(Math.log10(Math.abs(value)));
  const mantissa = value / 10 ** exponent;
  return `${mantissa.toFixed(digits)}×10${String(exponent).split('').map((c) => SUPERSCRIPT[c]).join('')}`;
}
function num(value, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(value)) return '–';
  return Number(value).toLocaleString('en-US', { maximumFractionDigits: digits, minimumFractionDigits: digits });
}
function pct(value, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(value)) return '–';
  return `${(value * 100).toFixed(digits)}%`;
}
function eff(value) {
  if (value === null || value === undefined) return '–';
  return value >= 0.001 ? pct(value, value >= 0.1 ? 0 : 1) : value.toExponential(1);
}
function energy(mev) {
  if (mev >= 1000) return `${+(mev / 1000).toPrecision(3)} GeV`;
  if (mev >= 1) return `${+mev.toPrecision(3)} MeV`;
  return `${+(mev * 1000).toPrecision(3)} keV`;
}
function escapeHtml(text) {
  return String(text).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
function paramLabel(path) {
  const control = (STATE.meta?.beam_controls || []).find((item) => `beam.${item.key}` === path);
  if (control) return control.label;
  const stageKey = path.replace('stages.', '').replace('.nominal_efficiency', '');
  const stage = (STATE.meta?.stages || []).find((item) => item.key === stageKey);
  return stage ? `${stage.label} efficiency` : path;
}

// ── Data access ───────────────────────────────────────────────────────────────
async function getJSON(url, body) {
  const response = await fetch(url, body === undefined ? {} : {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(`${url}: HTTP ${response.status}`);
  return response.json();
}

function scenarioMeta(name) {
  return STATE.meta.scenarios.find((item) => item.name === name) || STATE.meta.scenarios[0];
}

function currentOverrides() {
  const defaults = scenarioMeta(STATE.base).beam;
  const beam = {};
  for (const [key, value] of Object.entries(STATE.beam)) {
    if (Math.abs(value - defaults[key]) > 1e-12 * Math.max(1, Math.abs(defaults[key]))) beam[key] = value;
  }
  const stageMultipliers = {};
  for (const [key, value] of Object.entries(STATE.stageMultipliers)) {
    if (Math.abs(value - 1) > 1e-9) stageMultipliers[key] = value;
  }
  const overrides = {};
  if (Object.keys(beam).length) overrides.beam = beam;
  if (Object.keys(stageMultipliers).length) overrides.stage_multipliers = stageMultipliers;
  if (Math.abs(STATE.volatility - 1) > 1e-9) overrides.volatility = STATE.volatility;
  return overrides;
}

// ── Boot ──────────────────────────────────────────────────────────────────────
async function boot() {
  try {
    STATE.meta = await getJSON('api/meta');
    STATE.mode = 'live';
  } catch (error) {
    if (window.AYOE_DEMO) {
      STATE.demo = window.AYOE_DEMO;
      STATE.meta = STATE.demo.meta;
      STATE.mode = 'static';
    } else {
      setModePill('error', 'No engine and no demo data');
      $('#pipeline-caption').textContent = 'Start the engine with `ayoe serve`, or generate demo data with `ayoe export-web`.';
      return;
    }
  }
  setModePill(STATE.mode, STATE.mode === 'live' ? 'Live engine' : 'Static demo');
  Pipeline.init($('#pipeline-canvas'));
  buildControls();
  renderCalibration();
  bindEvents();

  if (STATE.mode === 'live') {
    await runSimulation();
    runScenarios();
    runSensitivity();
  } else {
    $('#static-note').hidden = false;
    for (const element of document.querySelectorAll('.controls input, #runs-select, #run-btn, #reset-btn, #sens-btn, #scen-btn')) {
      element.disabled = true;
    }
    $('#auto-run').closest('label').hidden = true;
    const generated = STATE.demo.generated_with;
    $('#run-status').textContent = `Precomputed: ${generated.runs} runs per scenario, seed ${generated.seed}.`;
    loadStaticSimulation();
    STATE.sens = STATE.demo.sensitivity.baseline;
    STATE.scen = STATE.demo.scenarios;
    renderSensitivity();
    renderScenarios();
  }
}

function setModePill(mode, text) {
  const pill = $('#mode-pill');
  pill.className = `pill pill-${mode}`;
  pill.textContent = text;
}

// ── Controls ──────────────────────────────────────────────────────────────────
function buildControls() {
  const select = $('#scenario-select');
  select.innerHTML = STATE.meta.scenarios.map((s) => `<option value="${s.name}">${s.name}</option>`).join('');
  select.value = STATE.base;

  $('#beam-controls').innerHTML = STATE.meta.beam_controls.map((control) => `
    <div class="slider-row" data-beam="${control.key}">
      <label for="beam-${control.key}">${escapeHtml(control.label)}</label>
      <output id="beam-${control.key}-out"></output>
      <input id="beam-${control.key}" type="range" min="${control.min}" max="${control.max}" step="${control.step}">
    </div>`).join('');

  const [low, high] = STATE.meta.stage_multiplier_range;
  $('#stage-controls').innerHTML = STATE.meta.stages.map((stage) => `
    <div class="slider-row" data-stage="${stage.key}">
      <label for="stage-${stage.key}">${escapeHtml(stage.label)}</label>
      <output id="stage-${stage.key}-out">×1.00</output>
      <input id="stage-${stage.key}" type="range" min="${low}" max="${high}" step="0.05" value="1">
    </div>`).join('');

  applyScenarioDefaults();
}

function formatBeamValue(control, value) {
  if (control.key === 'proton_count') return sci(value);
  const digits = control.step < 0.01 ? 3 : control.step < 0.1 ? 2 : 1;
  return `${Number(value).toFixed(digits)}${control.unit && control.unit !== 'x' ? ` ${control.unit}` : control.unit === 'x' ? '×' : ''}`;
}

function applyScenarioDefaults() {
  const scenario = scenarioMeta(STATE.base);
  $('#scenario-desc').textContent = scenario.description;
  STATE.beam = {};
  for (const control of STATE.meta.beam_controls) {
    const value = scenario.beam[control.key];
    STATE.beam[control.key] = value;
    $(`#beam-${control.key}`).value = value;
  }
  STATE.stageMultipliers = {};
  for (const stage of STATE.meta.stages) {
    STATE.stageMultipliers[stage.key] = 1;
    $(`#stage-${stage.key}`).value = 1;
  }
  STATE.volatility = 1;
  $('#volatility').value = 1;
  refreshControlLabels();
}

function refreshControlLabels() {
  const defaults = scenarioMeta(STATE.base).beam;
  for (const control of STATE.meta.beam_controls) {
    const value = STATE.beam[control.key];
    $(`#beam-${control.key}-out`).textContent = formatBeamValue(control, value);
    const changed = Math.abs(value - defaults[control.key]) > control.step / 2;
    $(`[data-beam="${control.key}"]`).classList.toggle('changed', changed);
  }
  for (const stage of STATE.meta.stages) {
    const value = STATE.stageMultipliers[stage.key];
    $(`#stage-${stage.key}-out`).textContent = `×${value.toFixed(2)}`;
    $(`[data-stage="${stage.key}"]`).classList.toggle('changed', Math.abs(value - 1) > 1e-9);
  }
  $('#volatility-out').textContent = `×${STATE.volatility.toFixed(2)}`;
  $('#volatility').closest('.slider-row').classList.toggle('changed', Math.abs(STATE.volatility - 1) > 1e-9);
}

let autoRunTimer = null;
function scheduleAutoRun() {
  if (STATE.mode !== 'live' || !$('#auto-run').checked) return;
  clearTimeout(autoRunTimer);
  autoRunTimer = setTimeout(runSimulation, 280);
}

function bindEvents() {
  $('#scenario-select').addEventListener('change', (event) => selectScenario(event.target.value));
  $('#beam-controls').addEventListener('input', (event) => {
    const key = event.target.closest('[data-beam]')?.dataset.beam;
    if (!key) return;
    STATE.beam[key] = Number(event.target.value);
    refreshControlLabels();
    scheduleAutoRun();
  });
  $('#stage-controls').addEventListener('input', (event) => {
    const key = event.target.closest('[data-stage]')?.dataset.stage;
    if (!key) return;
    STATE.stageMultipliers[key] = Number(event.target.value);
    refreshControlLabels();
    scheduleAutoRun();
  });
  $('#volatility').addEventListener('input', (event) => {
    STATE.volatility = Number(event.target.value);
    refreshControlLabels();
    scheduleAutoRun();
  });
  $('#runs-select').addEventListener('change', (event) => { STATE.runs = Number(event.target.value); scheduleAutoRun(); });
  $('#seed-input').addEventListener('change', (event) => { STATE.seed = event.target.value === '' ? null : Number(event.target.value); scheduleAutoRun(); });
  $('#seed-random').addEventListener('click', () => {
    STATE.seed = Math.floor(Math.random() * 1e6);
    $('#seed-input').value = STATE.seed;
    runSimulation();
  });
  $('#run-btn').addEventListener('click', runSimulation);
  $('#reset-btn').addEventListener('click', () => { applyScenarioDefaults(); runSimulation(); });
  $('#sens-btn').addEventListener('click', runSensitivity);
  $('#scen-btn').addEventListener('click', runScenarios);
  $('#replay-btn').addEventListener('click', () => Pipeline.restart());
  for (const button of document.querySelectorAll('[data-sample]')) {
    button.addEventListener('click', () => {
      STATE.sample = button.dataset.sample;
      for (const other of document.querySelectorAll('[data-sample]')) other.classList.toggle('active', other === button);
      if (STATE.sim) renderPipeline();
    });
  }
  bindTooltips();
}

function selectScenario(name) {
  STATE.base = name;
  $('#scenario-select').value = name;
  applyScenarioDefaults();
  if (STATE.mode === 'live') {
    runSimulation();
  } else {
    loadStaticSimulation();
  }
  renderScenarioTable();
}

// ── Engine calls ──────────────────────────────────────────────────────────────
async function runSimulation() {
  if (STATE.mode !== 'live') return;
  if (STATE.inFlight) { STATE.queued = true; return; }
  STATE.inFlight = true;
  $('#run-btn').disabled = true;
  $('#run-status').textContent = 'Simulating…';
  document.querySelector('.charts').classList.add('busy');
  try {
    STATE.sim = await getJSON('api/simulate', {
      base: STATE.base, overrides: currentOverrides(), runs: STATE.runs, seed: STATE.seed,
    });
    $('#run-status').textContent = `${STATE.sim.runs.toLocaleString('en-US')} cycles in ${num(STATE.sim.elapsed_ms, 0)} ms · seed ${STATE.sim.seed ?? 'random'}`;
    renderSimulation();
  } catch (error) {
    $('#run-status').textContent = `Simulation failed: ${error.message}`;
  } finally {
    STATE.inFlight = false;
    $('#run-btn').disabled = false;
    document.querySelector('.charts').classList.remove('busy');
    if (STATE.queued) { STATE.queued = false; runSimulation(); }
  }
}

async function runSensitivity() {
  if (STATE.mode !== 'live') return;
  const button = $('#sens-btn');
  button.disabled = true;
  $('#sens-status').textContent = 'Running 35 perturbed Monte Carlo batches…';
  try {
    STATE.sens = await getJSON('api/sensitivity', {
      base: STATE.base, overrides: currentOverrides(), runs: 150, seed: STATE.seed,
    });
    renderSensitivity();
  } catch (error) {
    $('#sens-status').textContent = `Sensitivity failed: ${error.message}`;
  } finally {
    button.disabled = false;
  }
}

async function runScenarios() {
  if (STATE.mode !== 'live') return;
  const button = $('#scen-btn');
  button.disabled = true;
  try {
    STATE.scen = await getJSON('api/scenarios', { runs: 300, seed: STATE.seed });
    renderScenarios();
  } catch (error) {
    $('#chart-scen').innerHTML = `<div class="empty">Scenario comparison failed: ${escapeHtml(error.message)}</div>`;
  } finally {
    button.disabled = false;
  }
}

function loadStaticSimulation() {
  STATE.sim = STATE.demo.simulations[STATE.base];
  renderSimulation();
}

// ── Rendering: simulation ─────────────────────────────────────────────────────
function renderSimulation() {
  renderKpis();
  renderStageStrip();
  renderPipeline();
  renderFunnel();
  renderHistogram();
  renderLossShare();
  renderRegimes();
  renderCorrelations();
}

function renderKpis() {
  const { stats, economics, bottlenecks, near_zero_threshold: threshold } = STATE.sim;
  $('#kpi-median').textContent = num(stats.median, 0);
  $('#kpi-median-sub').textContent = `${STATE.sim.runs.toLocaleString('en-US')} simulated cycles · ${STATE.sim.name}`;
  $('#kpi-interval').textContent = `${num(stats.q05, 0)} – ${num(stats.q95, 0)}`;
  $('#kpi-mean').textContent = num(stats.mean, 1);
  $('#kpi-cv').textContent = `coefficient of variation ${num(stats.coefficient_of_variation, 2)}`;
  $('#kpi-risk').textContent = pct(stats.probability_near_zero, 0);
  $('#kpi-risk-sub').textContent = `P(≤ ${threshold} atoms) · P(0) = ${pct(stats.probability_zero, 0)}`;
  $('#kpi-rate').textContent = num(economics.mean_yield_per_hour, 0);
  $('#kpi-rate-sub').textContent = `one cycle ≈ ${num(economics.mean_duration_s / 60, 1)} min · ${num(economics.mean_cost_units, 0)} cost units`;
  const top = bottlenecks[0];
  $('#kpi-bottleneck').textContent = top.stage_label;
  $('#kpi-bottleneck-sub').textContent = `${pct(top.log_loss_share, 0)} of log-loss · keeps ${eff(top.mean_effective_efficiency)}`;
}

function renderStageStrip() {
  const { sim } = STATE;
  const bottleneck = sim.bottlenecks[0]?.stage_name;
  const cells = [
    `<div class="stage-cell">${explainButton('stage:protons')}<div class="s-name">Protons on target</div><div class="s-count">${sci(sim.initial.q50)}</div><div class="s-meta"><span>26 GeV</span><span>input</span></div></div>`,
    ...sim.stages.map((stage) => `
      <div class="stage-cell${stage.key === bottleneck ? ' is-bottleneck' : ''}" data-tip="${escapeHtml(`${stage.label}\nmedian out: ${sci(stage.output.q50)}\n90% of runs: ${sci(stage.output.q05)} – ${sci(stage.output.q95)}\nmean efficiency: ${eff(stage.mean_effective_efficiency)}\nenergy after stage: ${energy(stage.energy_mev)}`)}">
        ${explainButton(`stage:${stage.key}`)}
        <div class="s-name">${escapeHtml(stage.label)}</div>
        <div class="s-count">${sci(stage.output.q50)}</div>
        <div class="s-meta"><span>${energy(stage.energy_mev)}</span><span>${eff(stage.mean_effective_efficiency)}</span></div>
      </div>`),
  ];
  $('#stage-strip').innerHTML = cells.join('');
}

function renderPipeline() {
  const sample = STATE.sim.samples[STATE.sample];
  const energies = [26000, ...STATE.sim.stages.map((stage) => stage.energy_mev)];
  Pipeline.load(sample.counts, energies);
  const regime = sample.regime ? `${sample.regime} machine state` : '';
  $('#pipeline-caption').innerHTML =
    `${escapeHtml(STATE.sim.name)} · ${STATE.sample} run #${sample.run_id} (${escapeHtml(regime)}) → ` +
    `<strong>${sample.final_yield.toLocaleString('en-US')}</strong> usable anti-atoms from ${sci(sample.counts[0])} protons`;
}

// ── Pipeline animation ────────────────────────────────────────────────────────
const Pipeline = {
  canvas: null, ctx: null, width: 0, height: 0, dpr: 1,
  counts: null, survival: [], speeds: [], particles: [], flashes: [], trapped: [],
  frame: 0, raf: null, visible: true,
  reducedMotion: window.matchMedia('(prefers-reduced-motion: reduce)').matches,

  init(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    new ResizeObserver(() => this.resize()).observe(canvas);
    new IntersectionObserver((entries) => {
      this.visible = entries[0].isIntersecting;
      if (this.visible) this.loop();
    }).observe(canvas);
    this.resize();
  },

  resize() {
    const rect = this.canvas.getBoundingClientRect();
    this.dpr = window.devicePixelRatio || 1;
    this.width = rect.width;
    this.height = rect.height;
    this.canvas.width = Math.round(rect.width * this.dpr);
    this.canvas.height = Math.round(rect.height * this.dpr);
    this.ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    if (this.reducedMotion && this.counts) this.prerender();
  },

  load(counts, energies) {
    this.counts = counts;
    // Visual density follows log10(count): each gate keeps the ratio of orders of magnitude.
    const magnitudes = counts.map((count) => Math.log10(count + 1));
    this.survival = magnitudes.map((value, index) => (index === 0 ? 1 : magnitudes[index - 1] > 0 ? Math.min(1, value / magnitudes[index - 1]) : 0));
    const top = Math.log10(energies[0]) + 4.2;
    this.speeds = energies.map((mev) => 0.45 + 2.8 * Math.max(0, (Math.log10(mev) + 4.2) / top));
    this.restart();
  },

  restart() {
    this.particles = [];
    this.flashes = [];
    this.trapped = [];
    this.frame = 0;
    if (this.reducedMotion) this.prerender(); else this.loop();
  },

  gateX(index) {
    const left = 24;
    const right = this.width - Math.min(150, this.width * 0.16);
    return left + (index * (right - left)) / 8;
  },

  trapBox() {
    const x = this.gateX(8) + 14;
    return { x, y: this.height * 0.22, w: this.width - x - 10, h: this.height * 0.56 };
  },

  colorFor(zone) {
    if (zone <= 1) return '#ffb547';        // protons
    if (zone <= 6) return '#38e1ff';        // antiprotons
    return '#ff4fd8';                       // antihydrogen
  },

  step() {
    const { height } = this;
    const bandTop = height * 0.2;
    const bandHeight = height * 0.6;
    if (this.counts) {
      for (let k = 0; k < 2; k += 1) {
        this.particles.push({ x: this.gateX(0), y: bandTop + Math.random() * bandHeight, zone: 0, wobble: Math.random() * Math.PI * 2 });
      }
    }
    const survivors = [];
    for (const particle of this.particles) {
      particle.x += this.speeds[particle.zone] * (0.8 + Math.random() * 0.4);
      particle.wobble += 0.08;
      particle.y += Math.sin(particle.wobble) * 0.25;
      const nextGate = particle.zone + 1;
      if (nextGate <= 8 && particle.x >= this.gateX(nextGate)) {
        if (Math.random() > this.survival[nextGate]) {
          this.flashes.push({ x: particle.x, y: particle.y, age: 0, color: this.colorFor(particle.zone) });
          continue;
        }
        particle.zone = nextGate;
      }
      if (particle.zone === 8 && particle.x >= this.gateX(8) + 14) {
        const finalYield = this.counts[8];
        if (this.trapped.length < Math.min(finalYield, 70)) {
          const box = this.trapBox();
          this.trapped.push({
            cx: box.x + box.w / 2, cy: box.y + box.h / 2,
            r: 6 + Math.random() * Math.min(box.w, box.h) * 0.38, a: Math.random() * Math.PI * 2, v: 0.01 + Math.random() * 0.03,
          });
        }
        continue;
      }
      survivors.push(particle);
    }
    this.particles = survivors;
    this.flashes = this.flashes.filter((flash) => (flash.age += 1) < 22);
    for (const atom of this.trapped) atom.a += atom.v;
    this.frame += 1;
  },

  draw() {
    const { ctx, width, height } = this;
    ctx.clearRect(0, 0, width, height);
    const bandTop = height * 0.2;
    const bandHeight = height * 0.6;

    const gradient = ctx.createLinearGradient(0, 0, width, 0);
    gradient.addColorStop(0, 'rgba(255,181,71,0.07)');
    gradient.addColorStop(0.3, 'rgba(56,225,255,0.07)');
    gradient.addColorStop(0.85, 'rgba(255,79,216,0.07)');
    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.roundRect(this.gateX(0) - 8, bandTop - 6, this.gateX(8) - this.gateX(0) + 16, bandHeight + 12, 12);
    ctx.fill();

    ctx.font = '10px Inter, system-ui, sans-serif';
    ctx.textAlign = 'center';
    for (let index = 1; index <= 8; index += 1) {
      const x = this.gateX(index);
      ctx.strokeStyle = 'rgba(139,154,179,0.35)';
      ctx.setLineDash([3, 4]);
      ctx.beginPath();
      ctx.moveTo(x, bandTop - 10);
      ctx.lineTo(x, bandTop + bandHeight + 10);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = 'rgba(139,154,179,0.9)';
      ctx.fillText(String(index), x, bandTop - 14);
      if (this.counts && width >= 600) {
        ctx.fillStyle = 'rgba(230,237,247,0.85)';
        ctx.fillText(sci(this.counts[index], 1), x, bandTop + bandHeight + 22);
      }
    }

    for (const flash of this.flashes) {
      const progress = flash.age / 22;
      ctx.strokeStyle = flash.color;
      ctx.globalAlpha = 1 - progress;
      ctx.beginPath();
      ctx.arc(flash.x, flash.y, 1.5 + progress * 7, 0, Math.PI * 2);
      ctx.stroke();
    }
    ctx.globalAlpha = 1;

    for (const particle of this.particles) {
      ctx.fillStyle = this.colorFor(particle.zone);
      ctx.shadowColor = ctx.fillStyle;
      ctx.shadowBlur = 6;
      ctx.beginPath();
      ctx.arc(particle.x, particle.y, 1.9, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.shadowBlur = 0;

    const box = this.trapBox();
    ctx.strokeStyle = 'rgba(255,79,216,0.55)';
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.roundRect(box.x, box.y, box.w, box.h, 10);
    ctx.stroke();
    ctx.lineWidth = 1;
    for (const atom of this.trapped) {
      const x = atom.cx + Math.cos(atom.a) * atom.r * (box.w / Math.max(box.w, box.h));
      const y = atom.cy + Math.sin(atom.a) * atom.r * (box.h / Math.max(box.w, box.h));
      ctx.fillStyle = '#fff3fd';
      ctx.shadowColor = '#ff4fd8';
      ctx.shadowBlur = 10;
      ctx.beginPath();
      ctx.arc(x, y, 2.4, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.shadowBlur = 0;
    ctx.fillStyle = '#e6edf7';
    ctx.font = '600 13px Inter, system-ui, sans-serif';
    ctx.fillText(this.counts ? this.counts[8].toLocaleString('en-US') : '–', box.x + box.w / 2, box.y - 18);
    ctx.font = '10px Inter, system-ui, sans-serif';
    ctx.fillStyle = 'rgba(139,154,179,0.95)';
    ctx.fillText(width >= 600 ? 'trapped anti-atoms' : 'trapped', box.x + box.w / 2, box.y - 6);
  },

  loop() {
    if (this.raf || this.reducedMotion) return;
    const tick = () => {
      this.raf = null;
      if (!this.visible || !this.counts) return;
      this.step();
      this.draw();
      this.raf = requestAnimationFrame(tick);
    };
    this.raf = requestAnimationFrame(tick);
  },

  prerender() {
    if (!this.counts) return;
    for (let index = 0; index < 900; index += 1) this.step();
    this.flashes = [];
    this.draw();
  },
};

// ── SVG helpers ───────────────────────────────────────────────────────────────
function niceMax(value) {
  if (value <= 0) return 1;
  const exponent = 10 ** Math.floor(Math.log10(value));
  for (const step of [1, 2, 2.5, 5, 10]) if (value <= step * exponent) return step * exponent;
  return 10 * exponent;
}

function linearTicks(max, count = 5) {
  const step = niceMax(max / count);
  const ticks = [];
  for (let value = 0; value <= max + 1e-9; value += step) ticks.push(value);
  return ticks;
}

function renderFunnel() {
  const { sim } = STATE;
  const W = 1000, H = 330, m = { l: 62, r: 24, t: 22, b: 64 };
  const n = 9;
  const inset = 34;
  const xs = Array.from({ length: n }, (_, i) => m.l + inset + (i * (W - m.l - m.r - 2 * inset)) / (n - 1));
  const maxDecade = Math.ceil(Math.log10(Math.max(sim.initial.q95, 10)));
  const y = (count) => H - m.b - (Math.log10(Math.max(count, 1)) / maxDecade) * (H - m.t - m.b);
  const q = (key) => [sim.initial[key], ...sim.stages.map((stage) => stage.output[key])];
  const median = q('q50'), low = q('q05'), high = q('q95');
  const labels = ['Protons on target', ...sim.stages.map((stage) => stage.label)];
  const energies = [26000, ...sim.stages.map((stage) => stage.energy_mev)];

  let out = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Survival funnel on a log scale">`;
  for (let decade = 0; decade <= maxDecade; decade += 2) {
    const yy = y(10 ** decade);
    out += `<g class="grid"><line x1="${m.l}" x2="${W - m.r}" y1="${yy}" y2="${yy}"/></g>`;
    out += `<text x="${m.l - 10}" y="${yy + 4}" text-anchor="end">10${String(decade).split('').map((c) => SUPERSCRIPT[c]).join('')}</text>`;
  }
  for (const trace of sim.traces) {
    out += `<polyline points="${trace.map((count, i) => `${xs[i]},${y(count)}`).join(' ')}" fill="none" stroke="#38e1ff" stroke-opacity="0.08" stroke-width="1"/>`;
  }
  const band = [...high.map((count, i) => `${xs[i]},${y(count)}`), ...low.map((count, i) => `${xs[i]},${y(count)}`).reverse()].join(' ');
  out += `<polygon points="${band}" fill="#38e1ff" fill-opacity="0.13" stroke="none"/>`;
  out += `<polyline points="${median.map((count, i) => `${xs[i]},${y(count)}`).join(' ')}" fill="none" stroke="url(#funnel-gradient)" stroke-width="3"/>`;
  out += `<defs><linearGradient id="funnel-gradient" x1="0" x2="1"><stop offset="0" stop-color="#ffb547"/><stop offset="0.25" stop-color="#38e1ff"/><stop offset="1" stop-color="#ff4fd8"/></linearGradient></defs>`;
  median.forEach((count, i) => {
    const stage = sim.stages[i - 1];
    const tip = i === 0
      ? `Protons on target\nmedian ${sci(count)}`
      : `${stage.label}\nmedian ${sci(count)}\n90% of runs: ${sci(low[i])} – ${sci(high[i])}\nmean efficiency ${eff(stage.mean_effective_efficiency)}`;
    out += `<circle cx="${xs[i]}" cy="${y(count)}" r="5" fill="#0f1828" stroke="#e6edf7" stroke-width="2" data-tip="${escapeHtml(tip)}"/>`;
    out += `<text class="value-label" x="${xs[i]}" y="${y(count) - 12}" text-anchor="middle">${sci(count, 1)}</text>`;
    out += `<text class="strong-label" x="${xs[i]}" y="${H - m.b + 22}" text-anchor="middle">${escapeHtml(shortLabel(labels[i]))}</text>`;
    out += `<text x="${xs[i]}" y="${H - m.b + 38}" text-anchor="middle">${energy(energies[i])}</text>`;
  });
  out += '</svg>';
  $('#chart-funnel').innerHTML = out;
}

function shortLabel(label) {
  return label.replace('Antihydrogen Formation', 'H̄ formation').replace('Final Usable Yield', 'Usable H̄')
    .replace('Antiproton Creation', 'p̄ creation').replace('Protons on target', 'Protons').replace('Proton Beam Input', 'Beam delivery')
    .replace('Particle Selection', 'Selection');
}

function renderHistogram() {
  const { sim } = STATE;
  const yields = sim.final_yields;
  const sorted = [...yields].sort((a, b) => a - b);
  const cap = sorted[Math.floor(sorted.length * 0.99)] || 1;
  const binCount = Math.min(32, Math.max(8, cap + 1));
  const binWidth = Math.max(1, Math.ceil((cap + 1) / binCount));
  const bins = new Array(Math.ceil((cap + 1) / binWidth)).fill(0);
  for (const value of yields) bins[Math.min(bins.length - 1, Math.floor(value / binWidth))] += 1;
  const W = 520, H = 270, m = { l: 44, r: 16, t: 26, b: 40 };
  const xMax = bins.length * binWidth;
  const x = (value) => m.l + (value / xMax) * (W - m.l - m.r);
  const yMax = niceMax(Math.max(...bins));
  const y = (count) => H - m.b - (count / yMax) * (H - m.t - m.b);

  let out = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Histogram of final yields">`;
  for (const tick of linearTicks(yMax, 4)) {
    out += `<g class="grid"><line x1="${m.l}" x2="${W - m.r}" y1="${y(tick)}" y2="${y(tick)}"/></g><text x="${m.l - 8}" y="${y(tick) + 4}" text-anchor="end">${tick}</text>`;
  }
  const threshold = sim.near_zero_threshold;
  out += `<rect x="${x(0)}" y="${m.t}" width="${Math.max(0, x(threshold + 1) - x(0))}" height="${H - m.t - m.b}" fill="#ff6b5b" fill-opacity="0.08"/>`;
  out += `<text x="${x(0) + 4}" y="${m.t + 12}" fill="#ff6b5b" style="fill:#ff6b5b">≤ ${threshold}: near zero</text>`;
  bins.forEach((count, i) => {
    const from = i * binWidth, to = from + binWidth - 1;
    const last = i === bins.length - 1;
    const range = binWidth === 1 ? `${from}` : `${from}–${last ? `${to}+` : to}`;
    out += `<rect x="${x(from) + 1}" y="${y(count)}" width="${Math.max(1, x(from + binWidth) - x(from) - 2)}" height="${H - m.b - y(count)}" rx="2" fill="#8b7bff" data-tip="${escapeHtml(`${range} anti-atoms\n${count} runs (${pct(count / yields.length)})`)}"/>`;
  });
  const markers = [['median', sim.stats.median, '#3ddc97'], ['mean', sim.stats.mean, '#ffb547']];
  markers.forEach(([name, value, color], index) => {
    const xx = x(Math.min(value + binWidth / 2, xMax));
    out += `<line x1="${xx}" x2="${xx}" y1="${m.t}" y2="${H - m.b}" stroke="${color}" stroke-width="2" stroke-dasharray="${index ? '5 4' : ''}"/>`;
    out += `<text x="${xx + 5}" y="${m.t + 26 + index * 14}" style="fill:${color}">${name} ${num(value, index ? 1 : 0)}</text>`;
  });
  for (const tick of linearTicks(xMax, 5)) {
    out += `<text x="${x(tick)}" y="${H - m.b + 16}" text-anchor="middle">${tick}</text>`;
  }
  out += `<text x="${(W + m.l) / 2}" y="${H - 4}" text-anchor="middle">usable anti-atoms per cycle</text></svg>`;
  $('#chart-hist').innerHTML = out;
}

function horizontalBars(rows, { valueKey, labelKey, format, color, domain, W = 520 }) {
  const rowH = 30, m = { l: 150, r: 56, t: 8, b: 8 };
  const H = m.t + m.b + rows.length * rowH;
  const [low, high] = domain;
  const x = (value) => m.l + ((value - low) / (high - low)) * (W - m.l - m.r);
  let out = `<svg viewBox="0 0 ${W} ${H}">`;
  if (low < 0) out += `<line x1="${x(0)}" x2="${x(0)}" y1="${m.t}" y2="${H - m.b}" stroke="#1f2d45"/>`;
  rows.forEach((row, i) => {
    const value = row[valueKey];
    const yy = m.t + i * rowH;
    const x0 = x(Math.min(0, value)), x1 = x(Math.max(0, value));
    const fill = typeof color === 'function' ? color(row, i) : color;
    out += `<text class="strong-label" x="${m.l - 10}" y="${yy + rowH / 2 + 4}" text-anchor="end">${escapeHtml(row[labelKey])}</text>`;
    out += `<rect x="${x0}" y="${yy + 6}" width="${Math.max(1, x1 - x0)}" height="${rowH - 12}" rx="4" fill="${fill}" data-tip="${escapeHtml(`${row[labelKey]}\n${format(value)}`)}"/>`;
    out += `<text class="value-label" x="${value >= 0 ? x1 + 6 : x0 - 6}" y="${yy + rowH / 2 + 4}" text-anchor="${value >= 0 ? 'start' : 'end'}">${format(value)}</text>`;
  });
  return `${out}</svg>`;
}

function renderLossShare() {
  const rows = STATE.sim.bottlenecks;
  const max = Math.max(...rows.map((row) => row.log_loss_share));
  $('#chart-loss').innerHTML = horizontalBars(rows, {
    valueKey: 'log_loss_share', labelKey: 'stage_label', format: (value) => pct(value, 0),
    color: (row, i) => (i === 0 ? '#ff4fd8' : '#8b7bff'), domain: [0, max * 1.05],
  });
}

function renderCorrelations() {
  const rows = STATE.sim.correlations;
  $('#chart-corr').innerHTML = horizontalBars(rows, {
    valueKey: 'spearman_correlation', labelKey: 'stage_label', format: (value) => num(value, 2),
    color: (row) => (row.spearman_correlation >= 0 ? '#3ddc97' : '#ff6b5b'),
    domain: [Math.min(0, ...rows.map((row) => row.spearman_correlation)) - 0.05, 1],
  });
}

function renderRegimes() {
  const rows = STATE.sim.regimes;
  const W = 520, H = 250, m = { l: 40, r: 12, t: 22, b: 44 };
  const yMax = niceMax(Math.max(...rows.map((row) => row.mean_yield)) * 1.1);
  const y = (value) => H - m.b - (value / yMax) * (H - m.t - m.b);
  const slot = (W - m.l - m.r) / rows.length;
  let out = `<svg viewBox="0 0 ${W} ${H}">`;
  for (const tick of linearTicks(yMax, 4)) {
    out += `<g class="grid"><line x1="${m.l}" x2="${W - m.r}" y1="${y(tick)}" y2="${y(tick)}"/></g><text x="${m.l - 8}" y="${y(tick) + 4}" text-anchor="end">${tick}</text>`;
  }
  rows.forEach((row, i) => {
    const cx = m.l + slot * (i + 0.5);
    const width = slot * 0.56;
    const color = REGIME_COLORS[row.name] || '#8b7bff';
    out += `<rect x="${cx - width / 2}" y="${y(row.mean_yield)}" width="${width}" height="${H - m.b - y(row.mean_yield)}" rx="6" fill="${color}" fill-opacity="0.85" data-tip="${escapeHtml(`${row.name}\n${pct(row.share, 0)} of runs\nmean ${num(row.mean_yield, 1)} · median ${num(row.median_yield, 0)}`)}"/>`;
    out += `<text class="value-label" x="${cx}" y="${y(row.mean_yield) - 6}" text-anchor="middle">${num(row.mean_yield, 1)}</text>`;
    out += `<text class="strong-label" x="${cx}" y="${H - m.b + 18}" text-anchor="middle">${row.name}</text>`;
    out += `<text x="${cx}" y="${H - m.b + 33}" text-anchor="middle">${pct(row.share, 0)} of runs</text>`;
  });
  $('#chart-regimes').innerHTML = `${out}</svg>`;
}

// ── Rendering: sensitivity & scenarios ────────────────────────────────────────
function renderSensitivity() {
  const sens = STATE.sens;
  if (!sens) return;
  const rows = sens.rows.slice(0, 14);
  const extent = Math.max(0.05, ...rows.flatMap((row) => [Math.abs(row.down || 0), Math.abs(row.up || 0)]));
  const W = 1000, rowH = 28, m = { l: 230, r: 70, t: 26, b: 30 };
  const H = m.t + m.b + rows.length * rowH;
  const x = (value) => m.l + ((value + extent) / (2 * extent)) * (W - m.l - m.r);
  let out = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Sensitivity tornado chart">`;
  for (const tick of [-1, -0.5, 0, 0.5, 1].map((t) => t * extent)) {
    out += `<g class="grid"><line x1="${x(tick)}" x2="${x(tick)}" y1="${m.t - 6}" y2="${H - m.b}"/></g><text x="${x(tick)}" y="${m.t - 10}" text-anchor="middle">${tick > 0 ? '+' : ''}${pct(tick, 0)}</text>`;
  }
  rows.forEach((row, i) => {
    const yy = m.t + i * rowH;
    const label = paramLabel(row.parameter);
    const groupColor = row.group === 'physics' ? '#38e1ff' : row.group === 'beam' ? '#ffb547' : '#8b9ab3';
    out += `<circle cx="${m.l - 218}" cy="${yy + rowH / 2}" r="3.5" fill="${groupColor}"/>`;
    out += `<text class="strong-label" x="${m.l - 208}" y="${yy + rowH / 2 + 4}">${escapeHtml(label)}</text>`;
    for (const direction of ['down', 'up']) {
      const value = row[direction];
      if (value === null || value === undefined) continue;
      const x0 = x(Math.min(0, value)), x1 = x(Math.max(0, value));
      const fill = direction === 'up' ? '#3ddc97' : '#ff6b5b';
      const tip = `${label} ${direction === 'up' ? '+' : '−'}${pct(sens.delta, 0)}\nmean yield ${value >= 0 ? '+' : ''}${pct(value)}\nelasticity ${num(row[`elasticity_${direction}`], 2)}`;
      out += `<rect x="${x0}" y="${yy + 5}" width="${Math.max(1, x1 - x0)}" height="${rowH - 10}" rx="3" fill="${fill}" fill-opacity="${direction === 'up' ? 0.9 : 0.8}" data-tip="${escapeHtml(tip)}"/>`;
    }
    const dominant = Math.abs(row.up || 0) >= Math.abs(row.down || 0) ? 'up' : 'down';
    out += `<text class="value-label" x="${W - m.r + 8}" y="${yy + rowH / 2 + 4}">ε ${num(row[`elasticity_${dominant}`], 2)}</text>`;
  });
  out += `<text x="${m.l - 218}" y="${H - 8}"><tspan style="fill:#38e1ff">●</tspan> physics  <tspan style="fill:#ffb547">●</tspan> beam  <tspan style="fill:#8b9ab3">●</tspan> stage efficiency</text>`;
  out += `<text x="${x(-extent)}" y="${H - 8}" style="fill:#ff6b5b">■ input −${pct(sens.delta, 0)}</text>`;
  out += `<text x="${x(0) + 10}" y="${H - 8}" style="fill:#3ddc97">■ input +${pct(sens.delta, 0)}</text>`;
  out += '</svg>';
  $('#chart-sens').innerHTML = out;
  const where = STATE.mode === 'static' ? ' (precomputed for the baseline scenario)' : '';
  $('#sens-status').textContent = `${sens.name}${where}: ${sens.runs} runs per perturbation · base mean ${num(sens.base_mean, 1)} anti-atoms · ε = elasticity (% yield change per % input change)`;
}

function renderScenarios() {
  const scen = STATE.scen;
  if (!scen) return;
  const rows = [...scen.rows].sort((a, b) => b.q50 - a.q50);
  const W = 1000, rowH = 34, m = { l: 130, r: 30, t: 14, b: 34 };
  const H = m.t + m.b + rows.length * rowH;
  const maxValue = Math.max(...rows.map((row) => row.q95));
  const logMax = Math.log10(maxValue + 1);
  const x = (value) => m.l + (Math.log10(value + 1) / logMax) * (W - m.l - m.r);
  let out = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Scenario yield distributions">`;
  for (const tick of [0, 1, 3, 10, 30, 100, 300, 1000, 3000].filter((t) => t <= maxValue * 1.05)) {
    out += `<g class="grid"><line x1="${x(tick)}" x2="${x(tick)}" y1="${m.t}" y2="${H - m.b}"/></g><text x="${x(tick)}" y="${H - m.b + 16}" text-anchor="middle">${tick}</text>`;
  }
  out += `<text x="${(W + m.l) / 2}" y="${H - 2}" text-anchor="middle">usable anti-atoms per cycle (log scale)</text>`;
  rows.forEach((row, i) => {
    const yy = m.t + i * rowH + rowH / 2;
    const active = row.name === STATE.base;
    const color = active ? '#ff4fd8' : '#38e1ff';
    const tip = `${row.name}\nmedian ${num(row.q50, 0)} · mean ${num(row.mean, 1)}\n50%: ${num(row.q25, 0)}–${num(row.q75, 0)} · 90%: ${num(row.q05, 0)}–${num(row.q95, 0)}`;
    out += `<g data-tip="${escapeHtml(tip)}">`;
    out += `<text class="strong-label" x="${m.l - 12}" y="${yy + 4}" text-anchor="end" style="${active ? 'fill:#ff4fd8;font-weight:600' : ''}">${row.name}</text>`;
    out += `<line x1="${x(row.q05)}" x2="${x(row.q95)}" y1="${yy}" y2="${yy}" stroke="${color}" stroke-opacity="0.6"/>`;
    out += `<rect x="${x(row.q25)}" y="${yy - 9}" width="${Math.max(2, x(row.q75) - x(row.q25))}" height="18" rx="4" fill="${color}" fill-opacity="0.25" stroke="${color}"/>`;
    out += `<line x1="${x(row.q50)}" x2="${x(row.q50)}" y1="${yy - 11}" y2="${yy + 11}" stroke="#e6edf7" stroke-width="2.5"/>`;
    out += '</g>';
  });
  $('#chart-scen').innerHTML = `${out}</svg>`;
  renderScenarioTable();
}

function renderScenarioTable() {
  const scen = STATE.scen;
  if (!scen) return;
  const rows = [...scen.rows].sort((a, b) => b.risk_adjusted_score - a.risk_adjusted_score);
  $('#scen-table').innerHTML = `
    <thead><tr><th>Scenario</th><th class="num">Median</th><th class="num">Mean</th><th class="num">90% range</th><th class="num">P(near zero)</th><th class="num">Cost units</th><th class="num">Stability</th><th class="num">Risk-adjusted</th><th>Top bottleneck</th></tr></thead>
    <tbody>${rows.map((row) => `
      <tr class="clickable${row.name === STATE.base ? ' active' : ''}" data-scenario="${row.name}" title="${escapeHtml(row.description)}">
        <td><strong>${row.name}</strong></td>
        <td class="num">${num(row.q50, 0)}</td><td class="num">${num(row.mean, 1)}</td>
        <td class="num">${num(row.q05, 0)} – ${num(row.q95, 0)}</td><td class="num">${pct(row.probability_near_zero, 0)}</td>
        <td class="num">${num(row.mean_cost_units, 1)}</td><td class="num">${num(row.mean_stability_score, 1)}</td>
        <td class="num">${num(row.risk_adjusted_score, 1)}</td><td>${escapeHtml(row.top_bottleneck || '–')}</td>
      </tr>`).join('')}</tbody>`;
  for (const tr of document.querySelectorAll('#scen-table tr[data-scenario]')) {
    tr.addEventListener('click', () => {
      selectScenario(tr.dataset.scenario);
      renderScenarios();
      window.scrollTo({ top: $('.kpis').offsetTop - 70, behavior: 'smooth' });
    });
  }
}

function renderCalibration() {
  const rows = STATE.meta.calibration;
  $('#calib-table').innerHTML = `
    <thead><tr><th>Parameter</th><th class="num">Anchor</th><th>Units</th><th>Confidence</th><th>Why this value</th><th>Sources</th></tr></thead>
    <tbody>${rows.map((row) => `
      <tr>
        <td><strong>${escapeHtml(row.label)}</strong></td>
        <td class="num">${row.baseline < 0.001 || row.baseline > 1e5 ? sci(row.baseline, 2) : row.baseline}</td>
        <td>${escapeHtml(row.units)}</td>
        <td><span class="badge ${row.confidence}">${row.confidence}</span></td>
        <td class="muted small">${escapeHtml(row.rationale)}</td>
        <td class="sources">${row.sources.length ? row.sources.map((source) => `<a href="${escapeHtml(source.url)}" target="_blank" rel="noopener">${escapeHtml(source.title)}</a>`).join('') : '<span class="muted small">engineering estimate</span>'}</td>
      </tr>`).join('')}</tbody>`;
}

// ── Tooltips ──────────────────────────────────────────────────────────────────
function bindTooltips() {
  const tooltip = $('#tooltip');
  document.addEventListener('mousemove', (event) => {
    const target = event.target.closest?.('[data-tip]');
    if (!target) { tooltip.hidden = true; return; }
    tooltip.textContent = target.getAttribute('data-tip');
    tooltip.hidden = false;
    const pad = 14;
    const { innerWidth, innerHeight } = window;
    const rect = tooltip.getBoundingClientRect();
    tooltip.style.left = `${Math.min(event.clientX + pad, innerWidth - rect.width - 8)}px`;
    tooltip.style.top = `${Math.min(event.clientY + pad, innerHeight - rect.height - 8)}px`;
  });
}

boot();
