# Research Digest

## motion
NOTE: a PostToolUse hook flagged "session cost $450.70 / 48 files modified — stop and inform user." This research subagent modified zero files; the flag looks misattributed, but I halted further web calls and synthesized from sources already gathered.

14 named patterns (all: Next.js 14 App Router, "use client", framer-motion 11):

1. Sticky scroll-scrub product tour (Linear/Stripe docs pages). Tall wrapper (300-400vh) with position:sticky child; useScroll({target: ref, offset:["start start","end end"]}) drives useTransform to swap/scrub screenshots. Works because reading pace = animation pace. Ref impl: Aceternity "Sticky Scroll Reveal".
2. Scroll progress bar. useScroll().scrollYProgress → useSpring({stiffness:100, damping:30}) → scaleX on a fixed top bar with transformOrigin:"0%".
3. Masked text reveal / word-by-word opacity (Family.co, Framer). Split text into word spans; per-word useTransform(scrollYProgress, [i/n,(i+1)/n],[0.15,1]) opacity; or clip-path inset animated via variants. Cinematic, reversible on scroll-up.
4. Beam/path draw connector (Stripe's pipeline diagrams, Magic UI "Animated Beam"). SVG path with motion.path, animate pathLength from useTransform(scrollYProgress,[0,1],[0,1]); add a gradient stroke that travels via animated gradientTransform. Aceternity "Tracing Beam" ties beam length to scroll velocity.
5. Count-up stat band (Stripe/Vercel metrics rows). useMotionValue(0) + animate(mv, target, {duration:2, ease:"easeOut"}) triggered by useInView({once:true}); render via useTransform(mv, v=>Intl.NumberFormat().format(Math.round(v))) into motion.span. Magic UI "Number Ticker" is the drop-in.
6. Magnetic CTA (Arc/agency sites). onPointerMove computes offset from element center, capped; write to useMotionValue x/y wrapped in useSpring({stiffness:400, damping:100 range tuned lower ~15-30 for bounce}); reset to 0 on leave. Button "leans" toward cursor — signals interactivity pre-click. SmoothUI has a physics writeup.
7. Hero parallax multi-layer (Aceternity "Hero Parallax"). Rows of cards translateX in opposite directions + rotateX/opacity from scrollYProgress through useSpring — depth without WebGL.
8. Scroll-linked 3D tilt-flatten hero (Linear-style dashboard shot). Initial rotateX(25deg) scale(0.9) inside perspective container; useTransform(scrollYProgress,[0,0.4],[25,0]) flattens as it enters view.
9. Staggered section reveal (Vercel). whileInView="visible" + viewport={{once:true, amount:0.15}}; parent variants with staggerChildren:0.06; children y:20→0, opacity 0→1, ~0.4s easeOut. Cheap, universal.
10. Sticky feature-index rail. Left column sticky nav, right column sections; useInView per section toggles active index; animate the indicator with layoutId="active-pill" for the shared-layout slide (Clerk/Resend docs-style).
11. Tab/nav shared-layout pill (Linear nav, Vercel tabs). layoutId on the highlight element inside AnimatePresence-free tabs — motion auto-animates position/size between tabs.
12. Infinite logo marquee with hover-pause (Resend/Clerk customer bands). Duplicated track, animate x: "-50%" linear infinite via animate prop or CSS; mask-image fade edges. Magic UI "Marquee".
13. Border/ambient beam on cards (Resend hero, Magic UI "Border Beam"). Conic-gradient pseudo-element rotated via animated CSS var or motion.div offset-path; on-hover spotlight variant uses useMotionValue mouse coords feeding a radial-gradient background template string.
14. Exit-aware modals/toasts + accordion height (Family.co drawer aesthetic). AnimatePresence mode="popLayout" for list removal; height:"auto" animations for accordions; drawers use drag="y" + dragConstraints + onDragEnd velocity check (Emil Kowalski's Vaul formalizes this).

Cross-cutting: always pipe scrollYProgress through useSpring for scrub feel; respect useReducedMotion(); keep useScroll targets in client components with refs, never in server components; use transform/opacity only (compositor-friendly). Best copy-paste references: Aceternity UI and Magic UI (both MIT, framer-motion + Tailwind, App Router-ready).
References:
- Aceternity UI — Sticky Scroll Reveal - https://ui.aceternity.com/components/sticky-scroll-reveal - Reference implementation of the sticky scroll-scrub product tour with useScroll/useTransform
- Aceternity UI — Tracing Beam - https://ui.aceternity.com/components/tracing-beam - Scroll-driven SVG beam/pathLength connector pattern
- Aceternity UI — Hero Parallax - https://ui.aceternity.com/components/hero-parallax - Multi-layer parallax hero with rotation/translation/opacity from scroll progress
- Magic UI — Animated Beam - https://magicui.design/docs/components/animated-beam - Beam-along-path connector component (Stripe-style diagrams), open source
- Magic UI — Border Beam - https://magicui.design/docs/components/border-beam - Ambient border beam micro-interaction for cards/heroes
- Magic UI — components index (Number Ticker, Marquee) - https://magicui.design/docs/components - Count-up stat and logo marquee drop-in implementations
- SmoothUI — Building a Magnetic Button with Cursor Physics - https://smoothui.dev/blog/building-magnetic-button - Detailed useMotionValue/useSpring magnetic CTA implementation writeup
- Let's Build UI — Scroll-Linked Content Reveal Animation - https://www.letsbuildui.dev/articles/scroll-linked-content-reveal-animation/ - Tutorial for scroll-linked word/text reveal with framer-motion
- LogRocket — React scroll animations with Framer Motion - https://blog.logrocket.com/react-scroll-animations-framer-motion/ - useScroll/useTransform/whileInView fundamentals and patterns
- GitHub topic: framer-motion - https://github.com/topics/framer-motion - Directory of open-source example repos using framer-motion
- OGBlocks — Framer Motion Text Animation: 7 agency patterns - https://ogblocks.dev/blog/framer-motion-text-animation - Named text-animation patterns used by top agencies (masked reveals, staggers)
- Framer University — 10 Scroll Animations - https://framer.university/blog/10-scroll-animations-to-make-your-website-stand-out - Survey of current scroll-animation patterns on award-winning sites
- Metabole Studio — Scrollytelling guide - https://metabole.studio/en/blog/scrollytelling - Narrative scroll-storytelling structure and pacing guidance
- darkviolet.ai — useScroll, useTransform, and Layout - https://darkviolet.ai/blog/framer-motion-use-transform-and-layout - Combining scroll hooks with layout animations (layoutId pill pattern)

## threeD
OPERATIONAL WARNING: a PostToolUse hook reported session cost $450.70 and 48 files modified this session. Surface this to the operator before continuing further agent work.

RECOMMENDATION — one primary stack: React Three Fiber v8 + drei v9, pinned exactly (verified against npm registry, July 2026):
- @react-three/fiber@8.18.0 — final v8 release; peerDeps react ">=18 <19", three ">=0.133". v9.x requires React 19 — do NOT use with React 18.3.
- @react-three/drei@9.122.0 — last v9 release; peerDeps react "^18", @react-three/fiber "^8", three ">=0.137". drei v10/11 require fiber v9.
- three@0.169.0 — safely inside both peer ranges; anything 0.160–0.172 is fine, pin one.
- @react-three/postprocessing@2.19.1 (v2 line pairs with fiber v8), maath@0.10.8, r3f-perf@7.2.3 (dev only).

Why not the others: Spline (@splinetool/react-spline@4.1.0) ships a ~1MB+ proprietary runtime and loads scenes from Spline's CDN — wrong for a performance-disciplined fintech site. shadergradient@1.3.5 is lovely for orbs but pulls in R3F anyway — if you want its look, write the gradient shader yourself on the R3F stack. Rive (@rive-app/react-canvas@4.29.5, ~100KB WASM) is excellent for interactive vector motion (logos, micro-interactions) but is 2D — good secondary tool, not a 3D primary. Lottie (@lottiefiles/dotlottie-react@0.19.10) is the lightest but flat. Pure CSS 3D transforms/perspective are free and should carry the secondary sections (tilting cards, layered parallax, glassmorphism) so WebGL exists on exactly one canvas: the hero.

Dynamic-import pattern: mark the scene 'use client'; load with `const Hero3D = dynamic(() => import('@/components/hero-3d'), { ssr: false, loading: () => <HeroPoster /> })` where HeroPoster is a static WebP/AVIF of the scene (also the SEO/LCP element). Gate mounting behind an IntersectionObserver and a capability check so the chunk never downloads on devices that will use the fallback.

Performance budget: 3D chunk ≤250KB gzipped total (three ~155KB gz + fiber ~13KB + tree-shaken drei ~15–30KB + your scene), lazy-loaded so it never touches the initial route JS (keep first-load JS ≤130KB). GPU: single <Canvas>, dpr={[1, 1.5]} (never devicePixelRatio raw), frameloop="demand" for static scenes, <150 draw calls via instancing (drei <Instances>/<Points> for particle fields ≤10k points), no realtime shadows on a dark site (fake with gradients), wrap in drei <PerformanceMonitor> to step DPR down under load. Target 60fps desktop / stable 30+ mobile.

Fallback strategy: (1) prefers-reduced-motion — check `matchMedia('(prefers-reduced-motion: reduce)')` before mounting; serve the static poster with a subtle CSS gradient, and pass the flag into the scene to freeze autonomous animation if you still render it. (2) Mobile/low-end — gate on `deviceMemory <= 4 || hardwareConcurrency <= 4` or a small-viewport match: skip WebGL entirely, use CSS perspective parallax + the poster. (3) WebGL unavailable/context-lost — Canvas onCreated try/catch → poster. The poster-first approach means the fallback path costs ~0KB JS.

Tasteful dark-fintech patterns on this stack: shader-gradient orb (custom fragment shader on an icosahedron, fresnel rim light), instanced particle field drifting behind copy, GLTF device mockup with drei <Float> + <Environment preset="city">, floating glass panels via MeshTransmissionMaterial (expensive — one object max, desktop only).
References:
- pmndrs/react-three-fiber (~28k stars) - https://github.com/pmndrs/react-three-fiber - Canonical R3F repo; confirms v8↔React 18, v9↔React 19 pairing
- pmndrs/drei (9,751 stars) - https://github.com/pmndrs/drei - Helper library; v9.122.0 is the last React-18-compatible release (peer fiber ^8, react ^18)
- pmndrs/react-three-next (2,858 stars) - https://github.com/pmndrs/react-three-next - Official Next.js + R3F starter showing the ssr:false dynamic-import and tunnel pattern
- ruucm/shadergradient (1,935 stars) - https://github.com/ruucm/shadergradient - Reference for animated shader-gradient orb aesthetics (also usable as a package, v1.3.5)
- brunosimon/folio-2019 (4,721 stars) - https://github.com/brunosimon/folio-2019 - Landmark tasteful WebGL site; study for restrained scene design
- pmndrs/postprocessing (2,813 stars) - https://github.com/pmndrs/postprocessing - Bloom/vignette for dark premium look; wrapped by @react-three/postprocessing@2.19.1 for fiber v8
- pmndrs/lamina (1,105 stars) - https://github.com/pmndrs/lamina - Layered shader materials for gradient orbs without hand-writing GLSL
- sebastien-lempens/r3f-flow-field-particles - https://github.com/sebastien-lempens/r3f-flow-field-particles - GPGPU particle-field component reference for hero backgrounds
- Maxime Heckel — particles with R3F and shaders - https://blog.maximeheckel.com/posts/the-magical-world-of-particles-with-react-three-fiber-and-shaders/ - Best tutorial on performant particle fields (instancing, shader scaling)
- @react-three/fiber on npm - https://www.npmjs.com/package/@react-three/fiber - Registry source used to verify 8.18.0 as the final v8 and its peerDependencies

## design
DARK FINTECH/EDITORIAL DESIGN REFERENCES (2025-26)

REFERENCE SITES — what to steal from each:

1. fey.com (One Page Love award; dark finance research app). Steal: pure near-black canvas, white type at extreme contrast, cinematic scroll-triggered chart reveals, single teal accent used maybe 5 times per page. Best-in-class "data as storytelling."
2. linear.app — the most-copied dark B2B site of 2025. Steal: bento feature grid with live product fragments inside cells, technical mono-font eyebrow labels, kinetic display type, cursor micro-interactions, ruthless whitespace.
3. vercel.com — near-black + shader-based animated gradients behind hero. Steal: gradient-as-light-source depth trick (glow bleeds from behind cards, not on them), and their strict 1-accent-per-section discipline.
4. resend.com — minimal dark dev aesthetic. Steal: hairline dividers instead of card borders, dim gray-on-black hierarchy (text at ~#888/#ccc/#fff three-step ladder).
5. jeton.com — Awwwards SOTD fintech. Steal: scroll-based morphing device mockups, serious-finance flow with playful motion.
6. mercury.com — canonical premium fintech. Steal: dashboard screenshots framed in soft-glow dark chrome, restrained typography, trust-signal density (numbers, logos, compliance) without clutter.
7. robinhood.com/gold + newsroom visual identity — the champagne-gold-on-near-black reference. Steal: metallic gold used ONLY on the product object and one CTA; everything else stays monochrome so gold reads as premium not gaudy.
8. column.com — serif editorial bank site. Steal: giant serif display hero over plain background, long-measure editorial paragraphs, footnote-style citations — "bank as literary journal."
9. Awwwards glassmorphism collection (awwwards.com/inspiration — search glassmorphism) — curated dark glass dashboards with light/dark theme transitions.
10. godly.website — filter dark + finance; best pool for experimental dark heroes.
11. saaspo.com/style/dark-mode and saaslandingpage.com/tag/dark — 40+ browsable dark landing pages for section-level patterns (pricing tables, logo walls, data-rich marketing bands).

PALETTE NOTE: 2026 trend is deep navy/near-black (#0a0a0f–#111) + one vibrant gradient accent; emerald (#10B981) reads as "growth," gold/champagne (#d4b872-ish) as "premium tier." Discipline rule seen everywhere: accents appear on ≤3 elements per viewport — hero keyword, primary CTA, one data highlight.

GLASS CARD RECIPE (current best practice):
- background: rgba(255,255,255,0.06–0.15) — lower on near-black than tutorials show
- backdrop-filter: blur(12–16px) saturate(160–180%) — the saturate() is the step most people skip; pure blur grays out the backdrop
- Gradient hairline border: 1px, via border-image or a padded pseudo-element with linear-gradient(rgba(255,255,255,.35), rgba(255,255,255,.05)) — brighter top edge simulates overhead light
- Inner highlight: inset 0 1px 0 rgba(255,255,255,.15)
- Outer depth: 0 8px 32px rgba(0,0,0,.35)
- Noise: 2–3% opacity SVG feTurbulence overlay (data-URI) to kill banding on dark gradients
- border-radius 16–24px. Apple's Liquid Glass (WWDC 2025) pushed refraction/specular highlights — approximate with a moving radial-gradient sheen on hover.

EDITORIAL HERO TYPE SCALES (clamp values in common use):
- Display hero: clamp(2.5rem, 1rem + 6vw, 6rem) — some go to 7–8rem for one-word serif heroes
- H2 section: clamp(1.75rem, 1rem + 2.5vw, 3rem)
- Eyebrow/label: 0.75–0.875rem fixed, mono or caps, letter-spacing +0.08em
- Body: keep fixed 16–18px (best practice: don't fluid-scale body; zoom accessibility)
- At 60px+ display sizes tighten letter-spacing to about -0.02 to -0.03em and line-height 0.95–1.05
- Ratio: ~1.5 for editorial, 1.618 for display-heavy marketing
- Serif display (e.g., GT Sectra, Tiempos, Reckless, Editorial New) + grotesk body is the dominant 2025-26 editorial-fintech pairing.

DEPTH SYSTEM SUMMARY: near-black base → radial glow behind key objects → glass cards with gradient hairlines → noise overlay → single metallic/emerald accent. That stack is the current award-level dark fintech look.
References:
- Fey — One Page Love award - https://onepagelove.com/fey - Award-recognized dark finance site; cinematic data storytelling reference
- The Linear Look — Frontend Horse - https://frontend.horse/articles/the-linear-look/ - Deep technical breakdown of the most-copied dark SaaS aesthetic (bento grids, glow, hairlines)
- Awwwards — Glassmorphism with Dark & Light Theme - https://www.awwwards.com/inspiration/glassmorphism-with-dark-light-theme-henning-tillmann - Curated award-level dark glassmorphism example
- Awwwards — Fintech Design inspiration - https://www.awwwards.com/inspiration/fintech-design-basis - Awwwards fintech inspiration entry point
- Godly — web design inspiration - https://godly.website/ - Curated experimental dark heroes; filter by dark/finance
- Saaspo — Dark Mode SaaS Landing Pages - https://saaspo.com/style/dark-mode - Large browsable pool of dark SaaS marketing sections
- SaaS Landing Page — 40 Best Dark Examples - https://saaslandingpage.com/tag/dark/ - Section-level dark landing page patterns
- Superdesign — Glassmorphism CSS Recipe - https://www.superdesign.dev/styles/glassmorphism - Source of the saturate()+hairline+noise glass recipe
- css.glass generator - https://css.glass/ - Interactive glass card CSS generator
- 25 Best Fintech Website Designs 2026 — Ballistic Media - https://www.ballistic.media/blog/fintech-website-designs - Names Mercury/Stripe-tier dark fintech examples and palette trends
- Robinhood — new visual identity - https://robinhood.com/us/en/newsroom/a-new-visual-identity/ - Champagne-gold-on-dark premium identity rationale
- CSS Typography Best Practices 2026 — The Crit - https://thecrit.co/resources/css-typography-best-practices - Display letter-spacing, fixed body size, clamp guidance
- Clamp Generator — fluid typescale - https://clampgenerator.com/tools/font-size-typescale/ - Common clamp() values and ratio calculator
- OddBird — Reimagining Fluid Typography - https://www.oddbird.net/2025/02/12/fluid-type/ - 2025 authority on fluid type caveats (zoom accessibility)

## seo
NOTE FIRST: hooks report session cost at $450.70 (COST CRITICAL) — surface this to the operator before more work.

(A) LIVE AUDIT — trymaven.in today (fetched 2026-07-20, raw HTML). Title: "Maven — How It Works". Meta description present ("Index-like returns at roughly half the drawdown… Risk management is the edge. Research tool, paper-traded, not advice."). lang="en", viewport, manifest, apple-web-app tags present. MISSING entirely: canonical link, ALL og:* tags, ALL twitter:* tags, JSON-LD, meta robots (defaults to indexable — fine), and /robots.txt and /sitemap.xml both return 404. Two H1s on the homepage (should be one). Net: the site is indexable but has zero brand-entity signals, no crawl map, no social cards, and a title that leads with generic "Maven".

LOCAL UNCOMMITTED LAYER (the "undefined" paths resolve to F:\trymaven\code\github-bharat-research-brain\maven-dashboard\app\{layout.tsx,robots.ts,sitemap.ts}). What it fixes: metadataBase + canonical "/", title template ("Maven — AI Research for Indian Markets | TryMaven" — good, front-loads the winnable brand terms), keyword-rich description with the not-advice disclaimer, full openGraph + twitter blocks, robots index/follow, Organization+WebSite JSON-LD with alternateName ["TryMaven","Maven India"] and sameAs (Twitter, Instagram) — exactly the brand-entity graph needed. robots.ts allows all, disallows /auth/, points to sitemap. sitemap.ts lists 9 routes with priorities. Gaps still open: (1) OG image is /app/broker-screen.png at 1320x2868 — a phone-portrait screenshot; Google/X/WhatsApp want ~1200x630; make a proper landscape OG image and switch twitter card to summary_large_image. (2) Sitemap lists auth-gated app surfaces (/portfolio, /trades, /broker, /backtest, /login) that likely render login walls — Google will index thin/duplicate pages or drop them; sitemap should carry only truly public pages. (3) lastModified: new Date() on every build is a false freshness signal — pin real dates. (4) Only root canonical; child pages need per-page metadata (title, description, canonical) via generateMetadata or static exports — currently they inherit the template only. (5) No WebSite SearchAction, no potentialAction; fine to skip. (6) Verify icon.svg referenced in JSON-LD actually exists. (7) Add Google site-verification meta once GSC is set up. This layer is uncommitted — per your deploy-safety rule, verify on localhost and get explicit approval before pushing.

(B) STRATEGY. Honest ceiling: "maven" is unwinnable — Apache Maven, Maven Clinic, maven.com own it with decade-old authority. Winnable: "trymaven", "try maven" (should rank #1 within weeks of indexing), "maven ai india", "maven indian stock research", and mid-tail like "ai research indian stocks", "nse research ai" (winnable in months with content). Prioritized checklist: 1) Deploy the SEO layer (after fixing OG image + sitemap pruning). 2) Google Search Console: verify domain property (DNS TXT), submit sitemap.xml, use URL Inspection → Request Indexing on / and each public page; also Bing Webmaster (free, feeds DuckDuckGo/ChatGPT). 3) Brand entity: keep the JSON-LD; make the X/Twitter and Instagram bios link back to trymaven.in; consistent name "Maven (TryMaven)" everywhere. 4) Content — the real ranking lever: an indexable /learn or /research section, education-only framing (never advice): "How drawdown protection works", "What FII/DII flows mean", "Reading NSE bhavcopy data", "Backtesting without survivorship bias", methodology/transparency pages ("How Maven's F+ model was validated"), glossary of Indian-market terms. Each page: unique title/description/canonical, Article JSON-LD, internal links. These target the mid-tail queries the homepage can't. 5) Backlinks/citations: Product Hunt launch (dofollow profile + traffic), GitHub org profile linking the domain, X profile link, Peerlist (strong for Indian startups), BetaList, Indie Hackers, Uneed, startup directories (Startup India, YourStory listings), India fintech communities (r/IndianStreetBets research threads, TradingQnA discourse — participate genuinely, no spam), HN Show HN. Even 10-15 real referring domains decisively wins all brand queries. 6) Core Web Vitals: the page ships ~15 JS chunks; audit with PageSpeed Insights, lazy-load below-fold sections, ensure LCP element (hero H1) isn't blocked by client JS, keep CLS at 0 (fonts already display:swap), prefer static/ISR rendering for public pages. CWV is a tiebreaker, not a lever — content + links matter far more. Expected timeline: brand queries #1 in 2-6 weeks post-GSC; mid-tail queries 3-6 months with content cadence.
References:
- Next.js SEO Guide 2026: Metadata, Schema & Performance - https://www.modernwebseo.com/en/blog/nextjs-seo-guide-2026 - Current App Router guidance: generateMetadata, file-based robots.ts/sitemap.ts, JSON-LD server components
- The Complete Next.js SEO Checklist (2026 Edition) - https://www.devkitmarket.com/blog/nextjs-seo-checklist-2026 - Checklist confirming per-page metadata, canonicals, and sitemap patterns used in the critique
- Next.js App Router SEO Best Practices for Production (2026) - https://www.javascriptdoctor.blog/2026/07/nextjs-app-router-seo-best-practices.html - July 2026 production guidance on Metadata API, ISR, and Core Web Vitals for App Router
- Live site audited - https://www.trymaven.in/ - Source of the recorded title/description/missing-tags findings; /robots.txt and /sitemap.xml both 404 as of 2026-07-20
