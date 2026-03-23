import anthropic
from typing import Dict


# ── 제목·썸네일 생성 ──────────────────────────────────────────
def chat_title_thumbnail(messages: list, channel_style: dict, api_key: str,
                         trend_titles: list = None) -> str:
    """채팅 방식으로 제목·썸네일 생성 (티키타카)"""
    client = anthropic.Anthropic(api_key=api_key)

    past_copies = channel_style.get('copies', '').strip()
    past_titles = channel_style.get('titles', '').strip()

    system = """당신은 유튜브 채널 전문 마케터입니다. 사용자와 대화하면서 썸네일 카피와 제목을 함께 만들어나갑니다.

【썸네일 카피】썸네일 이미지에 올라가는 짧고 임팩트 있는 문구. 10단어 이내. 숫자/반전/궁금증 유발.
【제목】유튜브 검색에 노출되는 풀 제목. 키워드 앞배치, 브랜드명·인물명 포함, 채널/시리즈명 필요시 포함.

응답 형식: **썸네일 카피** 후보 3~5개 → **제목** 후보 3~5개, 각 항목 한 줄 설명.
수정 요청이 오면 즉시 반영. 자연스럽고 친근하게 대화."""

    if past_copies:
        system += f"\n\n【이 채널의 썸네일 카피 스타일 — 반드시 참고】\n{past_copies}"
    if past_titles:
        system += f"\n\n【이 채널의 제목 스타일 — 반드시 참고】\n{past_titles}"

    if trend_titles:
        titles_text = "\n".join(f"- {t}" for t in trend_titles)
        system += f"\n\n【요즘 잘나가는 유사 유튜브 영상 제목 — 트렌드 참고용】\n{titles_text}\n(위 제목들의 패턴·키워드·어투를 참고해 더 클릭을 유발하는 결과를 만들어주세요.)"

    api_messages = [{'role': m['role'], 'content': m['content']} for m in messages]

    try:
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=system,
            messages=api_messages
        )
        return msg.content[0].text
    except Exception as e:
        return f"오류: {str(e)}"


def generate_title_thumbnail(text: str, api_key: str) -> Dict:
    """영상 내용에서 유튜브 제목·썸네일 아이디어 생성"""
    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"""당신은 유튜브 채널 성장 전문가이자 썸네일 디자이너입니다.
아래 영상 내용을 보고 클릭률이 높은 제목과 썸네일 아이디어를 제안해주세요.

━━ 영상 내용 ━━
{text}
━━━━━━━━━━

【제목 작성 기준】
- 클릭하고 싶은 호기심 유발
- 핵심 키워드 앞에 배치
- 숫자, 반전, 질문형 활용
- 30자 내외 (너무 길지 않게)

【썸네일 기준】
- 텍스트 오버레이: 3~5단어, 크고 굵게
- 인물 표정/제스처 제안
- 배경/색감 제안
- 강조할 핵심 비주얼 요소"""

    tool = {
        "name": "suggest_title_thumbnail",
        "description": "유튜브 제목과 썸네일 아이디어 제안",
        "input_schema": {
            "type": "object",
            "properties": {
                "titles": {
                    "type": "array",
                    "description": "제목 후보 5~8개",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title":  {"type": "string", "description": "제목"},
                            "reason": {"type": "string", "description": "이 제목이 효과적인 이유 (한 줄)"},
                            "type":   {"type": "string", "description": "호기심자극/숫자형/질문형/반전형/정보형 중 하나"}
                        },
                        "required": ["title", "reason", "type"]
                    }
                },
                "thumbnails": {
                    "type": "array",
                    "description": "썸네일 아이디어 3~4개",
                    "items": {
                        "type": "object",
                        "properties": {
                            "concept":     {"type": "string", "description": "썸네일 전체 컨셉 설명"},
                            "text_overlay":{"type": "string", "description": "썸네일에 넣을 텍스트 (3~5단어)"},
                            "visual":      {"type": "string", "description": "배경/인물/색감 등 비주얼 설명"},
                            "emotion":     {"type": "string", "description": "전달할 감정/분위기"}
                        },
                        "required": ["concept", "text_overlay", "visual", "emotion"]
                    }
                },
                "hashtags": {
                    "type": "array",
                    "description": "추천 해시태그 10개",
                    "items": {"type": "string"}
                }
            },
            "required": ["titles", "thumbnails", "hashtags"]
        }
    }

    try:
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            tools=[tool],
            tool_choice={"type": "tool", "name": "suggest_title_thumbnail"},
            messages=[{"role": "user", "content": prompt}]
        )
        for block in msg.content:
            if block.type == "tool_use":
                return dict(block.input)
    except Exception as e:
        return {"error": str(e)}

    return {"error": "생성 실패. 다시 시도해주세요."}


