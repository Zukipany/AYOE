'use strict';

// "Explain it like I'm 4" bubbles. Every element with data-explain="<key>" gets a speech
// bubble with three parts: what you see, what happens, and (when a simulation has run)
// what the numbers on screen are right now. Uses STATE and the formatters from app.js.

const EXPLAIN = {
  mode: {
    icon: '🔌', title: 'Live or demo?',
    see: 'A little sign at the top that says how this page is working.',
    happens: () => (STATE.mode === 'live'
      ? '"Live engine" means a real computer program is doing all the maths right now. Every time you move a knob it plays the whole game again.'
      : '"Static demo" means the answers were worked out earlier and saved, like a photo. To move the knobs yourself, run "ayoe serve" on your own computer.'),
  },
  pipeline: {
    icon: '🏁', title: 'The particle race',
    see: 'Tiny dots racing from left to right. 🟠 Orange dots are protons, tiny bits of normal stuff. 🔵 Blue dots are antiprotons, their mirror twins. 🩷 Pink dots are anti-atoms. The dashed lines are 8 doors, and the pink box at the end is a jar.',
    happens: 'At every door some dots don\'t make it. Each little ring is a dot going "poof!". The dots also get slower and slower, because the machine keeps pressing the brakes. Only a few dots ever reach the jar, and those are the anti-atoms we get to keep. There are far too many particles to draw, so one dot stands for a whole crowd.',
    now: (sim) => {
      const sample = sim.samples[STATE.sample];
      return `This try started with ${sci(sample.counts[0])} protons and ended with ${sample.final_yield.toLocaleString('en-US')} anti-atoms in the jar.`;
    },
  },
  samples: {
    icon: '🎲', title: 'Worst, median, best',
    see: 'Three buttons that choose which try the race above shows.',
    happens: 'The computer played the whole game hundreds of times, and every try comes out a bit different, just like rolling dice. "Worst" is the unluckiest try, "Best" is the luckiest, and "Median" is a normal one right in the middle. The ↻ button starts the race again.',
    now: (sim) => `Out of ${sim.runs.toLocaleString('en-US')} tries: the worst gave ${sim.samples.worst.final_yield}, the middle one ${sim.samples.median.final_yield} and the best ${sim.samples.best.final_yield} anti-atoms.`,
  },

  'stage:protons': {
    icon: '⚾', title: 'Protons on target',
    see: 'How many protons we start with.',
    happens: 'A huge accelerator at CERN throws a giant bunch of protons. It\'s an enormous number: about 1,500 protons for every person on Earth!',
    now: (sim) => `In a normal try, ${sci(sim.initial.q50)} protons go in.`,
  },
  'stage:proton_beam_input': {
    icon: '🎯', title: 'Aiming the beam',
    see: 'How many protons really reach the metal block.',
    happens: 'The machine aims all the protons at a metal block, like throwing lots and lots of balls at a wall. Almost all of them hit it.',
  },
  'stage:antiproton_creation': {
    icon: '💥', title: 'Making antiprotons',
    see: 'How many antiprotons get made.',
    happens: 'The protons smash into the metal block super hard. Nearly every crash makes nothing we can use. Only about 1 crash in a million makes an antiproton, the mirror twin of a proton. This is the biggest drop of the whole trip!',
  },
  'stage:particle_selection': {
    icon: '🧺', title: 'Picking the good ones',
    see: 'How many antiprotons we keep after sorting.',
    happens: 'The new antiprotons fly out every which way and at all sorts of speeds. Magnets sort them, and we only keep the ones going the right way at the right speed. It\'s like picking only the red balls out of a ball pit.',
  },
  'stage:ad_survival': {
    icon: '🏎️', title: 'The big slow-down track',
    see: 'How many antiprotons are still there after the first racetrack.',
    happens: 'The Antiproton Decelerator is a big round racetrack. Instead of making things faster, it presses the brakes lap after lap until the antiprotons are much slower. Most of them make it.',
  },
  'stage:elena_survival': {
    icon: '🛝', title: 'The little slow-down track',
    see: 'How many antiprotons are left after the second, smaller racetrack.',
    happens: 'ELENA is a smaller racetrack that brakes them even more. Now they are slow enough to catch. They are still faster than a rocket, though!',
  },
  'stage:trap_capture': {
    icon: '🫙', title: 'Catching them in a trap',
    see: 'How many antiprotons get caught.',
    happens: 'A trap made of magnets and electricity tries to catch the antiprotons, like catching fireflies in a jar. They are slippery, so most of them get away.',
  },
  'stage:antihydrogen_formation': {
    icon: '🤝', title: 'Making anti-atoms',
    see: 'How many anti-atoms get made.',
    happens: 'Inside the trap we add positrons, which are tiny mirror twins of electrons. When an antiproton and a positron hold hands, they become an anti-atom called antihydrogen!',
  },
  'stage:final_usable_yield': {
    icon: '🧲', title: 'Keeping the anti-atoms',
    see: 'How many anti-atoms we get to keep. This is the final score!',
    happens: 'Anti-atoms are very hard to hold, because magnets only pull on them a tiny bit. If one touches the wall it goes "poof", because antimatter and normal matter destroy each other. Only about 6 out of every 10,000 stay floating in the magnetic bowl.',
  },

  'kpi:median': {
    icon: '🎯', title: 'The normal score',
    see: 'The number of anti-atoms in a normal try.',
    happens: 'Imagine lining up every try from the smallest score to the biggest. The median is the one standing right in the middle: half the tries got less and half got more.',
    now: (sim) => `Right now a normal try gives ${num(sim.stats.median, 0)} anti-atoms.`,
  },
  'kpi:interval': {
    icon: '↔️', title: 'The usual range',
    see: 'Two numbers: a low one and a high one.',
    happens: 'Nine tries out of ten land between these two numbers. Only really unlucky or really lucky tries end up outside.',
    now: (sim) => `Most tries give between ${num(sim.stats.q05, 0)} and ${num(sim.stats.q95, 0)} anti-atoms.`,
  },
  'kpi:mean': {
    icon: '➗', title: 'The average',
    see: 'The average score.',
    happens: 'Put the anti-atoms from every try into one big pile, then share them out evenly. A few super-lucky tries make the pile bigger, so the average is usually higher than the normal score.',
  },
  'kpi:risk': {
    icon: '😟', title: 'Almost-nothing tries',
    see: 'How often a try ends with almost nothing.',
    happens: 'Some tries end with only a handful of anti-atoms or none at all. This number says how often that happens. Smaller is better!',
    now: (sim) => `${Math.round(sim.stats.probability_near_zero * sim.runs)} of the ${sim.runs.toLocaleString('en-US')} tries ended with ${sim.near_zero_threshold} anti-atoms or fewer.`,
  },
  'kpi:rate': {
    icon: '⏱️', title: 'Anti-atoms per hour',
    see: 'How many anti-atoms you would collect in one hour.',
    happens: 'One try takes a few minutes. If the machine keeps going for a whole hour, this is roughly how many anti-atoms you would have in your jar.',
  },
  'kpi:bottleneck': {
    icon: '🍾', title: 'The bottleneck',
    see: 'The step that loses the most.',
    happens: 'The neck of a bottle is the narrow bit where everything gets stuck when you pour. Our bottleneck is the step where the most get lost, so making that step better helps the most.',
    now: (sim) => `Right now the bottleneck is "${sim.bottlenecks[0].stage_label}".`,
  },

  'controls:scenario': {
    icon: '🌦️', title: 'What kind of day?',
    see: 'A menu of different kinds of days at the lab.',
    happens: '"aggressive" is a great day when everything works really well. "conservative" is a tired, grumpy day. The others each make one part of the machine better or worse. Pick one and the computer plays the game again.',
    now: () => `You picked "${STATE.base}": ${scenarioMeta(STATE.base).description}`,
  },
  'controls:machine': {
    icon: '🎛️', title: 'The machine knobs',
    see: 'Knobs that change how the machine works.',
    happens: [
      '🧲 Magnetic field: how strong the magnets are. Stronger magnets steer and hold better.',
      '🫧 Vacuum quality: how empty the pipes are. Leftover air bumps into antimatter and makes it go poof.',
      '❄️ Trap temperature: how cold the trap is. Colder means calmer, and calm things are easier to catch.',
      '💞 Positron mixing and inventory: how many positron partners there are, and how well they mix.',
      '🧱 Target density: how thick the metal block is.',
      '⚡ Pulse length: how short the burst of protons is.',
      '📏 Beam stability: how steady the beam is.',
      '🌀 Machine volatility: how wobbly and unlucky the machine is.',
    ].join('\n'),
    now: () => (STATE.mode === 'live' ? 'Move a knob and the computer plays all the tries again with the new setting.' : null),
  },
  'controls:stages': {
    icon: '🔧', title: 'Step boosters',
    see: 'One slider for each step of the trip.',
    happens: 'Slide one to the right and that step keeps more particles. Slide it to the left and it loses more. It\'s a way to ask: "What if we fixed just this one step?"',
  },
  'controls:runs': {
    icon: '🎲', title: 'Tries and dice',
    see: 'How many times we play, and the dice number.',
    happens: '"Runs" is how many tries the computer plays. More tries give a better answer but take a little longer. The "seed" is like the number on a pack of dice: the same seed always rolls the same numbers, so you can change one knob and compare fairly. The 🎲 button picks new dice.',
  },

  'chart:funnel': {
    icon: '🔻', title: 'The shrinking line',
    see: 'A line that goes down, down, down from left to right.',
    happens: 'Each dot shows how many are still there after each step. The ladder on the left is special: every step up the ladder means 100 times more! That\'s the only way giant numbers and tiny numbers can fit in one picture. The shaded band shows where most tries land, and the faint lines are single tries.',
  },
  'chart:hist': {
    icon: '📊', title: 'How the scores spread out',
    see: 'Bars that look like a city skyline.',
    happens: 'Every try drops one block into the bar that matches its score. Tall bars are scores that happen a lot. The red zone on the left is the "almost nothing" area. The green line is the normal score and the orange line is the average.',
  },
  'chart:loss': {
    icon: '🕳️', title: 'Where they get lost',
    see: 'One bar for each step.',
    happens: 'A longer bar means that step loses more. We measure it fairly: losing 9 out of 10 counts the same at every step, whether you had a million or just ten. Fix the longest bar first!',
    now: (sim) => `The longest bar is "${sim.bottlenecks[0].stage_label}".`,
  },
  'chart:regimes': {
    icon: '🌤️', title: 'The machine\'s mood',
    see: 'Four bars, one for each machine mood.',
    happens: 'Machines have good days and bad days too. For every try the computer secretly picks a mood: favourable (happy), nominal (normal), stressed (grumpy) or unstable (very grumpy). A taller bar means more anti-atoms on that kind of day. The small words underneath say how often that mood happened.',
  },
  'chart:corr': {
    icon: '🎢', title: 'Who makes the scores jump',
    see: 'One bar for each step.',
    happens: 'Every step is a bit lucky or unlucky on each try. A long bar means that when this step gets lucky, the whole try usually gets lucky too. The long bars are the steps that make the scores jump around the most.',
  },
  'chart:sens': {
    icon: '🌪️', title: 'Which knob matters most?',
    see: 'Red and green bars that look like a tornado.',
    happens: 'We turn each knob up a little (green) and down a little (red), then play all the tries again. A bar going right means more anti-atoms and a bar going left means fewer. The longest bars at the top are the most important knobs. Look at trap temperature: it\'s flipped, because a colder trap catches more!',
  },
  'chart:scen': {
    icon: '🏆', title: 'The race of the days',
    see: 'One row for each kind of day.',
    happens: 'The box shows where most tries land, and the white line is the normal try. Further right means more anti-atoms. Click a row in the table to try that kind of day yourself!',
  },
  calibration: {
    icon: '📚', title: 'Real numbers from real scientists',
    see: 'A table of numbers, each with a link.',
    happens: 'We didn\'t make these numbers up. They come from reports by scientists at CERN, the lab in Switzerland that really makes antimatter. That\'s how our game knows how the real machine behaves. "low" confidence means it\'s a careful guess.',
  },
};

