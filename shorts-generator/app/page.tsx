"use client";

import { useState } from "react";

type Result = {
  title: string;
  hook: string;
  script: string;
  srt: string;
  thumbnails: string[];
  hashtags: string[];
  cta: string;
};

function Copy({ text }: { text: string }) {
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
      {done ? "복사됨 ✓" : "복사"}
    </button>
  );
}

export default function Home() {
  const [topic, setTopic] = useState("");
  const [niche, setNiche] = useState("재테크/정보");
  const [tone, setTone] = useState("친근하고 신뢰감 있는");
  const [duration, setDuration] = useState(45);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<Result | null>(null);

  async function generate() {
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const res = await fetch("/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic, niche, tone, duration }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.error || "생성에 실패했습니다.");
      } else {
        setResult(data.result as Result);
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
          주제 한 줄만 넣으면 <b>대본 · SRT 자막 · 썸네일 문구 · 해시태그</b>를
          한 번에 뽑아드립니다. 재테크·정보·일상 어떤 채널이든.
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
        <button
          className="primary"
          onClick={generate}
          disabled={loading || !topic.trim()}
        >
          {loading ? (
            <>
              <span className="spin" />
              생성 중…
            </>
          ) : (
            "쇼츠 패키지 생성하기"
          )}
        </button>
      </div>

      {error && <div className="err">{error}</div>}

      {result && (
        <div className="card result">
          <div className="block">
            <h3>제목</h3>
            <div className="title-big">{result.title}</div>
          </div>

          <div className="block">
            <h3>
              훅 (0~3초) <Copy text={result.hook} />
            </h3>
            <pre>{result.hook}</pre>
          </div>

          <div className="block">
            <h3>
              나레이션 대본 <Copy text={result.script} />
            </h3>
            <pre>{result.script}</pre>
          </div>

          <div className="block">
            <h3>
              자막 (SRT) <Copy text={result.srt} />
            </h3>
            <pre>{result.srt}</pre>
          </div>

          <div className="block">
            <h3>썸네일 문구 3안</h3>
            <div className="thumbs">
              {result.thumbnails?.map((t, i) => (
                <div className="thumb" key={i}>
                  {t}
                </div>
              ))}
            </div>
          </div>

          <div className="block">
            <h3>해시태그</h3>
            <div className="tags">
              {result.hashtags?.map((h, i) => (
                <span className="tag" key={i}>
                  {h}
                </span>
              ))}
            </div>
          </div>

          <div className="block">
            <h3>
              마무리 CTA <Copy text={result.cta} />
            </h3>
            <pre>{result.cta}</pre>
          </div>
        </div>
      )}

      <div className="foot">
        ⚠️ 투자·수익 관련 콘텐츠는 참고용이며 원금 보장이 아닙니다. 생성 결과는
        검토 후 사용하세요.
      </div>
    </div>
  );
}