# ── 텍스트 직접 입력 분석 ────────────────────────────────────
def analyze_text(text: str, api_key: str) -> Dict:
    """대사/스크립트 텍스트에서 이미지·뉴스 자료 추천"""
    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"""당신은 방송/유튜브 영상 편집 전문가입니다.
아래 대사/스크립트를 보고 편집에 필요한 이미지 자료와 뉴스 기사를 추천해주세요.

━━ 텍스트 ━━
{text}
━━━━━━━

【이미지 자료 추천 기준】
- 브랜드/회사/서비스명 → 로고, 앱 화면
- 인물 언급 → 인물 사진, 프로필
- 수치/통계 → 그래프, 인포그래픽
- 제품/기술 → 제품 사진, 다이어그램
- 장소/국가 → 해당 장소 사진
- 개념 설명 → 시각화 이미지

【뉴스 기사 추천 기준】
- 정부기관/정책/법안 → 관련 기사
- 시장 수치/트렌드 → 시장 분석 기사
- 기업/인물 → 관련 뉴스

검색어는 구체적으로: "유심사 eSIM 앱 화면" O / "앱" X"""

    tool = {
        "name": "suggest_materials",
        "description": "이미지와 뉴스 자료 추천",
        "input_schema": {
            "type": "object",
            "properties": {
                "image_needs": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id":                 {"type": "integer"},
                            "title":              {"type": "string"},
                            "context_quote":      {"type": "string"},
                            "search_keywords_ko": {"type": "array", "items": {"type": "string"},
                                                   "description": "2~3개"},
                            "search_keywords_en": {"type": "array", "items": {"type": "string"},
                                                   "description": "1~2개"},
                            "material_type":      {"type": "string",
                                                   "description": "사진/그래픽/영상캡처/로고 중 하나"}
                        },
                        "required": ["id", "title", "search_keywords_ko", "material_type"]
                    }
                },
                "news_needs": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id":                 {"type": "integer"},
                            "title":              {"type": "string"},
                            "description":        {"type": "string"},
                            "search_keywords_ko": {"type": "array", "items": {"type": "string"},
                                                   "description": "2~3개"},
                            "time_range":         {"type": "string"}
                        },
                        "required": ["id", "title", "search_keywords_ko"]
                    }
                }
            },
            "required": ["image_needs", "news_needs"]
        }
    }

    try:
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            tools=[tool],
            tool_choice={"type": "tool", "name": "suggest_materials"},
            messages=[{"role": "user", "content": prompt}]
        )
        for block in msg.content:
            if block.type == "tool_use":
                return dict(block.input)
    except Exception as e:
        return {"error": str(e)}

    return {"error": "분석 실패. 다시 시도해주세요."}


