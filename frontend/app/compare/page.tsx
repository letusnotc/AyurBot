"use client";

import React, { useState } from "react";
import { Loader2, Search } from "lucide-react";

const API_URL = "http://127.0.0.1:8000/compare";

type TreatmentData = {
  description: string;
  key_medicines: string[];
  approach: string;
  price_range: string;
};

type CompareResult = {
  disease: string;
  query: string;
  treatments: {
    ayurveda: TreatmentData;
    homeopathy: TreatmentData;
    allopathy: TreatmentData;
  };
};

const SYSTEMS: {
  key: keyof CompareResult["treatments"];
  label: string;
  subtitle: string;
  accent: string;
  headerBg: string;
  headerText: string;
  cardBg: string;
  border: string;
  pillBg: string;
  pillText: string;
  image: string;
}[] = [
  {
    key: "ayurveda",
    label: "Ayurveda",
    subtitle: "Ancient Indian Wisdom",
    accent: "#2d5a27",
    headerBg: "#2d5a27",
    headerText: "#ffffff",
    cardBg: "#ffffff",
    border: "#a5d6a7",
    pillBg: "#e8f5e9",
    pillText: "#1b5e20",
    image: "/ayurveda_img.jpeg",
  },
  {
    key: "homeopathy",
    label: "Homeopathy",
    subtitle: "Like Cures Like",
    accent: "#1565c0",
    headerBg: "#1565c0",
    headerText: "#ffffff",
    cardBg: "#ffffff",
    border: "#90caf9",
    pillBg: "#e3f2fd",
    pillText: "#0d47a1",
    image: "/homoe_img.jpg",
  },
  {
    key: "allopathy",
    label: "Allopathy",
    subtitle: "Modern Medicine",
    accent: "#00695c",
    headerBg: "#00695c",
    headerText: "#ffffff",
    cardBg: "#ffffff",
    border: "#80cbc4",
    pillBg: "#e0f2f1",
    pillText: "#004d40",
    image: "/allo_img.png",
  },
];

const LOADING_STEPS = [
  "Identifying condition...",
  "Searching Ayurvedic treatments...",
  "Searching Homeopathic remedies...",
  "Searching Allopathic medicines...",
  "Synthesizing comparison...",
];

function MedicineImage({ src, alt, accent }: { src: string; alt: string; accent: string }) {
  const [failed, setFailed] = useState(false);

  if (!src || failed) {
    return (
      <div
        className="w-full h-40 rounded-xl flex items-center justify-center text-xs font-bold uppercase tracking-widest"
        style={{ background: `${accent}12`, color: accent, border: `1.5px dashed ${accent}40` }}
      >
        {alt}
      </div>
    );
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={src}
      alt={alt}
      onError={() => setFailed(true)}
      className="w-full h-40 object-cover rounded-xl"
      style={{ border: `1.5px solid ${accent}25` }}
    />
  );
}

