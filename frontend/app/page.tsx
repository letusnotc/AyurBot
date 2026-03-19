// "use client";

// import React, { useEffect, useMemo, useRef, useState } from "react";
// import { ExternalLink, Loader2, Send } from "lucide-react";

// type Citation = {
//   rank: number;
//   score?: number;
//   sthana: string;
//   adhyaya_number: number;
//   adhyaya_name: string;
//   shloka_start: number;
//   shloka_end: number;
//   url: string;
// };

// type ChatMessage = {
//   id: string;
//   role: "user" | "assistant";
//   content: string;
//   citations?: Citation[];
// };

// const BG_URL = "/ayurbot.png"; // put in /public/ayurbot.png
// const API_URL = "http://127.0.0.1:8000/chat";

// function uid() {
//   return Math.random().toString(16).slice(2) + Date.now().toString(16);
// }

// function prettyCitation(c: Citation) {
//   return `${c.sthana} • Ch ${c.adhyaya_number} • ${c.adhyaya_name} • Shlokas ${c.shloka_start}-${c.shloka_end}`;
// }

// export default function AyurbotDemoPage() {
//   const [messages, setMessages] = useState<ChatMessage[]>(() => [
//     {
//       id: uid(),
//       role: "assistant",
//       content:
//         "Namaste. Ask me anything from Charaka Samhita — I will answer with citations.",
//     },
//   ]);

//   const [input, setInput] = useState("");
//   const [loading, setLoading] = useState(false);
//   const [topK, setTopK] = useState(5);

//   const scrollRef = useRef<HTMLDivElement | null>(null);

//   useEffect(() => {
//     scrollRef.current?.scrollIntoView({ behavior: "smooth" });
//   }, [messages, loading]);

//   const canSend = useMemo(
//     () => input.trim().length > 0 && !loading,
//     [input, loading]
//   );

//   async function send() {
//     if (!canSend) return;

//     const q = input.trim();
//     setInput("");

//     const userMsg: ChatMessage = {
//       id: uid(),
//       role: "user",
//       content: q,
//     };

//     setMessages((m) => [...m, userMsg]);
//     setLoading(true);

//     try {
//       const res = await fetch(API_URL, {
//         method: "POST",
//         headers: { "Content-Type": "application/json" },
//         body: JSON.stringify({ query: q, top_k: topK }),
//       });

//       if (!res.ok) {
//         const t = await res.text();
//         throw new Error(t || `HTTP ${res.status}`);
//       }

//       const data = await res.json();

//       const botMsg: ChatMessage = {
//         id: uid(),
//         role: "assistant",
//         content: data?.answer ?? "(No answer returned)",
//         citations: Array.isArray(data?.citations) ? data.citations : [],
//       };

//       setMessages((m) => [...m, botMsg]);
//     } catch (e: any) {
//       const botMsg: ChatMessage = {
//         id: uid(),
//         role: "assistant",
//         content:
//           "I couldn't reach the backend.\n\nMake sure FastAPI is running on http://127.0.0.1:8000 and CORS is enabled.\n\nError: " +
//           (e?.message ?? "Unknown"),
//       };
//       setMessages((m) => [...m, botMsg]);
//     } finally {
//       setLoading(false);
//     }
//   }

//   function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
//     if (e.key === "Enter") send();
//   }

//   return (
//     <div className="min-h-screen w-full">
//       {/* Background */}
//       <div
//         className="fixed inset-0 -z-10 bg-cover bg-center"
//         style={{ backgroundImage: `url(${BG_URL})` }}
//       />

//       {/* Layout */}
//       <div className="min-h-screen w-full relative">
//         <div className="max-w-[1100px]">
//           <div className="w-full md:w-[820px] lg:w-[900px]">
//             <div className="rounded-3xl shadow-2xl border border-black/10 bg-white/85 backdrop-blur-md">
//               {/* Header */}
//               <div className="px-6 pt-6 pb-4 flex items-start justify-between gap-4">
//                 <div>
//                   <h1 className="text-xl font-semibold">Ayurbot Chat</h1>
//                   <p className="text-sm text-black/60 mt-1">
//                     Charaka Samhita • RAG • citations included
//                   </p>
//                 </div>