def _get_duration_minutes(srt_data: Dict) -> int:
    try:
        t = srt_data.get('duration', '00:00:00,000').replace(',', '.').split('.')[0]
        parts = t.split(':')
        total_sec = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        return max(1, total_sec // 60)
    except Exception:
        return 10


def _make_stamped_text(srt_data: Dict, max_chars: int = 12000) -> str:
    from srt_parser import format_with_timestamps
    text = format_with_timestamps(srt_data['subtitles'], interval_seconds=30)
    if len(text) > max_chars:
        half = max_chars // 2
        text = text[:half] + "\n\n[...중략...]\n\n" + text[-2000:]
    return text


def _base_prompt(stamped_text: str, duration_min: int) -> str:
    return f"""당신은 방송/유튜브 영상 편집 전문가입니다.
아래 자막을 처음부터 끝까지 꼼꼼히 읽고 편집 자료를 찾아주세요.
[HH:MM:SS] 타임스탬프 기준으로 삽입 위치를 정확히 제시하세요.

영상 총 길이: 약 {duration_min}분

━━━ 자막 ━━━
{stamped_text}
━━━━━━━━━━━"""


# ── 자막 청크 분할 ────────────────────────────────────────────
def _split_subtitles_by_time(subtitles: list, chunk_minutes: int = 10) -> list:
    """자막을 N분 단위로 분할"""
    if not subtitles:
        return [[]]
    chunks, current, boundary_sec = [], [], chunk_minutes * 60
    for sub in subtitles:
        t = sub['start'].replace(',', '.').split('.')[0]
        parts = t.split(':')
        try:
            sec = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        except (ValueError, IndexError):
            sec = 0
        if current and sec >= boundary_sec:
            chunks.append(current)
            current = []
            boundary_sec += chunk_minutes * 60
        current.append(sub)
    if current:
        chunks.append(current)
    return chunks or [[]]


# ── 1단계: 이미지 자료 분석 ───────────────────────────────────
def analyze_images(srt_data: Dict, api_key: str) -> Dict:
    """10분 단위 청크로 나눠서 분석 후 합침"""
    client       = anthropic.Anthropic(api_key=api_key)
    duration_min = _get_duration_minutes(srt_data)
    chunks       = _split_subtitles_by_time(srt_data['subtitles'], chunk_minutes=10)

    all_needs, item_id = [], 1

    for i, chunk_subs in enumerate(chunks):
        chunk_start = i * 10
        chunk_end   = min((i + 1) * 10, duration_min)
        label       = f"{chunk_start}~{chunk_end}분"
        min_cnt     = max(5, (chunk_end - chunk_start) * 2)   # 1분에 2개

        chunk_data   = {**srt_data, 'subtitles': chunk_subs}
        stamped_text = _make_stamped_text(chunk_data, max_chars=8000)

        result = _try_analyze_images(client, duration_min, min_cnt,
                                     stamped_text, label)
        if result.get('image_needs'):
            for item in result['image_needs']:
                item['id'] = item_id
                item_id += 1
            all_needs.extend(result['image_needs'])

    if all_needs:
        return {
            'image_needs': all_needs,
            '_meta': {'duration_min': duration_min, 'min_images': len(all_needs),
                      'chunks': len(chunks)}
        }
    return {"error": f"이미지 분석 실패 ({len(chunks)}개 구간 모두 실패). API 키를 확인하거나 잠시 후 다시 시도해주세요."}


def _try_analyze_images(client, duration_min: int, min_images: int,
                         stamped_text: str, chunk_label: str = "") -> Dict:
    """청크 하나에 대한 이미지 분석 호출"""
    section = f"{chunk_label} 구간" if chunk_label else "전체"

    prompt = f"""당신은 방송/유튜브 영상 편집 전문가입니다.
아래는 약 {duration_min}분짜리 영상의 [{section}] 자막입니다.

이 구간을 편집할 때 삽입할 B-roll(보조 이미지/영상 자료)을 추천해주세요.

━━ 자막 ({section}) ━━
{stamped_text}
━━━━━━━

【B-roll 추천 기준 (나올 때마다 반드시 추천)】
- 회사/브랜드/서비스명 → 로고, 앱 화면, 웹사이트 캡처
- 인물 소개/언급 → 인물 사진, 프로필
- 숫자/통계/수치 → 그래프, 인포그래픽
- 제품/기술 설명 → 제품 사진, 다이어그램
- 장소/국가 언급 → 해당 장소 사진
- 경쟁사/타사 비교 → 비교 화면
- 뉴스/사건/트렌드 → 관련 뉴스 화면
- 개념 설명 → 시각화 이미지

검색어는 구체적으로: "유심사 eSIM 앱 화면" O / "앱" X

⚠️ 최소 {min_images}개. 빈 배열 절대 금지."""

    tool = {
        "name": "provide_images",
        "description": f"{section} B-roll 목록. 최소 {min_images}개.",
        "input_schema": {
            "type": "object",
            "properties": {
                "image_needs": {
                    "type": "array",
                    "description": f"최소 {min_images}개. 빈 배열 금지.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id":                 {"type": "integer"},
                            "timestamp_start":    {"type": "string"},
                            "timestamp_end":      {"type": "string"},
                            "context_quote":      {"type": "string",
                                                   "description": "자막 한 줄 (짧게)"},
                            "title":              {"type": "string",
                                                   "description": "필요한 이미지 설명 (한 줄)"},
                            "search_keywords_ko": {"type": "array",
                                                   "items": {"type": "string"},
                                                   "description": "2~3개"},
                            "search_keywords_en": {"type": "array",
                                                   "items": {"type": "string"},
                                                   "description": "1~2개"},
                            "material_type":      {"type": "string",
                                                   "description": "사진/그래픽/영상캡처/로고 중 하나"}
                        },
                        "required": ["id", "timestamp_start", "title",
                                     "search_keywords_ko", "material_type"]
                    }
                }
            },
            "required": ["image_needs"]
        }
    }

    try:
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=8192,
            tools=[tool],
            tool_choice={"type": "tool", "name": "provide_images"},
            messages=[{"role": "user", "content": prompt}]
        )
        for block in msg.content:
            if block.type == "tool_use":
                return dict(block.input)
    except Exception as e:
        return {"error": str(e)}

    return {"image_needs": []}