function TreatmentCard({
  system,
  data,
}: {
  system: (typeof SYSTEMS)[number];
  data: TreatmentData;
}) {
  return (
    <div
      className="flex flex-col rounded-2xl overflow-hidden shadow-lg"
      style={{ background: system.cardBg, border: `1.5px solid ${system.border}` }}
    >
      {/* Coloured header */}
      <div className="px-6 py-5" style={{ background: system.headerBg }}>
        <p
          className="text-[10px] font-black uppercase tracking-[0.22em] mb-0.5"
          style={{ color: system.headerText, opacity: 0.7 }}
        >
          {system.subtitle}
        </p>
        <h2 className="text-2xl font-black" style={{ color: system.headerText }}>
          {system.label}
        </h2>
        <p
          className="text-xs mt-2 leading-snug font-medium"
          style={{ color: system.headerText, opacity: 0.85 }}
        >
          {data.approach}
        </p>
      </div>

      <div className="p-5 flex flex-col gap-4 flex-1">
        {/* Medicine image — static asset from /public */}
        <MedicineImage src={system.image} alt={system.label} accent={system.accent} />

        {/* Description */}
        <p className="text-sm leading-relaxed text-gray-600">{data.description}</p>

        {/* Key medicines */}
        {data.key_medicines && data.key_medicines.length > 0 && (
          <div>
            <p
              className="text-[10px] font-black uppercase tracking-[0.18em] mb-2"
              style={{ color: system.accent }}
            >
              Key Medicines / Remedies
            </p>
            <div className="flex flex-wrap gap-2">
              {data.key_medicines.map((med, i) => (
                <span
                  key={i}
                  className="text-xs font-semibold px-3 py-1 rounded-full"
                  style={{ background: system.pillBg, color: system.pillText }}
                >
                  {med}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Price */}
        <div
          className="mt-auto pt-4 border-t flex items-center justify-between"
          style={{ borderColor: system.border }}
        >
          <span className="text-[10px] font-black uppercase tracking-widest text-gray-400">
            Approx. Cost
          </span>
          <span className="text-sm font-black" style={{ color: system.accent }}>
            {data.price_range}
          </span>
        </div>
      </div>
    </div>
  );
}

export default function ComparePage() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState(0);
  const [result, setResult] = useState<CompareResult | null>(null);
  const [error, setError] = useState("");

  async function handleCompare() {
    if (!query.trim() || loading) return;
    setLoading(true);
    setResult(null);
    setError("");
    setLoadingStep(0);

    const interval = setInterval(() => {
      setLoadingStep((s) => (s + 1) % LOADING_STEPS.length);
    }, 2500);

    try {
      const res = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: query.trim() }),
      });
      if (!res.ok) {
        const t = await res.json().catch(() => ({ error: `HTTP ${res.status}` }));
        throw new Error(t.error || `HTTP ${res.status}`);
      }
      const data: CompareResult = await res.json();
      setResult(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      clearInterval(interval);
      setLoading(false);
    }
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") handleCompare();
  }

  return (
    <div className="min-h-screen w-full" style={{ background: "linear-gradient(135deg, #f5f0eb 0%, #ede4d8 50%, #e8dfd1 100%)" }}>
      <div className="max-w-5xl mx-auto px-6 py-10">

        {/* Page heading */}
        <div className="mb-8 text-center">
          <h1 className="text-4xl font-black tracking-tight text-[#3e2723]">
            Treatment Comparison
          </h1>
          <p className="text-sm text-[#5d4037] mt-2 font-bold uppercase tracking-[0.18em]">
            Ayurveda &nbsp;vs&nbsp; Homeopathy &nbsp;vs&nbsp; Allopathy
          </p>
        </div>

        {/* Search card */}
        <div className="bg-white rounded-2xl shadow-lg border border-[#e0d5c8] px-8 py-7 mb-8">
          <p className="text-xs font-black uppercase tracking-[0.2em] text-[#8d6e63] mb-3">
            Describe your condition
          </p>
          <div className="flex gap-3">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder="e.g. I have diabetes, joint pain, high blood pressure..."
              className="flex-1 rounded-xl px-5 py-3.5 bg-[#fdfaf7] border-2 border-[#e0d5c8] outline-none focus:ring-4 focus:ring-[#3e2723]/5 focus:border-[#3e2723]/40 transition-all text-sm font-semibold text-[#3e2723] placeholder:text-[#3e2723]/30"
              disabled={loading}
            />
            <button
              onClick={handleCompare}
              disabled={!query.trim() || loading}
              className="rounded-xl px-7 py-3.5 bg-[#3e2723] text-white flex items-center gap-2 disabled:opacity-30 hover:bg-[#2a1b18] active:scale-95 transition-all shadow-md font-bold text-sm"
            >
              <Search className="h-4 w-4" />
              COMPARE
            </button>
          </div>
        </div>

        {/* Loading */}
        {loading && (
          <div className="bg-white rounded-2xl shadow-lg border border-[#e0d5c8] px-8 py-10 flex flex-col items-center gap-4">
            <Loader2 className="h-8 w-8 animate-spin text-[#2d5a27]" />
            <p className="text-sm font-bold text-[#3e2723]">{LOADING_STEPS[loadingStep]}</p>
            <p className="text-xs text-[#3e2723]/40 font-semibold uppercase tracking-widest">
              Searching the web across all three systems...
            </p>
          </div>
        )}

        {/* Error */}
        {error && !loading && (
          <div className="bg-red-50 rounded-2xl border border-red-200 px-8 py-5 text-sm text-red-700 font-semibold">
            {error}
          </div>
        )}

        {/* Results */}
        {result && !loading && (
          <div>
            {/* Disease badge */}
            <div className="flex items-center justify-center mb-6">
              <div className="bg-white rounded-full px-6 py-2.5 border border-[#e0d5c8] shadow-md">
                <span className="text-xs font-black uppercase tracking-[0.15em] text-[#8d6e63]">
                  Condition:{" "}
                </span>
                <span className="text-sm font-black text-[#3e2723]">{result.disease}</span>
              </div>
            </div>

            {/* 3-column grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              {SYSTEMS.map((sys) => {
                const data = result.treatments[sys.key];
                if (!data) return null;
                return <TreatmentCard key={sys.key} system={sys} data={data} />;
              })}
            </div>

            {/* Disclaimer */}
            <p className="text-center text-[10px] text-[#5d4037]/50 mt-8 font-semibold uppercase tracking-widest">
              For informational purposes only. Always consult a qualified healthcare provider.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
