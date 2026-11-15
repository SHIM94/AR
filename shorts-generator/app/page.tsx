"use client";

import { useEffect, useState } from "react";

type Episode = {
  ep: number;
  title: string;
  hook: string;
  script: string;
  srt: string;
  description: string;
  thumbnails: string[];
  hashtags: string[];
  cta: string;
};

type Result = {
  series_title: string;
  episodes: Episode[];
};

const FREE_PER_DAY = 3;

function todayKey() {
  return new Date().toISOString().slice(0, 10);
}

function readUsage(): number {
  try {
    const raw = localStorage.getItem("usage");
    if (!raw) return 0;
    const obj = JSON.parse(raw);
    if (obj.date !== todayKey()) return 0;
    return obj.count || 0;
  } catch {
    return 0;
  }
}

function bumpUsage(): number {
  const next = readUsage() + 1;
  try {
    localStorage.setItem("usage", JSON.stringify({ date: todayKey(), count: next }));
  } catch {
    /* ignore */
  }
  return next;
}

function Copy({ text, label = "복사" }: { text: string; label?: string }) {
  const [done, setDone] = useState(false);
  return (
    <button
      className="copybtn"
      onClick={async () => {
        await navigator.clipboard.writeText(text);
        setDone(true);
        setTimeout(() => setDone(false), 1200);
      }}
    >
      {done ? "복사됨 ✓" : label}
    </button>
  );
}

function EpisodeView({ e }: { e: Episode }) {
  const uploadBundle = [
    `【제목】 ${e.title}`,
    "",
    `【설명란】`,
    e.description,
    "",
    e.hashtags?.join(" "),
  ].join("\n");

  return (
    <div className="result">
      <div className="block">
        <h3>제목</h3>
        <div className="title-big">{e.title}</div>
      </div>

      <div className="block">
        <h3>
          훅 (0~3초) <Copy text={e.hook} />
        </h3>
        <pre>{e.hook}</pre>
      </div>

      <div className="block">
        <h3>
          나레이션 대본 <Copy text={e.script} />
        </h3>
        <pre>{e.script}</pre>
      </div>

      <div className="block">
        <h3>
          자막 (SRT) <Copy text={e.srt} />
        </h3>
        <pre>{e.srt}</pre>
      </div>

      <div className="block">
        <h3>썸네일 문구 3안</h3>
        <div className="thumbs">
          {e.thumbnails?.map((t, i) => (
            <div className="thumb" key={i}>
              {t}
            </div>
          ))}
        </div>
      </div>

      <div className="block">
        <h3>
          유튜브 업로드용 (제목+설명+태그) <Copy text={uploadBundle} label="전체 복사" />
        </h3>
        <pre>{uploadBundle}</pre>
      </div>

      <div className="block">
        <h3>
          마무리 CTA <Copy text={e.cta} />
        </h3>
        <pre>{e.cta}</pre>
      </div>
    </div>
  );
}

export default function Home() {
  const [topic, setTopic] = useState("");
  const [niche, setNiche] = useState("재테크/정보");
  const [tone, setTone] = useState("친근하고 신뢰감 있는");
  const [duration, setDuration] = useState(45);
  const [episodes, setEpisodes] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<Result | null>(null);
  const [active, setActive] = useState(0);
  const [used, setUsed] = useState(0);

  useEffect(() => {
    setUsed(readUsage());
  }, []);

  const remaining = Math.max(0, FREE_PER_DAY - used);
  const gated = remaining <= 0;

  async function generate() {
    if (gated) return;
    setLoading(true);
    setError("");
    setResult(null);
    setActive(0);
    try {
      const res = await fetch("/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic, niche, tone, duration, episodes }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.error || "생성에 실패했습니다.");
      } else {
        setResult(data.result as Result);
        setUsed(bumpUsage());
      }
    } catch {
      setError("네트워크 오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="wrap">
      <div className="hero">
        <h1>쇼츠 공장 🎬</h1>
        <p>
          주제 한 줄만 넣으면 <b>대본 · SRT 자막 · 썸네일 문구 · 업로드 메타데이터</b>를
          한 번에. 시리즈(1~3화)도 자동 생성.
        </p>
      </div>

      <div className="card">
        <div className="field">
          <label>영상 주제 *</label>
          <textarea
            placeholder="예: 월급 300만원 직장인이 1년에 1000만원 모으는 현실적인 방법"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
          />
        </div>
        <div className="grid">
          <div className="field">
            <label>채널 분야</label>
            <input value={niche} onChange={(e) => setNiche(e.target.value)} />
          </div>
          <div className="field">
            <label>톤앤매너</label>
            <input value={tone} onChange={(e) => setTone(e.target.value)} />
          </div>
        </div>
        <div className="grid">
          <div className="field">
            <label>영상 길이: {duration}초</label>
            <input
              type="range"
              min={15}
              max={90}
              step={5}
              value={duration}
              onChange={(e) => setDuration(Number(e.target.value))}
            />
          </div>
          <div className="field">
            <label>시리즈 편수: {episodes}화</label>
            <input
              type="range"
              min={1}
              max={3}
              step={1}
              value={episodes}
              onChange={(e) => setEpisodes(Number(e.target.value))}
            />
          </div>
        </div>
        <button
          className="primary"
          onClick={generate}
          disabled={loading || !topic.trim() || gated}
        >
          {loading ? (
            <>
              <span className="spin" />
              생성 중… {episodes > 1 ? `(${episodes}화)` : ""}
            </>
          ) : gated ? (
            "오늘 무료 횟수를 모두 사용했어요"
          ) : (
            "쇼츠 패키지 생성하기"
          )}
        </button>
        <div className="quota">
          오늘 남은 무료 생성: <b>{remaining}</b> / {FREE_PER_DAY}회
        </div>
      </div>

      {gated && (
        <div className="upsell">
          <b>무제한으로 쓰고 싶으신가요?</b>
          <br />
          프로 플랜(준비 중)에서는 하루 제한 없이, 시리즈 10화까지, 썸네일
          이미지까지 생성됩니다. 관심 있으면 알려주세요.
        </div>
      )}

      {error && <div className="err">{error}</div>}

      {result && (
        <div className="card">
          {result.series_title && (
            <div className="series-title">📺 {result.series_title}</div>
          )}

          {result.episodes?.length > 1 && (
            <div className="tabs">
              {result.episodes.map((e, i) => (
                <button
                  key={i}
                  className={`tab ${i === active ? "on" : ""}`}
                  onClick={() => setActive(i)}
                >
                  {e.ep || i + 1}화
                </button>
              ))}
            </div>
          )}

          {result.episodes?.[active] && (
            <EpisodeView e={result.episodes[active]} />
          )}
        </div>
      )}

      <div className="foot">
        ⚠️ 투자·수익 관련 콘텐츠는 참고용이며 원금 보장이 아닙니다. 생성 결과는
        검토 후 사용하세요.
      </div>
    </div>
  );
}
