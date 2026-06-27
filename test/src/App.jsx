import React, { useState, useEffect, useRef } from "react";
import { motion, useScroll, useTransform, AnimatePresence } from "framer-motion";
import { 
  Link2, Check, Copy, ArrowRight, Shield, Clock, Smartphone, Zap, 
  BarChart3, QrCode, Sparkles, MapPin, RefreshCw, SmartphoneIcon, 
  Laptop, Compass, Globe, Lock, AlertTriangle, Play, ChevronRight,
  TrendingUp, Users, Terminal, Database
} from "lucide-react";

export default function App() {
  // Mouse tilt position for Hero Dashboard
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  const heroRef = useRef(null);

  useEffect(() => {
    const handleMouseMove = (e) => {
      if (!heroRef.current) return;
      const rect = heroRef.current.getBoundingClientRect();
      const x = (e.clientX - rect.left) / rect.width - 0.5; // -0.5 to 0.5
      const y = (e.clientY - rect.top) / rect.height - 0.5;
      setMousePosition({ x, y });
    };

    const currentHero = heroRef.current;
    if (currentHero) {
      currentHero.addEventListener("mousemove", handleMouseMove);
    }
    return () => {
      if (currentHero) {
        currentHero.removeEventListener("mousemove", handleMouseMove);
      }
    };
  }, []);

  // Scroll Tracking for Parallax
  const { scrollY } = useScroll();
  
  // Parallax transforms
  const bgY = useTransform(scrollY, [0, 1000], [0, 80]);
  const dashY = useTransform(scrollY, [0, 1000], [0, 180]);
  const cardsY = useTransform(scrollY, [0, 1000], [0, 280]);
  const particlesY = useTransform(scrollY, [0, 1000], [0, 450]);

  // Demo 1: Interactive Shortener State with Premium Config
  const [longUrl, setLongUrl] = useState("");
  const [shortenStep, setShortenStep] = useState("idle"); // idle, analyzing, security, generating, done
  const [generatedShort, setGeneratedShort] = useState("");
  const [copied, setCopied] = useState(false);
  const [premiumOptions, setPremiumOptions] = useState({
    schedule: false,
    device: false,
    webhook: false,
    passcode: false
  });

  const togglePremiumOption = (key) => {
    setPremiumOptions(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const handleShorten = async (e) => {
    e.preventDefault();
    if (!longUrl) return;

    setShortenStep("analyzing");
    await new Promise(r => setTimeout(r, 1200));
    setShortenStep("security");
    await new Promise(r => setTimeout(r, 1000));
    setShortenStep("generating");
    await new Promise(r => setTimeout(r, 800));
    
    const randomCode = Math.random().toString(36).substring(2, 7);
    setGeneratedShort(`https://flex.url/${randomCode}`);
    setShortenStep("done");
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(generatedShort);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Demo 2: Clicks Counter and Chart Animation
  const [clickCount, setClickCount] = useState(1482);
  const [analyticsData, setAnalyticsData] = useState([
    { country: "United States", clicks: 642, percentage: "43%" },
    { country: "United Kingdom", clicks: 311, percentage: "21%" },
    { country: "Germany", clicks: 184, percentage: "12%" },
    { country: "Japan", clicks: 112, percentage: "8%" },
  ]);

  useEffect(() => {
    const interval = setInterval(() => {
      setClickCount(prev => prev + Math.floor(Math.random() * 3) + 1);
      setAnalyticsData(prev => 
        prev.map((item, index) => {
          if (index === 0) {
            return { ...item, clicks: item.clicks + 1 };
          }
          return item;
        })
      );
    }, 4000);
    return () => clearInterval(interval);
  }, []);

  // Demo 3: Interactive Smart Routing State
  const [activeDevice, setActiveDevice] = useState("desktop"); // desktop, ios, android
  const routingTargets = {
    desktop: "https://flexurl.in/product-landing",
    ios: "https://apps.apple.com/app/flexurl",
    android: "https://play.google.com/store/apps/flexurl"
  };

  // FAQ Accordion State
  const [openFaq, setOpenFaq] = useState(null);

  return (
    <div className="min-h-screen bg-[#fafaf8] text-[#0a0a0a] overflow-x-hidden selection:bg-primary/20 selection:text-primary">
      {/* Background elements */}
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
        {/* Soft floating gradient blobs */}
        <motion.div 
          style={{ y: bgY }}
          className="absolute -top-40 -right-40 w-[600px] h-[600px] rounded-full bg-indigo-100/40 blur-[120px]"
        />
        <motion.div 
          style={{ y: bgY }}
          className="absolute top-[40%] -left-40 w-[500px] h-[500px] rounded-full bg-slate-100/30 blur-[100px]"
        />
        {/* Dot grid background texture */}
        <div 
          className="absolute inset-0 opacity-[0.3]" 
          style={{
            backgroundImage: "radial-gradient(#6b6b63 1px, transparent 1px)",
            backgroundSize: "24px 24px"
          }}
        />
      </div>

      {/* Header Navigation */}
      <header className="sticky top-0 z-50 bg-white/70 backdrop-blur-xl border-b border-[#e7e6dd]">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <a href="#" className="flex items-center gap-2.5 group">
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-primary text-white shadow-lg shadow-indigo-500/20 group-hover:scale-105 transition-transform duration-300">
              <Link2 className="h-5 w-5" />
            </span>
            <span className="font-sans text-xl font-extrabold tracking-tight text-slate-900">
              FlexURL
            </span>
          </a>

          <nav className="hidden md:flex items-center gap-8">
            <a href="#features" className="text-sm font-medium text-slate-600 hover:text-primary transition-colors">Features</a>
            <a href="#demo" className="text-sm font-medium text-slate-600 hover:text-primary transition-colors">Interactive Demo</a>
            <a href="#analytics" className="text-sm font-medium text-slate-600 hover:text-primary transition-colors">Analytics</a>
            <a href="#pricing" className="text-sm font-medium text-slate-600 hover:text-primary transition-colors">Pricing</a>
          </nav>

          <div className="flex items-center gap-4">
            <a 
              href="#" 
              className="px-5 py-2 rounded-full bg-slate-900 text-white font-semibold text-sm hover:scale-102 hover:bg-primary hover:text-white transition-all duration-300"
            >
              Get Started
            </a>
          </div>
        </div>
      </header>

      {/* Main Content wrapper */}
      <main className="relative z-10">
        
        {/* HERO SECTION */}
        <section ref={heroRef} className="max-w-7xl mx-auto px-6 pt-16 lg:pt-24 pb-20 relative overflow-hidden">
          {/* Animated floating particles inside Hero */}
          <motion.div 
            style={{ y: particlesY }}
            className="absolute top-20 left-10 w-2.5 h-2.5 rounded-full bg-primary/20 blur-xs"
            animate={{ y: [-15, 15, -15] }}
            transition={{ duration: 7, repeat: Infinity, ease: "easeInOut" }}
          />
          <motion.div 
            style={{ y: particlesY }}
            className="absolute bottom-20 right-1/2 w-2 h-2 rounded-full bg-slate-300/40 blur-xs"
            animate={{ y: [10, -10, 10] }}
            transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
          />

          <div className="grid grid-cols-1 lg:grid-cols-[1.1fr_0.9fr] gap-12 lg:gap-16 items-start">
            
            {/* Hero Left Content */}
            <div className="text-left space-y-8">
              {/* Feature Badges */}
              <div className="flex flex-wrap gap-2.5">
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-primary/20 bg-primary/5 text-[11px] font-bold text-primary uppercase tracking-wider">
                  <TrendingUp className="h-3 w-3" />
                  Real-time Analytics
                </span>
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-[#e7e6dd] bg-white/50 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  <Shield className="h-3 w-3" />
                  SSRF Protected
                </span>
              </div>

              {/* Reveal Headline */}
              <h1 className="font-sans text-4.5xl sm:text-5.5xl lg:text-6xl font-extrabold tracking-tight leading-[0.98] text-slate-900">
                You shorten<br />
                like a pro.<br />
                You analyze like an <span className="text-primary lime-underline">engine.</span>
              </h1>

              {/* Description */}
              <p className="text-base sm:text-lg text-slate-600 leading-relaxed max-w-xl">
                Advanced redirect tracking and metadata analytics for brand managers. Monitor click statistics, client OS targeting routing, and webhook payload alerts.
              </p>

              {/* Shorten Input UI Inside left hero column (WITH Fake Premium Checkboxes) */}
              <div className="w-full max-w-[34rem] bg-white border border-slate-200 rounded-3xl p-6 shadow-md space-y-4">
                <form onSubmit={handleShorten} className="space-y-4">
                  <div className="flex flex-col gap-1.5">
                    <label className="text-[10px] font-bold text-slate-450 uppercase tracking-wider">Destination URL</label>
                    <input 
                      type="url" 
                      required
                      value={longUrl}
                      onChange={(e) => setLongUrl(e.target.value)}
                      placeholder="https://example.com/target-redirect-campaign" 
                      className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-[#fafaf8] text-slate-950 outline-none focus:border-primary transition-colors text-sm font-sans"
                    />
                  </div>

                  {/* Fake Premium Option Boxes */}
                  <div className="space-y-2.5 pt-3 border-t border-slate-100">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">Premium Routing Policy Configuration</span>
                    
                    {/* 1. Scheduled Activation */}
                    <div className="flex items-start gap-3 p-3 rounded-xl border border-slate-100 hover:border-primary/20 transition-all duration-200 bg-slate-50/50">
                      <input 
                        type="checkbox" 
                        id="opt-schedule"
                        checked={premiumOptions.schedule} 
                        onChange={() => togglePremiumOption("schedule")}
                        className="mt-0.5 h-4 w-4 rounded border-slate-300 text-primary focus:ring-primary cursor-pointer" 
                      />
                      <label htmlFor="opt-schedule" className="flex-1 cursor-pointer select-none">
                        <div className="text-xs font-bold flex justify-between items-center text-slate-800">
                          <span>Scheduled Activation Timer</span>
                          <span className="text-[9px] bg-primary/10 text-primary px-1.5 py-0.5 rounded font-black uppercase">PRO</span>
                        </div>
                        <p className="text-[10px] text-slate-500 leading-tight">Activate URL redirection at specified epoch. Serves live visitor countdown prior.</p>
                        {premiumOptions.schedule && (
                          <div className="mt-2.5 grid grid-cols-1 sm:grid-cols-2 gap-2">
                            <input type="datetime-local" className="px-2.5 py-1.5 rounded-lg border border-slate-200 text-[11px] outline-none focus:border-primary bg-white" onClick={(e) => e.stopPropagation()} />
                            <input type="url" placeholder="Countdown URL" className="px-2.5 py-1.5 rounded-lg border border-slate-200 text-[11px] outline-none focus:border-primary bg-white" onClick={(e) => e.stopPropagation()} />
                          </div>
                        )}
                      </label>
                    </div>

                    {/* 2. Device Routing */}
                    <div className="flex items-start gap-3 p-3 rounded-xl border border-slate-100 hover:border-primary/20 transition-all duration-200 bg-slate-50/50">
                      <input 
                        type="checkbox" 
                        id="opt-device"
                        checked={premiumOptions.device} 
                        onChange={() => togglePremiumOption("device")}
                        className="mt-0.5 h-4 w-4 rounded border-slate-300 text-primary focus:ring-primary cursor-pointer" 
                      />
                      <label htmlFor="opt-device" className="flex-1 cursor-pointer select-none">
                        <div className="text-xs font-bold flex justify-between items-center text-slate-800">
                          <span>OS-Aware Redirect Routing</span>
                          <span className="text-[9px] bg-primary/10 text-primary px-1.5 py-0.5 rounded font-black uppercase">PRO</span>
                        </div>
                        <p className="text-[10px] text-slate-500 leading-tight">Direct mobile devices directly to iOS App Store / Google Play and desktop to fallback.</p>
                        {premiumOptions.device && (
                          <div className="mt-2.5 grid grid-cols-1 sm:grid-cols-2 gap-2">
                            <input type="url" placeholder="iOS App URL" className="px-2.5 py-1.5 rounded-lg border border-slate-200 text-[11px] outline-none focus:border-primary bg-white" onClick={(e) => e.stopPropagation()} />
                            <input type="url" placeholder="Android App URL" className="px-2.5 py-1.5 rounded-lg border border-slate-200 text-[11px] outline-none focus:border-primary bg-white" onClick={(e) => e.stopPropagation()} />
                          </div>
                        )}
                      </label>
                    </div>

                    {/* 3. Webhooks */}
                    <div className="flex items-start gap-3 p-3 rounded-xl border border-slate-100 hover:border-primary/20 transition-all duration-200 bg-slate-50/50">
                      <input 
                        type="checkbox" 
                        id="opt-webhook"
                        checked={premiumOptions.webhook} 
                        onChange={() => togglePremiumOption("webhook")}
                        className="mt-0.5 h-4 w-4 rounded border-slate-300 text-primary focus:ring-primary cursor-pointer" 
                      />
                      <label htmlFor="opt-webhook" className="flex-1 cursor-pointer select-none">
                        <div className="text-xs font-bold flex justify-between items-center text-slate-800">
                          <span>Real-time Webhook Callbacks</span>
                          <span className="text-[9px] bg-primary/10 text-primary px-1.5 py-0.5 rounded font-black uppercase">PRO</span>
                        </div>
                        <p className="text-[10px] text-slate-500 leading-tight">Transmit redirect client metadata payload to external HTTP endpoints instantly.</p>
                        {premiumOptions.webhook && (
                          <div className="mt-2.5">
                            <input type="url" placeholder="https://api.yourdomain.com/webhook" className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 text-[11px] outline-none focus:border-primary bg-white" onClick={(e) => e.stopPropagation()} />
                          </div>
                        )}
                      </label>
                    </div>

                    {/* 4. Passcode */}
                    <div className="flex items-start gap-3 p-3 rounded-xl border border-slate-100 hover:border-primary/20 transition-all duration-200 bg-slate-50/50">
                      <input 
                        type="checkbox" 
                        id="opt-passcode"
                        checked={premiumOptions.passcode} 
                        onChange={() => togglePremiumOption("passcode")}
                        className="mt-0.5 h-4 w-4 rounded border-slate-300 text-primary focus:ring-primary cursor-pointer" 
                      />
                      <label htmlFor="opt-passcode" className="flex-1 cursor-pointer select-none">
                        <div className="text-xs font-bold flex justify-between items-center text-slate-800">
                          <span>Passcode Verification Gate</span>
                          <span className="text-[9px] bg-primary/10 text-primary px-1.5 py-0.5 rounded font-black uppercase">PRO</span>
                        </div>
                        <p className="text-[10px] text-slate-500 leading-tight">Intercept visitor with password validation screen before redirecting.</p>
                        {premiumOptions.passcode && (
                          <div className="mt-2.5">
                            <input type="password" placeholder="Gate Passcode Value" className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 text-[11px] outline-none focus:border-primary bg-white" onClick={(e) => e.stopPropagation()} />
                          </div>
                        )}
                      </label>
                    </div>
                  </div>

                  <button type="submit" className="btn-submit w-full mt-4 flex items-center justify-center gap-2">
                    {shortenStep !== "idle" && shortenStep !== "done" ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Zap className="h-4.5 w-4.5" />}
                    {shortenStep === "idle" && "Shorten Link"}
                    {shortenStep === "analyzing" && "Metadata Analysis..."}
                    {shortenStep === "security" && "Resolving Host Security..."}
                    {shortenStep === "generating" && "Scaffolding DB Index..."}
                    {shortenStep === "done" && "Complete"}
                  </button>
                </form>

                {/* Done Panel */}
                <AnimatePresence>
                  {shortenStep === "done" && (
                    <motion.div 
                      initial={{ opacity: 0, y: 15 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: 15 }}
                      className="p-4 rounded-xl border border-emerald-100 bg-emerald-50/50 flex flex-col sm:flex-row items-center justify-between gap-4"
                    >
                      <div className="flex items-center gap-3 text-left">
                        <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-500">
                          <Check className="h-5 w-5" />
                        </div>
                        <div>
                          <div className="text-[10px] font-bold text-emerald-600 uppercase tracking-wide">Active Smart Redirect Schema</div>
                          <div className="text-sm font-mono font-bold text-slate-900">{generatedShort}</div>
                        </div>
                      </div>

                      <button 
                        type="button"
                        onClick={handleCopy}
                        className="px-5 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold flex items-center gap-1.5 transition-colors self-stretch sm:self-auto justify-center"
                      >
                        {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                        {copied ? "Copied!" : "Copy URL"}
                      </button>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </div>

            {/* Hero Right Visuals (Tilt Dashboard Mockup focused on Analytics) */}
            <div className="hero-visual flex justify-center items-center">
              <motion.div 
                style={{
                  rotateX: mousePosition.y * -8,
                  rotateY: mousePosition.x * 12,
                  transformStyle: "preserve-3d",
                  y: dashY
                }}
                className="relative w-full max-w-[420px] aspect-square rounded-[32px] border border-slate-200/80 bg-white/45 p-6 shadow-xl"
              >
                <div className="glow-breathe absolute inset-0 z-0 bg-gradient-to-tr from-primary/10 to-transparent blur-[30px]" />
                
                {/* Floating Card 1: Clicks Live Metrics */}
                <motion.div 
                  style={{ y: useTransform(scrollY, [0, 1000], [0, -40]) }}
                  animate={{ y: [-6, 6, -6] }}
                  transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}
                  className="absolute top-4 left-4 z-10 w-[190px] p-4 rounded-2xl border border-slate-200 bg-white shadow-md"
                >
                  <div className="flex justify-between items-start mb-2">
                    <span className="text-[10px] font-bold text-slate-450 uppercase tracking-wide">Live Clicks</span>
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                  </div>
                  <div className="text-2xl font-black tracking-tight tabular-nums">
                    {clickCount}
                  </div>
                  {/* Mock sparkline graph */}
                  <svg className="w-full h-8 mt-2 text-primary" viewBox="0 0 100 30" fill="none">
                    <path d="M0,25 Q15,10 30,22 T60,5 T90,15 L100,10" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
                  </svg>
                </motion.div>

                {/* Floating Card 2: iOS Targeting */}
                <motion.div 
                  style={{ y: useTransform(scrollY, [0, 1000], [0, 50]) }}
                  animate={{ y: [6, -6, 6] }}
                  transition={{ duration: 7, repeat: Infinity, ease: "easeInOut", delay: 1 }}
                  className="absolute bottom-6 left-6 z-10 w-[160px] p-4 rounded-2xl border border-slate-200 bg-white shadow-md flex items-center gap-3"
                >
                  <div className="p-2 rounded-lg bg-indigo-500/10 text-primary">
                    <Smartphone className="h-5 w-5" />
                  </div>
                  <div className="text-left">
                    <div className="text-[10px] font-bold text-slate-450 uppercase">Routing</div>
                    <div className="text-xs font-bold text-slate-800">iOS Redirect</div>
                  </div>
                </motion.div>

                {/* Floating Card 3: QR Code card */}
                <motion.div 
                  style={{ y: useTransform(scrollY, [0, 1000], [0, -80]) }}
                  animate={{ y: [-8, 8, -8] }}
                  transition={{ duration: 8, repeat: Infinity, ease: "easeInOut", delay: 0.5 }}
                  className="absolute top-12 right-4 z-10 w-[130px] p-4 rounded-2xl border border-slate-200 bg-white shadow-md text-center"
                >
                  <div className="mx-auto w-16 h-16 bg-slate-100 rounded-lg p-2.5 flex items-center justify-center border border-[#e7e6dd]">
                    <QrCode className="w-full h-full text-slate-700" />
                  </div>
                  <span className="text-[10px] font-bold text-primary uppercase mt-2 block tracking-wider">QR Code</span>
                </motion.div>

                {/* Floating Card 4: Location Analytics */}
                <motion.div 
                  style={{ y: useTransform(scrollY, [0, 1000], [0, 80]) }}
                  animate={{ y: [8, -8, 8] }}
                  transition={{ duration: 9, repeat: Infinity, ease: "easeInOut", delay: 1.5 }}
                  className="absolute bottom-16 right-4 z-10 w-[200px] p-4 rounded-2xl border border-indigo-100 bg-indigo-50/80 shadow-md"
                >
                  <div className="flex items-center gap-1.5 mb-1 text-primary">
                    <Globe className="h-4 w-4" />
                    <span className="text-[10px] font-bold uppercase tracking-wider">Location parser</span>
                  </div>
                  <div className="text-[11px] leading-normal font-mono text-slate-700 space-y-1">
                    <div>IP: 192.0.2.1 (US)</div>
                    <div className="text-emerald-500">{"HTTP 302 \u2192 Forwarded"}</div>
                  </div>
                </motion.div>

                {/* Dotted orbits around center */}
                <div className="absolute inset-8 rounded-full border border-dashed border-primary/20 orbit-dash z-0" />
                <div className="absolute inset-16 rounded-full border border-dashed border-primary/10 z-0" />

                {/* Center Node representing Short Code */}
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-0 p-4 rounded-2xl bg-primary text-white font-mono font-bold text-sm shadow-xl shadow-indigo-500/30">
                  flex.url/v2
                </div>
              </motion.div>
            </div>
          </div>
        </section>

        {/* SCROLL STORYTELLING: PROBLEM VS SOLUTION */}
        <section id="features" className="py-24 bg-white border-t border-b border-[#e7e6dd] transition-colors duration-500">
          <div className="max-w-6xl mx-auto px-6">
            <div className="text-center max-w-2xl mx-auto mb-16">
              <span className="badge">
                <span className="badge-dot" />
                The Problem / The Solution
              </span>
              <h2 className="section-title text-slate-900 mt-4">
                Redefining the redirection logic.
              </h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-stretch">
              
              {/* Problem Card */}
              <div className="p-8 rounded-[28px] border border-[#e3e2da] bg-[#f2f1ec] text-left flex flex-col justify-between">
                <div className="space-y-6">
                  <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-rose-500/10 text-rose-500 text-xs font-bold uppercase tracking-wider">
                    ✕ Generic Redirects
                  </div>
                  
                  {/* Bad visual */}
                  <div className="rounded-2xl bg-black/5 border border-slate-205 p-6 flex flex-col items-center justify-center aspect-video relative overflow-hidden">
                    <div className="text-center space-y-2">
                      <div className="h-10 w-10 rounded-full bg-rose-500/10 text-rose-500 inline-grid place-items-center mb-1">
                        <AlertTriangle className="h-5 w-5" />
                      </div>
                      <div className="text-xs font-mono text-slate-400">link.generic-shortener.com/expired</div>
                      <div className="text-xs font-bold text-rose-500 uppercase tracking-wide">HTTP 404 NOT FOUND</div>
                    </div>
                  </div>

                  <p className="text-sm leading-relaxed text-slate-655">
                    Traditional link shorteners are blind endpoints. When marketing campaigns expire or target domains get flagged, users are dropped directly onto generic 404 error screens.
                  </p>
                </div>

                <div className="pt-6 border-t border-slate-200 text-xs italic text-slate-500">
                  Frustrating mobile users. Vulnerable to domain blacklist actions.
                </div>
              </div>

              {/* Solution Card */}
              <div className="p-8 rounded-[28px] border-2 border-primary bg-white text-left flex flex-col justify-between relative shadow-xl shadow-indigo-500/5">
                <span className="absolute top-0 right-8 -translate-y-1/2 px-3 py-1 rounded-full bg-primary text-white text-[10px] font-bold tracking-widest uppercase">
                  Highly Intelligent
                </span>
                
                <div className="space-y-6">
                  <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 text-primary text-xs font-bold uppercase tracking-wider">
                    ✓ FlexURL Redirects
                  </div>

                  {/* Nice active visual */}
                  <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6 flex flex-col items-center justify-center aspect-video relative overflow-hidden">
                    <div className="absolute inset-0 bg-radial-gradient from-primary/10 via-transparent to-transparent blur-[20px]" />
                    <div className="text-center space-y-2 z-10">
                      <div className="h-10 w-10 rounded-full bg-emerald-500/10 text-emerald-500 inline-grid place-items-center mb-1 animate-pulse">
                        <Clock className="h-5 w-5" />
                      </div>
                      <div className="text-xs font-mono text-zinc-400">link.zerodaily.in/promo-launch</div>
                      <div className="text-xs font-bold text-indigo-400 uppercase tracking-wide">Activating in: 04m 12s</div>
                    </div>
                  </div>

                  <p className="text-sm leading-relaxed text-slate-700">
                    FlexURL adds intelligent gates. If a link isn't active yet, visitors see beautiful live count panels. If expired, we route them to fallback pages. Webhooks trigger on request.
                  </p>
                </div>

                <div className="pt-6 border-t border-slate-200 text-xs italic text-primary font-semibold">
                  Intelligent routing logic. Guaranteed 60ms redirection response times.
                </div>
              </div>

            </div>
          </div>
        </section>

        {/* PRO DEMO 2: LIVE ANALYTICS & GLOBAL WORLD MAP */}
        <section id="analytics" className="py-24 bg-white transition-colors duration-500">
          <div className="max-w-6xl mx-auto px-6">
            <div className="grid grid-cols-1 lg:grid-cols-[1.1fr_0.9fr] gap-12 lg:gap-16 items-center">
              
              {/* Analytics Left: Info */}
              <div className="text-left space-y-6">
                <span className="badge">
                  <span className="badge-dot" />
                  Link Analytics Hub
                </span>
                <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-slate-900 leading-[1.05]">
                  Get real-time insights,<br />second by second.
                </h2>
                <p className="text-sm leading-relaxed text-slate-655 max-w-lg">
                  FlexURL parses visitor headers, resolves user countries via internal DB lookup caches, and records click log metrics. Beautiful sparklines and country analytics update in real-time.
                </p>

                <div className="grid grid-cols-2 gap-6 pt-4">
                  <div className="p-4 rounded-2xl border border-slate-100 bg-[#fafaf8]">
                    <div className="text-2xl font-black text-primary tabular-nums">{clickCount}</div>
                    <div className="text-[10px] font-bold text-slate-450 uppercase tracking-wider mt-1">Total click logs</div>
                  </div>
                  <div className="p-4 rounded-2xl border border-slate-100 bg-[#fafaf8]">
                    <div className="text-2xl font-black text-emerald-500">99.99%</div>
                    <div className="text-[10px] font-bold text-slate-450 uppercase tracking-wider mt-1">Uptime SLA Guarantee</div>
                  </div>
                </div>
              </div>

              {/* Analytics Right: Interactive Visual Card */}
              <div className="flex justify-center">
                <div className="w-full max-w-[400px] p-6 rounded-3xl border border-slate-200 bg-white shadow-xl text-left">
                  <div className="flex justify-between items-center mb-6">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-slate-450">Live Traffic Logs</span>
                    <span className="px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-500 text-[10px] font-bold">LIVE</span>
                  </div>

                  {/* List of Countries Clicks */}
                  <div className="space-y-4">
                    {analyticsData.map((item, index) => (
                      <div key={item.country} className="space-y-1.5">
                        <div className="flex justify-between text-xs font-bold">
                          <span className="flex items-center gap-2">
                            <span className="h-1.5 w-1.5 rounded-full bg-primary" />
                            {item.country}
                          </span>
                          <span className="tabular-nums text-slate-500">{item.clicks} clicks</span>
                        </div>
                        {/* Mock progress bar */}
                        <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
                          <motion.div 
                            className="h-full bg-primary"
                            initial={{ width: 0 }}
                            animate={{ width: item.percentage }}
                            transition={{ duration: 1.5, ease: "easeOut" }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Simulated click arrival stream */}
                  <div className="mt-8 pt-6 border-t border-slate-100 flex justify-between items-center text-xs">
                    <span className="text-slate-455 flex items-center gap-1.5">
                      <Globe className="h-4 w-4 animate-spin text-primary" />
                      Awaiting new redirects...
                    </span>
                    <span className="text-[10px] font-mono text-emerald-500 font-bold uppercase">60ms latency</span>
                  </div>
                </div>
              </div>

            </div>
          </div>
        </section>

        {/* DYNAMIC OS-TARGET ROUTING FLOW */}
        <section className="py-24 bg-slate-50 transition-colors duration-500">
          <div className="max-w-4xl mx-auto px-6 text-center">
            <div className="max-w-xl mx-auto mb-16">
              <span className="badge">
                <span className="badge-dot" />
                Dynamic OS-Target Routing
              </span>
              <h2 className="section-title text-slate-900 mt-4">
                Smart redirection logic.
              </h2>
            </div>

            <div className="p-8 rounded-[32px] border border-slate-200/80 bg-white shadow-xl text-left">
              <div className="flex flex-col md:flex-row gap-8 items-stretch">
                
                {/* Router console left controls */}
                <div className="w-full md:w-[220px] flex flex-col gap-3 justify-center">
                  <div className="text-[10px] font-bold text-slate-450 uppercase tracking-wider mb-1">Select visitor client device</div>
                  
                  <button 
                    onClick={() => setActiveDevice("desktop")}
                    className={`px-4 py-3 rounded-xl border text-xs font-bold text-left flex items-center justify-between transition-all duration-300 ${
                      activeDevice === "desktop" ? "border-primary bg-primary/5 text-primary scale-102" : "border-slate-205 bg-white/50 text-slate-700"
                    }`}
                  >
                    <span className="flex items-center gap-2"><Laptop className="h-4.5 w-4.5" /> Desktop PC</span>
                    {activeDevice === "desktop" && <Check className="h-4.5 w-4.5" />}
                  </button>

                  <button 
                    onClick={() => setActiveDevice("ios")}
                    className={`px-4 py-3 rounded-xl border text-xs font-bold text-left flex items-center justify-between transition-all duration-300 ${
                      activeDevice === "ios" ? "border-primary bg-primary/5 text-primary scale-102" : "border-slate-205 bg-white/50 text-slate-700"
                    }`}
                  >
                    <span className="flex items-center gap-2"><SmartphoneIcon className="h-4.5 w-4.5" /> iOS Visitor</span>
                    {activeDevice === "ios" && <Check className="h-4.5 w-4.5" />}
                  </button>

                  <button 
                    onClick={() => setActiveDevice("android")}
                    className={`px-4 py-3 rounded-xl border text-xs font-bold text-left flex items-center justify-between transition-all duration-300 ${
                      activeDevice === "android" ? "border-primary bg-primary/5 text-primary scale-102" : "border-slate-205 bg-white/50 text-slate-700"
                    }`}
                  >
                    <span className="flex items-center gap-2"><Smartphone className="h-4.5 w-4.5" /> Android Visitor</span>
                    {activeDevice === "android" && <Check className="h-4.5 w-4.5" />}
                  </button>
                </div>

                {/* Router right interactive graph flow chart */}
                <div className="flex-1 rounded-2xl bg-slate-900 border border-slate-800 p-8 flex flex-col justify-between aspect-video relative overflow-hidden">
                  <div className="absolute inset-0 bg-radial-gradient from-primary/10 via-transparent to-transparent opacity-50 blur-[20px]" />
                  
                  {/* Visual nodes */}
                  <div className="flex justify-between items-center relative z-10 my-auto h-full">
                    {/* Visitor Node */}
                    <div className="flex flex-col items-center gap-2 text-center">
                      <div className="h-12 w-12 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-white">
                        {activeDevice === "desktop" && <Laptop className="h-6 w-6 text-primary" />}
                        {activeDevice === "ios" && <SmartphoneIcon className="h-6 w-6 text-primary" />}
                        {activeDevice === "android" && <Smartphone className="h-6 w-6 text-primary" />}
                      </div>
                      <span className="text-[10px] font-bold text-zinc-500 uppercase">Visitor Click</span>
                    </div>

                    {/* Arrow flow */}
                    <div className="flex-1 flex flex-col items-center justify-center relative">
                      {/* Animating line path */}
                      <svg className="w-full h-10 text-zinc-800" fill="none" viewBox="0 0 100 10" preserveAspectRatio="none">
                        <line x1="0" y1="5" x2="100" y2="5" stroke="currentColor" strokeWidth="1.5" strokeDasharray="3 3" />
                        <motion.line 
                          x1="0" y1="5" x2="100" y2="5" 
                          stroke="#4f46e5" strokeWidth="2" 
                          initial={{ strokeDashoffset: 12 }}
                          animate={{ strokeDashoffset: [12, 0] }}
                          transition={{ repeat: Infinity, duration: 1.5, ease: "linear" }}
                          strokeDasharray="4 4"
                        />
                      </svg>
                    </div>

                    {/* Router Engine Node */}
                    <div className="flex flex-col items-center gap-2 text-center">
                      <div className="h-14 w-14 rounded-2xl bg-primary flex items-center justify-center text-white shadow-xl shadow-indigo-500/20">
                        <Compass className="h-7 w-7 text-white animate-spin" style={{ animationDuration: '6s' }} />
                      </div>
                      <span className="text-[10px] font-bold text-primary uppercase">FlexURL Router</span>
                    </div>

                    {/* Arrow flow */}
                    <div className="flex-1 flex flex-col items-center justify-center relative">
                      <svg className="w-full h-10 text-zinc-800" fill="none" viewBox="0 0 100 10" preserveAspectRatio="none">
                        <line x1="0" y1="5" x2="100" y2="5" stroke="currentColor" strokeWidth="1.5" strokeDasharray="3 3" />
                        <motion.line 
                          x1="0" y1="5" x2="100" y2="5" 
                          stroke="#4f46e5" strokeWidth="2" 
                          initial={{ strokeDashoffset: 12 }}
                          animate={{ strokeDashoffset: [12, 0] }}
                          transition={{ repeat: Infinity, duration: 1.5, ease: "linear" }}
                          strokeDasharray="4 4"
                        />
                      </svg>
                    </div>

                    {/* Target Node */}
                    <div className="flex flex-col items-center gap-2 text-center">
                      <div className="h-12 w-12 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-white">
                        <Zap className="h-6 w-6 text-emerald-400" />
                      </div>
                      <span className="text-[10px] font-bold text-zinc-500 uppercase">Redirect Destination</span>
                    </div>
                  </div>

                  {/* Redirection link status text */}
                  <div className="bg-slate-850 border border-slate-800 rounded-xl p-3 flex justify-between items-center text-xs font-mono">
                    <span className="text-slate-500">Destination:</span>
                    <span className="text-emerald-400 truncate max-w-[200px] sm:max-w-none">{routingTargets[activeDevice]}</span>
                  </div>
                </div>

              </div>
            </div>
          </div>
        </section>

        {/* PRICING SECTION */}
        <section id="pricing" className="py-24 bg-slate-50 border-t border-[#e7e6dd] transition-colors duration-500">
          <div className="max-w-6xl mx-auto px-6">
            <div className="text-center max-w-xl mx-auto mb-16">
              <span className="badge">
                <span className="badge-dot" />
                Pricing Plans
              </span>
              <h2 className="section-title text-slate-900 mt-4">
                Start free. Upgrade when it clicks.
              </h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 items-stretch max-w-5xl mx-auto">
              {/* Developer Free */}
              <div className="bg-white border border-slate-202 rounded-3xl p-8 flex flex-col justify-between shadow-sm text-left">
                <div>
                  <h3 className="text-lg font-bold text-slate-900 mb-2">Developer Free</h3>
                  <p className="text-xs text-slate-400 mb-6">Perfect for building and personal utility.</p>
                  <div className="text-4xl font-extrabold text-slate-900 mb-6">$0<span className="text-xs text-slate-400 font-normal"> /mo</span></div>
                  <ul className="space-y-3.5 mb-8">
                    <li className="flex items-center text-xs text-slate-650"><span className="text-primary mr-2">✓</span> 10 URLs per day limit</li>
                    <li class="flex items-center text-xs text-slate-650"><span className="text-primary mr-2">✓</span> 100 URLs per month limit</li>
                    <li className="flex items-center text-xs text-slate-650"><span className="text-primary mr-2">✓</span> URLs expire in 15 days</li>
                    <li className="flex items-center text-xs text-slate-650"><span className="text-primary mr-2">✓</span> SSRF & Safe Browsing protection</li>
                  </ul>
                </div>
                <a href="#demo" className="block text-center w-full py-3 rounded-xl border border-slate-200 bg-[#fafaf8] font-bold hover:border-slate-400 text-xs transition-colors">
                  Try Instant Shortening
                </a>
              </div>

              {/* Business Pro */}
              <div className="bg-white border-2 border-primary rounded-3xl p-8 flex flex-col justify-between shadow-lg text-left relative">
                <span className="absolute top-0 right-8 -translate-y-1/2 bg-primary text-white text-[10px] font-bold tracking-widest uppercase py-1 px-3.5 rounded-full">
                  Most Popular
                </span>
                <div>
                  <h3 class="text-lg font-bold text-slate-900 mb-2">Business Pro</h3>
                  <p className="text-xs text-slate-400 mb-6">For growing teams and brands.</p>
                  <div className="text-4xl font-extrabold text-slate-900 mb-6">$19<span class="text-xs text-slate-400 font-normal"> /mo</span></div>
                  <ul className="space-y-3.5 mb-8">
                    <li className="flex items-center text-xs text-slate-650"><span className="text-primary mr-2">✓</span> Unlimited short redirects</li>
                    <li className="flex items-center text-xs text-slate-650"><span className="text-primary mr-2">✓</span> 3 Custom Domain Names</li>
                    <li className="flex items-center text-xs text-slate-650"><span className="text-primary mr-2">✓</span> Extended location reports</li>
                    <li className="flex items-center text-xs text-slate-650"><span className="text-primary mr-2">✓</span> Full API Integration & SDKs</li>
                  </ul>
                </div>
                <a href="#" className="block text-center w-full py-3 rounded-xl bg-primary text-white font-bold hover:bg-primary-hover text-xs transition-colors shadow-md shadow-indigo-500/20">
                  Get Started
                </a>
              </div>

              {/* Enterprise Dedicated */}
              <div className="bg-white border border-slate-202 rounded-3xl p-8 flex flex-col justify-between shadow-sm text-left">
                <div>
                  <h3 className="text-lg font-bold text-slate-900 mb-2">Enterprise Dedicated</h3>
                  <p className="text-xs text-slate-400 mb-6">Dedicated deployment on customer tenants.</p>
                  <div className="text-4xl font-extrabold text-slate-900 mb-6">Custom</div>
                  <ul className="space-y-3.5 mb-8">
                    <li className="flex items-center text-xs text-slate-650"><span className="text-primary mr-2">✓</span> Single Tenant hosting (AWS/GCP)</li>
                    <li className="flex items-center text-xs text-slate-650"><span className="text-primary mr-2">✓</span> Custom branding & SSL termination</li>
                    <li className="flex items-center text-xs text-slate-650"><span className="text-primary mr-2">✓</span> 99.99% redirection uptime SLAs</li>
                    <li className="flex items-center text-xs text-slate-650"><span className="text-primary mr-2">✓</span> Custom DB logging adapter</li>
                  </ul>
                </div>
                <a href="#" className="block text-center w-full py-3 rounded-xl border border-slate-200 bg-[#fafaf8] font-bold hover:border-slate-400 text-xs transition-colors">
                  Contact Sales
                </a>
              </div>
            </div>
          </div>
        </section>

        {/* FAQ SECTION */}
        <section id="faq" className="py-24 bg-white transition-colors duration-500">
          <div className="max-w-3xl mx-auto px-6">
            <div className="text-center max-w-xl mx-auto mb-16">
              <span className="badge">
                <span className="badge-dot" />
                FAQ
              </span>
              <h2 className="section-title text-slate-900 mt-4">
                Questions, answered.
              </h2>
            </div>

            <div className="border border-slate-200 rounded-3xl bg-white p-6 space-y-1">
              {[
                {
                  q: "What is FlexURL?",
                  a: "FlexURL is a highly secure, fast URL shortener supporting dynamic target configurations like device routing, webhook updates, passcode verification, and launch-date scheduling."
                },
                {
                  q: "How does the Scheduled Activation work?",
                  a: "Until the scheduled launch date/time occurs, visitors will see a live countdown dashboard or are auto-routed to a custom URL you designate. Links activate instantly when the target epoch passes."
                },
                {
                  q: "What is SSRF protection?",
                  a: "Server-Side Request Forgery protection resolves custom redirect URLs to verify they don't map to internal, loopback, or private networking scopes (like localhost or RFC 1918 addresses), blocking link abuse vectors."
                }
              ].map((item, index) => (
                <div key={item.q} className="border-b border-slate-100 last:border-b-0">
                  <button 
                    onClick={() => setOpenFaq(openFaq === index ? null : index)}
                    className="flex w-full items-center justify-between gap-5 py-5 text-left font-semibold text-slate-900 hover:text-primary transition-colors text-sm"
                  >
                    <span>{item.q}</span>
                    <span className={`h-6 w-6 rounded-full border border-slate-200 grid place-items-center text-xs transition-transform duration-200 ${
                      openFaq === index ? "rotate-45 border-primary text-primary" : "text-slate-500"
                    }`}>
                      +
                    </span>
                  </button>
                  <AnimatePresence>
                    {openFaq === index && (
                      <motion.div 
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        className="overflow-hidden"
                      >
                        <p className="pb-5 text-xs leading-relaxed text-slate-550">
                          {item.a}
                        </p>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              ))}
            </div>
          </div>
        </section>

      </main>

      {/* Footer */}
      <footer className="border-t border-[#e7e6dd] bg-[#fafaf8] transition-colors duration-500">
        <div className="max-w-7xl mx-auto px-6 py-12 flex flex-col sm:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-2">
            <span className="grid h-7.5 w-7.5 place-items-center rounded-lg bg-primary text-white">
              <Link2 className="h-4 w-4" />
            </span>
            <span className="text-sm font-extrabold tracking-tight">FlexURL</span>
          </div>
          <div className="text-xs text-slate-400">
            &copy; 2026 FlexURL. All rights reserved.
          </div>
          <div className="flex gap-6 text-xs text-slate-400">
            <a href="#" className="hover:text-primary transition-colors">Privacy</a>
            <a href="#" className="hover:text-primary transition-colors">Terms</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
