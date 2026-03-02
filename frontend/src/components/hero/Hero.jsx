import { Activity, Radio, Database, Cpu } from 'lucide-react';

export default function Hero() {
  return (
    <section className="relative overflow-hidden -mx-4 -mt-6 mb-8">
      {/* Background gradient layers */}
      <div className="absolute inset-0 bg-gradient-to-b from-gray-950 via-gray-900/80 to-gray-950" />
      <div className="absolute inset-0 bg-gradient-to-r from-brand-teal/5 via-transparent to-brand-orange/5" />

      {/* Animated grid pattern */}
      <div className="absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage: `linear-gradient(rgba(20,184,166,0.3) 1px, transparent 1px),
                            linear-gradient(90deg, rgba(20,184,166,0.3) 1px, transparent 1px)`,
          backgroundSize: '64px 64px',
        }}
      />

      {/* Radial glow behind title */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[400px] bg-brand-teal/5 rounded-full blur-3xl" />

      <div className="relative max-w-7xl mx-auto px-4 py-16 md:py-24">
        {/* Eyebrow */}
        <div className="animate-hero-1 flex items-center gap-2 mb-6">
          <div className="w-2 h-2 rounded-full bg-brand-teal animate-pulse" />
          <span className="text-[11px] font-medium tracking-[0.2em] uppercase text-brand-teal/80">
            Live Intelligence Feed
          </span>
        </div>

        {/* Headline */}
        <h1 className="animate-hero-2 text-4xl md:text-5xl lg:text-6xl font-bold text-white tracking-tight leading-[1.1] max-w-3xl">
          One operational picture.
          <br />
          <span className="text-brand-teal">33.7 million lives</span> depending on it.
        </h1>

        {/* Subtitle */}
        <p className="animate-hero-3 mt-6 text-base md:text-lg text-gray-400 max-w-2xl leading-relaxed">
          Conflict, displacement, food security, and news — synthesized into
          actionable intelligence for humanitarian field teams in Sudan.
        </p>

        {/* Accent line */}
        <div className="accent-line my-8 max-w-md animate-hero-4" />

        {/* Source pills */}
        <div className="animate-hero-5 flex flex-wrap gap-3">
          <SourcePill icon={Database} label="HDX HAPI" sub="IDP + Conflict + IPC" />
          <SourcePill icon={Radio} label="GDELT" sub="Real-time news" />
          <SourcePill icon={Activity} label="UNHCR" sub="Displacement" />
          <SourcePill icon={Cpu} label="Local AI" sub="Ollama synthesis" />
        </div>
      </div>

      {/* Bottom fade */}
      <div className="absolute bottom-0 left-0 right-0 h-24 bg-gradient-to-t from-gray-950 to-transparent" />
    </section>
  );
}

function SourcePill({ icon: Icon, label, sub }) {
  return (
    <div className="group flex items-center gap-2.5 px-3.5 py-2 rounded-lg
                    bg-white/[0.03] border border-white/[0.06]
                    hover:bg-white/[0.06] hover:border-brand-teal/20
                    transition-all duration-300">
      <Icon className="w-3.5 h-3.5 text-brand-teal/70 group-hover:text-brand-teal transition-colors" />
      <div>
        <div className="text-xs font-medium text-gray-300 leading-none">{label}</div>
        <div className="text-[10px] text-gray-600 mt-0.5">{sub}</div>
      </div>
    </div>
  );
}