//                 <div className="flex items-center gap-2">
//                   <span className="text-xs font-medium px-3 py-1 rounded-full bg-black/5 border border-black/10">
//                     TopK
//                   </span>
//                   <div className="flex items-center gap-1">
//                     {[3, 5, 7].map((k) => (
//                       <button
//                         key={k}
//                         onClick={() => setTopK(k)}
//                         className={
//                           topK === k
//                             ? "text-xs px-3 py-1 rounded-full bg-black text-white"
//                             : "text-xs px-3 py-1 rounded-full bg-white border border-black/15 hover:bg-black/5"
//                         }
//                       >
//                         {k}
//                       </button>
//                     ))}
//                   </div>
//                 </div>
//               </div>

//               {/* Chat box */}
//               <div className="px-6 pb-4">
//                 <div className="rounded-3xl border border-black/10 bg-white/60">
//                   <div className="h-[62vh] overflow-y-auto p-4 space-y-4">
//                     {messages.map((m) => (
//                       <div
//                         key={m.id}
//                         className={
//                           m.role === "user"
//                             ? "flex justify-end"
//                             : "flex justify-start"
//                         }
//                       >
//                         <div
//                           className={
//                             m.role === "user"
//                               ? "max-w-[88%] rounded-3xl px-4 py-3 bg-black text-white"
//                               : "max-w-[88%] rounded-3xl px-4 py-3 bg-white border border-black/10"
//                           }
//                         >
//                           <div className="whitespace-pre-wrap text-sm leading-relaxed">
//                             {m.content}
//                           </div>

//                           {m.role === "assistant" &&
//                             m.citations &&
//                             m.citations.length > 0 && (
//                               <>
//                                 <div className="my-3 h-px bg-black/10" />
//                                 <div className="space-y-2">
//                                   <div className="text-xs font-semibold text-black/60">
//                                     Citations
//                                   </div>

//                                   <div className="space-y-2">
//                                     {m.citations.map((c) => (
//                                       <a
//                                         key={`${m.id}-${c.rank}`}
//                                         href={c.url}
//                                         target="_blank"
//                                         rel="noreferrer"
//                                         className="block rounded-2xl border border-black/10 bg-white/70 px-3 py-2 hover:bg-white transition"
//                                       >
//                                         <div className="flex items-start justify-between gap-3">
//                                           <div className="text-xs leading-snug">
//                                             <span className="font-semibold">
//                                               SOURCE {c.rank}
//                                             </span>
//                                             <span className="text-black/60">
//                                               {" "}
//                                               — {prettyCitation(c)}
//                                             </span>
//                                           </div>
//                                           <ExternalLink className="h-4 w-4 text-black/50" />
//                                         </div>
//                                       </a>
//                                     ))}
//                                   </div>
//                                 </div>
//                               </>
//                             )}
//                         </div>
//                       </div>
//                     ))}

//                     {loading && (
//                       <div className="flex justify-start">
//                         <div className="max-w-[88%] rounded-3xl px-4 py-3 bg-white border border-black/10">
//                           <div className="flex items-center gap-2 text-sm text-black/60">
//                             <Loader2 className="h-4 w-4 animate-spin" />
//                             Thinking…
//                           </div>
//                         </div>
//                       </div>
//                     )}

//                     <div ref={scrollRef} />
//                   </div>
//                 </div>
//               </div>

//               {/* Input */}
//               <div className="px-6 pb-6">
//                 <div className="flex items-center gap-2">
//                   <input
//                     value={input}
//                     onChange={(e) => setInput(e.target.value)}
//                     onKeyDown={onKeyDown}
//                     placeholder="Ask from Charaka Samhita…"
//                     className="w-full rounded-3xl px-4 py-3 bg-white/90 border border-black/10 outline-none focus:ring-2 focus:ring-black/10"
//                     disabled={loading}
//                   />
//                   <button
//                     onClick={send}
//                     disabled={!canSend}
//                     className="rounded-3xl px-5 py-3 bg-black text-white flex items-center gap-2 disabled:opacity-50"
//                   >
//                     <Send className="h-4 w-4" />
//                     Send
//                   </button>
//                 </div>

