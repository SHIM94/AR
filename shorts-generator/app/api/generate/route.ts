import Anthropic from "@anthropic-ai/sdk";
import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const maxDuration = 60;

const MODEL = process.env.ANTHROPIC_MODEL || "claude-opus-5-5";

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

type GenBody = {
  topic?: string;
  niche?: string;
  tone?: string;
  duration?: number; // seconds
};

const SYSTEM = `당신은 한국어 유튜브 쇼츠(Shorts) 전문 작가이자 편집 기획자입니다.
주어진 주제로 '손이 멈추는' 쇼츠 한 편의 제작 패키지를 만듭니다.

규칙:
- 첫 3초 훅은 스크롤을 멈추게 할 만큼 강력하고 구체적이어야 합니다. 과장된 수익 보장("무조건 2배")·허위·불법·투자 원금보장 표현은 쓰지 않습니다.
- 나레이션은 입말체, 짧은 문장, 숫자·구체 사례 중심으로 작성합니다.
- 자막(SRT)은 나레이션을 2~4초 단위로 끊어 타임코드를 매깁니다. 전체 길이는 요청된 duration 초에 맞춥니다.
- 썸네일 문구는 8자 이내 2줄 구성 3개 안을 제시합니다.
- 반드시 아래 JSON 스키마로만, 다른 설명 없이 출력합니다.

JSON 스키마:
{
  "title": "영상 제목(클릭 유도, 25자 이내)",
  "hook": "0~3초 훅 대사",
  "script": "전체 나레이션 전문(훅 포함, 줄바꿈 \\n 로 구분)",
  "srt": "SRT 자막 전문. 각 블록은 번호/타임코드(00:00:00,000 --> 00:00:03,000)/텍스트",
  "thumbnails": ["문구안1\\n문구안2", "...", "..."],
  "hashtags": ["#태그1", "#태그2", "..."],
  "cta": "마지막 행동 유도 문장(구독/저장 등)"
}`;

function extractJson(text: string): string {
  const fence = text.match(/```(?:json)?\s*([\s\S]*?)```/);
  if (fence) return fence[1].trim();
  const first = text.indexOf("{");
  const last = text.lastIndexOf("}");
  if (first !== -1 && last !== -1) return text.slice(first, last + 1);
  return text.trim();
}

export async function POST(req: NextRequest) {
  if (!process.env.ANTHROPIC_API_KEY) {
    return NextResponse.json(
      { error: "서버에 ANTHROPIC_API_KEY가 설정되지 않았습니다." },
      { status: 500 }
    );
  }

  let body: GenBody;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "잘못된 요청입니다." }, { status: 400 });
  }

  const topic = (body.topic || "").trim();
  if (!topic) {
    return NextResponse.json({ error: "주제를 입력해주세요." }, { status: 400 });
  }

  const niche = (body.niche || "재테크/정보").trim();
  const tone = (body.tone || "친근하고 신뢰감 있는").trim();
  const duration = Math.min(Math.max(Number(body.duration) || 45, 15), 90);

  const userPrompt = `채널 분야: ${niche}
톤앤매너: ${tone}
영상 길이: 약 ${duration}초
주제: ${topic}

위 조건으로 쇼츠 제작 패키지를 JSON으로 생성해줘.`;

  try {
    const message = await client.messages.create({
      model: MODEL,
      max_tokens: 4096,
      system: SYSTEM,
      messages: [{ role: "user", content: userPrompt }],
    });

    if (message.stop_reason === "refusal") {
      return NextResponse.json(
        { error: "해당 주제는 생성할 수 없습니다. 다른 주제로 시도해주세요." },
        { status: 422 }
      );
    }

    const textBlock = message.content.find((b) => b.type === "text");
    const raw = textBlock && "text" in textBlock ? textBlock.text : "";

    let parsed: unknown;
    try {
      parsed = JSON.parse(extractJson(raw));
    } catch {
      return NextResponse.json(
        { error: "생성 결과 파싱에 실패했습니다. 다시 시도해주세요.", raw },
        { status: 502 }
      );
    }

    return NextResponse.json({ result: parsed, model: MODEL });
  } catch (err: unknown) {
    const msg =
      err instanceof Anthropic.APIError
        ? `API 오류 (${err.status}): ${err.message}`
        : "알 수 없는 오류가 발생했습니다.";
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