// Stage bubbles without their own "now" text report that stage's live numbers.
function stageNow(key, sim) {
  const stage = sim.stages.find((item) => `stage:${item.key}` === key);
  if (!stage) return null;
  const kept = stage.mean_effective_efficiency;
  const share = kept >= 0.01 ? `about ${Math.round(kept * 100)} out of every 100`
    : kept >= 1e-4 ? `about ${Math.round(kept * 10000)} out of every 10,000`
      : `about ${Math.max(1, Math.round(kept * 1e6))} out of every million`;
  return `In a normal try ${sci(stage.mean_input)} go in and ${sci(stage.output.q50)} come out. This step keeps ${share}.`;
}

const TOUR = [
  'pipeline', 'samples', 'stage:antiproton_creation', 'stage:trap_capture', 'stage:final_usable_yield',
  'kpi:median', 'kpi:bottleneck', 'controls:scenario', 'controls:machine',
  'chart:funnel', 'chart:hist', 'chart:loss', 'chart:regimes', 'chart:sens', 'chart:scen',
];

const Explain = {
  pop: null,
  trigger: null,
  tourIndex: -1,

  init() {
    this.pop = document.getElementById('explain-pop');
    document.addEventListener('click', (event) => {
      const button = event.target.closest('.explain-btn');
      if (button) {
        // Buttons can sit inside <summary> or <label>; don't toggle or focus those.
        event.preventDefault();
        event.stopPropagation();
        if (this.trigger === button && !this.pop.hidden) this.close();
        else { this.tourIndex = -1; this.open(button); }
        return;
      }
      if (!this.pop.hidden && !this.pop.contains(event.target)) this.close();
    }, true);
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && !this.pop.hidden) this.close();
    });
    const reposition = () => { if (!this.pop.hidden && this.trigger) this.place(this.trigger); };
    window.addEventListener('scroll', reposition, { passive: true });
    window.addEventListener('resize', reposition);
    document.getElementById('tour-btn').addEventListener('click', () => this.startTour());
  },

  open(button) {
    const entry = EXPLAIN[button.dataset.explain];
    if (!entry) return;
    this.trigger = button;
    const resolve = (value) => (typeof value === 'function' ? value() : value);
    let now = null;
    try {
      if (entry.now && STATE.sim) now = entry.now(STATE.sim);
      else if (entry.now && !entry.now.length) now = entry.now();
      else if (STATE.sim) now = stageNow(button.dataset.explain, STATE.sim);
    } catch { now = null; }
    const inTour = this.tourIndex >= 0;
    this.pop.innerHTML = `
      <div class="explain-head">
        <span class="explain-icon" aria-hidden="true">${entry.icon}</span>
        <h3 id="explain-title">${escapeHtml(entry.title)}</h3>
        <button type="button" class="explain-close" aria-label="Close">×</button>
      </div>
      <div class="explain-part"><div class="explain-label">👀 What you see</div><p>${escapeHtml(resolve(entry.see))}</p></div>
      <div class="explain-part"><div class="explain-label">✨ What happens</div><p>${escapeHtml(resolve(entry.happens))}</p></div>
      ${now ? `<div class="explain-part explain-now"><div class="explain-label">🔢 Right now</div><p>${escapeHtml(now)}</p></div>` : ''}
      <div class="explain-foot">
        ${inTour ? `<span class="explain-step">${this.tourIndex + 1} / ${this.tourSteps().length}</span>
          <span class="explain-actions">${this.tourIndex > 0 ? '<button type="button" class="ghost" data-tour="back">◀ Back</button>' : ''}
          <button type="button" class="primary" data-tour="next">${this.tourIndex === this.tourSteps().length - 1 ? 'Finish 🎉' : 'Next ▶'}</button></span>`
        : '<span></span><button type="button" class="primary" data-tour="close">Got it! 👍</button>'}
      </div>`;
    this.pop.hidden = false;
    for (const element of document.querySelectorAll('.explain-btn.is-open')) element.classList.remove('is-open');
    button.classList.add('is-open');
    this.pop.querySelector('.explain-close').addEventListener('click', () => this.close());
    for (const action of this.pop.querySelectorAll('[data-tour]')) {
      action.addEventListener('click', () => {
        if (action.dataset.tour === 'next') this.step(1);
        else if (action.dataset.tour === 'back') this.step(-1);
        else this.close();
      });
    }
    this.place(button);
    this.pop.querySelector('.primary').focus({ preventScroll: true });
  },

  place(button) {
    const rect = button.getBoundingClientRect();
    const width = Math.min(380, window.innerWidth - 24);
    this.pop.style.width = `${width}px`;
    const height = this.pop.offsetHeight;
    const left = Math.min(Math.max(12, rect.left + rect.width / 2 - width / 2), window.innerWidth - width - 12);
    const below = rect.bottom + 12 + height < window.innerHeight || rect.top - 12 - height < 0;
    const top = below ? rect.bottom + 12 : rect.top - 12 - height;
    this.pop.style.left = `${left}px`;
    this.pop.style.top = `${Math.max(8, top)}px`;
    this.pop.style.setProperty('--tail-x', `${Math.min(Math.max(18, rect.left + rect.width / 2 - left), width - 18)}px`);
    this.pop.classList.toggle('above', !below);
  },

  close() {
    this.pop.hidden = true;
    this.tourIndex = -1;
    if (this.trigger) {
      this.trigger.classList.remove('is-open');
      this.trigger.focus({ preventScroll: true });
    }
    this.trigger = null;
  },

  tourSteps() {
    return TOUR.filter((key) => document.querySelector(`.explain-btn[data-explain="${key}"]`));
  },

  startTour() {
    this.tourIndex = 0;
    this.show(this.tourSteps()[0]);
  },

  step(direction) {
    const steps = this.tourSteps();
    const next = this.tourIndex + direction;
    if (next >= steps.length) { this.close(); return; }
    this.tourIndex = Math.max(0, next);
    this.show(steps[this.tourIndex]);
  },

  show(key) {
    const button = document.querySelector(`.explain-btn[data-explain="${key}"]`);
    if (!button) return;
    const details = button.closest('details');
    if (details) details.open = true;
    const index = this.tourIndex;
    this.pop.hidden = true;
    button.scrollIntoView({ block: 'center', behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
    setTimeout(() => { this.tourIndex = index; this.open(button); }, 420);
  },
};

function explainButton(key, label) {
  const entry = EXPLAIN[key];
  const title = label || (entry ? entry.title : 'this');
  return `<button type="button" class="explain-btn" data-explain="${key}" aria-label="Explain simply: ${escapeHtml(title)}" title="Explain it simply">?</button>`;
}

Explain.init();