# ── 2단계: 뉴스 기사 분석 ─────────────────────────────────────
def analyze_news(srt_data: Dict, api_key: str) -> Dict:
    """뉴스 기사만 분석 (2단계)"""
    client = anthropic.Anthropic(api_key=api_key)
    duration_min = _get_duration_minutes(srt_data)
    min_news     = max(5, duration_min // 3)
    stamped_text = _make_stamped_text(srt_data)

    prompt = _base_prompt(stamped_text, duration_min) + f"""

【뉴스 기사 — 최소 {min_news}개 필수】
다음 항목이 언급될 때마다 반드시 뉴스 기사 추천:
① 정부기관 (과기부·방통위·공정위 등) → 해당 기관의 구체적 정책/규제 기사
② 법/규제/제도 → 해당 법안 시행/통과 기사
③ 시장규모·성장률·점유율 수치 → 해당 수치가 담긴 시장 분석 기사
④ 경쟁사/타사 언급 → 비교 기사
⑤ 창업·투자·IR → 투자 유치, 성장 관련 기사
⑥ 사건·사고·이슈  ⑦ 트렌드·전망

【검색어 작성 규칙】
- 실제 뉴스 검색에서 기사가 나오도록 구체적으로
- 나쁜 예: "eSIM 규제" → 좋은 예: "eSIM 단말기 자급제 규제 완화 과학기술정보통신부"
- 기관명/회사명/인물명/법안명은 정확한 명칭으로
- 연도가 중요하면 검색어에 연도 포함

빠뜨리지 말고 최대한 많이 찾을 것."""

    tool = {
        "name": "provide_news",
        "description": f"뉴스 기사 목록 제공. 최소 {min_news}개.",
        "input_schema": {
            "type": "object",
            "properties": {
                "news_needs": {
                    "type": "array",
                    "description": f"최소 {min_news}개. 기관/법/수치/이슈 언급 시 반드시 포함.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id":                 {"type": "integer"},
                            "timestamp_start":    {"type": "string"},
                            "timestamp_end":      {"type": "string"},
                            "context_quote":      {"type": "string"},
                            "title":              {"type": "string"},
                            "description":        {"type": "string"},
                            "purpose":            {"type": "string"},
                            "search_keywords_ko": {"type": "array", "items": {"type": "string"}},
                            "time_range":         {"type": "string"},
                            "media_type":         {"type": "string", "description": "종합일간지/경제지/방송뉴스/IT전문매체/공식보도자료"}
                        },
                        "required": ["id", "timestamp_start", "timestamp_end", "context_quote",
                                     "title", "description", "purpose", "search_keywords_ko", "time_range"]
                    }
                }
            },
            "required": ["news_needs"]
        }
    }

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8192,
        tools=[tool],
        tool_choice={"type": "tool", "name": "provide_news"},
        messages=[{"role": "user", "content": prompt}]
    )
    for block in msg.content:
        if block.type == "tool_use":
            result = dict(block.input)
            result['_meta'] = {'duration_min': duration_min, 'min_news': min_news}
            return result

    return {"error": "뉴스 분석 실패. 다시 시도해주세요."}