//                 <p className="text-xs text-black/50 mt-3">
//                   Demo note: This chatbot answers only from the indexed Ashtanga
//                   Hridayam text. It is not a substitute for professional medical
//                   care.
//                 </p>
//               </div>
//             </div>
//           </div>
//         </div>
//       </div>
//     </div>
//   );
// }
"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { ExternalLink, Loader2, Send } from "lucide-react";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type Citation = {
  rank: number;
  score?: number;
  sthana: string;
  adhyaya_number: number;
  adhyaya_name: string;
  shloka_start: number;
  shloka_end: number;
  url: string;
};

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
};

const BG_URL = "/ayurbot.png"; 
const API_URL = "http://127.0.0.1:8000/chat";

function uid() {
  return Math.random().toString(16).slice(2) + Date.now().toString(16);
}

function prettyCitation(c: Citation) {
  return `${c.sthana} • Ch ${c.adhyaya_number} • ${c.adhyaya_name} • Shlokas ${c.shloka_start}-${c.shloka_end}`;
}

export default function AyurbotDemoPage() {
  const [messages, setMessages] = useState<ChatMessage[]>(() => [
    {
      id: "initial-message",
      role: "assistant",
      content:
        "Namaste. Ask me anything from Charaka Samhita — I will answer with citations.",
    },
  ]);

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [topK, setTopK] = useState(5);

  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const canSend = useMemo(
    () => input.trim().length > 0 && !loading,
    [input, loading]
  );

  async function send() {
    if (!canSend) return;
    const q = input.trim();
    setInput("");

    const userMsg: ChatMessage = { id: uid(), role: "user", content: q };
    setMessages((m) => [...m, userMsg]);
    setLoading(true);

    try {
      const res = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: q, top_k: topK }),
      });
      if (!res.ok) throw new Error("Backend Error");
      const data = await res.json();
      const botMsg: ChatMessage = {
        id: uid(),
        role: "assistant",
        content: data?.answer ?? "(No answer returned)",
        citations: Array.isArray(data?.citations) ? data.citations : [],
      };
      setMessages((m) => [...m, botMsg]);
    } catch (e: any) {
      setMessages((m) => [
        ...m,
        { id: uid(), role: "assistant", content: "I couldn't reach the backend." }
      ]);
    } finally {
      setLoading(false);
    }
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") send();
  }

  return (
    <div className="min-h-screen w-full overflow-hidden">
      {/* Background */}
      <div
        className="fixed inset-0 -z-10 bg-cover bg-center"
        style={{ backgroundImage: `url(${BG_URL})` }}
      />

      <div className="min-h-screen w-full relative">
        <div 
          className="absolute top-10 left-[25%] -translate-x-1/2 w-[42%] max-w-[850px] min-w-[380px]"
        >
          {/* Main Card */}
          <div className="rounded-3xl shadow-2xl border border-[#5d4037]/20 bg-[#f4ece1]/90 backdrop-blur-2xl overflow-hidden flex flex-col">
            
            {/* Header */}
            <div className="px-8 pt-8 pb-4 flex items-start justify-between gap-4">
              <div>
                <h1 className="text-2xl font-bold tracking-tight text-[#3e2723]">Ayurbot Chat</h1>
                <p className="text-sm text-[#5d4037]/70 font-semibold mt-0.5 uppercase tracking-wide">
                  Charaka Samhita • Vedantic RAG
                </p>
              </div>

              {/* TopK Toggles */}
              <div className="flex items-center gap-1 bg-[#3e2723]/5 p-1 rounded-full border border-[#3e2723]/10">
                {[3, 5, 7].map((k) => (
                  <button
                    key={k}
                    onClick={() => setTopK(k)}
                    className={
                      topK === k
                        ? "text-xs font-bold px-4 py-1.5 rounded-full bg-[#2d5a27] text-[#f4ece1] shadow-lg transition-all"
                        : "text-xs font-bold px-4 py-1.5 rounded-full text-[#3e2723]/60 hover:bg-[#3e2723]/10 transition-all"
                    }
                  >
                    {k}
                  </button>
                ))}
              </div>
            </div>

            {/* Chat History Area */}
            <div className="px-6 pb-4">
              <div className="rounded-[2rem] border border-[#3e2723]/10 bg-[#e8dfd1]/50 shadow-inner">
                <div className="h-[58vh] overflow-y-auto p-6 space-y-6">
                  {messages.map((m) => (
                    <div
                      key={m.id}
                      className={m.role === "user" ? "flex justify-end" : "flex justify-start"}
                    >
                      <div
                        className={
                          m.role === "user"
                            ? "max-w-[85%] rounded-2xl rounded-tr-none px-5 py-3.5 bg-[#3e2723] text-[#f4ece1] shadow-xl"
                            : "max-w-[85%] rounded-2xl rounded-tl-none px-5 py-3.5 bg-[#fdfbf7] border border-[#d7ccc8] shadow-md text-[#2a1b18]"
                        }
                      >
                        <div className="text-[15px] leading-relaxed font-medium">
                          <ReactMarkdown 
                            remarkPlugins={[remarkGfm]}
                            components={{
                              p: ({children}) => <p className="mb-2 last:mb-0">{children}</p>,
                              ul: ({children}) => <ul className="list-disc ml-4 mb-2">{children}</ul>,
                              ol: ({children}) => <ol className="list-decimal ml-4 mb-2">{children}</ol>,
                              li: ({children}) => <li className="mb-1">{children}</li>,
                              strong: ({children}) => <strong className="font-bold text-[#2d5a27]">{children}</strong>,
                              h3: ({children}) => <h3 className="text-lg font-bold text-[#3e2723] mt-4 mb-2 border-b border-[#d7ccc8] pb-1">{children}</h3>,
                            }}
                          >
                            {m.content}
                          </ReactMarkdown>
                        </div>

                        {/* Citations: Earthy Terracotta & Deep Green */}
                        {m.role === "assistant" && m.citations && m.citations.length > 0 && (
                          <div className="mt-4 pt-4 border-t border-[#d7ccc8] space-y-3">
                            <p className="text-[10px] font-black uppercase tracking-[0.15em] text-[#8d6e63]">Source Verification</p>
                            <div className="grid gap-2">
                              {m.citations.map((c) => (
                                <a
                                  key={`${m.id}-${c.rank}`}
                                  href={c.url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="group flex items-center justify-between gap-3 rounded-xl border border-[#d7ccc8] bg-[#f4ece1]/80 px-3 py-2.5 hover:bg-[#2d5a27] hover:border-[#2d5a27] transition-all group"
                                >
                                  <div className="text-[11px] font-semibold leading-tight text-[#3e2723] group-hover:text-[#f4ece1]">
                                    <span className="font-bold text-[#2d5a27] group-hover:text-[#a5d6a7]">#{c.rank}</span> — {prettyCitation(c)}
                                  </div>
                                  <ExternalLink className="h-3.5 w-3.5 text-[#3e2723]/30 group-hover:text-[#f4ece1]" />
                                </a>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}

                  {loading && (
                    <div className="flex justify-start">
                      <div className="rounded-2xl rounded-tl-none px-5 py-3.5 bg-[#fdfbf7] border border-[#d7ccc8]">
                        <div className="flex items-center gap-3 text-sm font-bold text-[#3e2723]/40">
                          <Loader2 className="h-4 w-4 animate-spin text-[#2d5a27]" />
                          Analyzing Sanskrit Manuscripts...
                        </div>
                      </div>
                    </div>
                  )}
                  <div ref={scrollRef} />
                </div>
              </div>
            </div>

            {/* Input Area: Warm Wood / Cocoa tones */}
            <div className="px-8 pb-8 pt-2">
              <div className="flex items-center gap-3">
                <input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={onKeyDown}
                  placeholder="Query the Charaka Samhita..."
                  className="w-full flex-1 rounded-2xl px-6 py-4 bg-[#fdfbf7] border-2 border-[#d7ccc8] outline-none focus:ring-4 focus:ring-[#3e2723]/5 focus:border-[#3e2723]/40 transition-all text-sm font-semibold text-[#3e2723] placeholder:text-[#3e2723]/30"
                  disabled={loading}
                />
                <button
                  onClick={send}
                  disabled={!canSend}
                  className="rounded-2xl px-8 py-4 bg-[#3e2723] text-[#f4ece1] flex items-center gap-2.5 disabled:opacity-30 hover:bg-[#2a1b18] active:scale-95 transition-all shadow-xl"
                >
                  <Send className="h-4 w-4 text-[#f4ece1]" />
                  <span className="font-bold text-sm">SEND</span>
                </button>
              </div>
              <p className="text-[10px] text-center text-[#3e2723]/40 mt-4 font-black uppercase tracking-[0.25em]">
                Authentic Ayurvedic Knowledge Engine
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}