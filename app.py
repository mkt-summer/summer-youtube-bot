import streamlit as st
import os
import json
import urllib.parse
from analyzer import analyze_text, chat_title_thumbnail
from searcher import NaverSearcher, search_all_news, search_youtube_trends

# ── API 키 로드 (Streamlit Secrets → 로컬 저장 파일 → 환경변수 순) ──
CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'saved_keys.json')

def _secret(key: str, default: str = "") -> str:
    """st.secrets → 환경변수 순서로 값을 가져옴"""
    try:
        return st.secrets.get(key, default) or default
    except Exception:
        return os.getenv(key, default)

def load_keys():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)
    return {}

def save_keys(keys: dict):
    with open(CONFIG_PATH, 'w') as f:
        json.dump(keys, f)

# Secrets에 키가 있으면 사이드바 입력창 숨김
_secrets_anthropic = _secret("ANTHROPIC_API_KEY")
_secrets_naver_id  = _secret("NAVER_CLIENT_ID")
_secrets_naver_sec = _secret("NAVER_CLIENT_SECRET")
_has_secrets = bool(_secrets_anthropic)  # 핵심 키 존재 여부

# ── 페이지 설정 ───────────────────────────────────────────────
st.set_page_config(page_title="썸머 유튜브봇", page_icon="🎬", layout="wide",
                   initial_sidebar_state="expanded")

st.markdown("""
<style>
    .news-card {
        background: #ffffff; border-radius: 12px; padding: 18px 20px; margin: 10px 0;
        border-left: 5px solid #0284c7; box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        color: #1a1a1a; line-height: 1.7;
    }
    .img-card {
        background: #ffffff; border-radius: 12px; padding: 18px 20px; margin: 10px 0;
        border-left: 5px solid #7c3aed; box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        color: #1a1a1a; line-height: 1.7;
    }
    .tag-purple { display:inline-block; background:#f3e8ff; color:#6d28d9; border-radius:4px;
                  padding:2px 8px; font-size:0.8em; margin:2px; }
    .tag-gray   { display:inline-block; background:#f1f5f9; color:#475569; border-radius:4px;
                  padding:2px 8px; font-size:0.8em; margin:2px; }
    .quote-text { background:#f3f4f6; border-left:3px solid #9ca3af; padding:4px 10px;
                  border-radius:0 6px 6px 0; color:#374151; font-style:italic;
                  font-size:0.9em; margin:4px 0 8px 0; }
</style>
""", unsafe_allow_html=True)

# ── 사이드바 ──────────────────────────────────────────────────
saved = load_keys()
with st.sidebar:
    if _has_secrets:
        # ── 배포 모드: 키가 Secrets에 있으면 깔끔하게 표시만 ──
        st.title("🎬 썸머 유튜브봇")
        st.success("✅ API 키 설정 완료")
        st.caption("팀 공유 버전입니다.")
        anthropic_key = _secrets_anthropic
        naver_id      = _secrets_naver_id
        naver_secret  = _secrets_naver_sec
    else:
        # ── 로컬 모드: 직접 입력 ──
        st.title("⚙️ API 설정")
        st.markdown("**필수**")
        anthropic_key = st.text_input("🤖 Claude API Key", type="password",
            placeholder="sk-ant-...",
            value=saved.get("anthropic_key", os.getenv("ANTHROPIC_API_KEY", "")))
        st.markdown("---")
        st.markdown("**선택 (뉴스/트렌드 검색 향상)**")
        naver_id = st.text_input("🟢 네이버 Client ID", type="password",
            value=saved.get("naver_id", ""), help="네이버 뉴스 & 동영상 검색")
        naver_secret = st.text_input("🟢 네이버 Client Secret", type="password",
            value=saved.get("naver_secret", ""))
        st.markdown("---")
        if st.button("💾 API 키 저장", use_container_width=True):
            save_keys({"anthropic_key": anthropic_key, "naver_id": naver_id,
                       "naver_secret": naver_secret})
            st.success("✅ 저장 완료!")
        st.caption("💡 네이버 없이도 구글 뉴스로 기본 검색됩니다.")

# ── 메인 ──────────────────────────────────────────────────────
st.title("🎬 썸머 유튜브봇")

if not anthropic_key:
    st.warning("왼쪽 사이드바에서 Claude API 키를 먼저 입력해주세요.")
    st.stop()

main_tab1, main_tab2 = st.tabs(["🔍 이미지 & 뉴스 검색", "🖼️ 제목 & 썸네일"])

# ════════════════════════════════════════════════════
# 탭 1 — 이미지 & 뉴스 검색
# ════════════════════════════════════════════════════
with main_tab1:
    text_input = st.text_area(
        "대사 / 스크립트 입력",
        height=180,
        placeholder="편집할 영상의 대사나 내용을 붙여넣으세요.\n\n예) 유심사는 글로벌 eSIM 로밍 서비스를 제공하는 스타트업으로, 창업 후 3년 만에 매출 100억을 달성했습니다.",
        label_visibility="collapsed"
    )

    if st.button("🔍 이미지 & 뉴스 검색", type="primary", use_container_width=True):
        if not text_input.strip():
            st.warning("텍스트를 입력해주세요.")
        else:
            with st.spinner("분석 중... (10~30초 소요)"):
                result = analyze_text(text_input.strip(), anthropic_key)
            if 'error' in result:
                st.error(f"❌ {result['error']}")
            else:
                naver = NaverSearcher(naver_id, naver_secret) if (naver_id and naver_secret) else None
                news_results = {}
                for item in result.get('news_needs', []):
                    kw = item.get('search_keywords_ko', [])
                    if kw:
                        query = ' '.join(kw[:2])
                        news_results[item['id']] = {
                            'need': item, 'query': query,
                            'results': search_all_news(query, naver=naver, num=4)
                        }
                image_results = {}
                for item in result.get('image_needs', []):
                    kw = item.get('search_keywords_ko', [])
                    if kw:
                        query = ' '.join(kw[:2])
                        image_results[item['id']] = {'need': item, 'query': query}
                st.session_state['last_result']       = result
                st.session_state['last_news_results'] = news_results
                st.session_state['last_img_results']  = image_results

    if 'last_result' in st.session_state:
        result        = st.session_state['last_result']
        news_results  = st.session_state['last_news_results']
        image_results = st.session_state['last_img_results']

        res_tab1, res_tab2 = st.tabs([
            f"🖼️ 이미지 자료  ({len(image_results)}개)",
            f"📰 뉴스 기사  ({len(news_results)}개)"
        ])

        with res_tab1:
            st.caption("링크를 클릭하면 새 탭에서 바로 검색됩니다.")
            for iid, data in image_results.items():
                need     = data['need']
                query    = data['query']
                kw_en    = need.get('search_keywords_en', [])
                query_en = ' '.join(kw_en[:2]) if kw_en else query
                q        = urllib.parse.quote(query)
                q_en     = urllib.parse.quote(query_en)
                with st.expander(f"🔍 #{iid}  {need.get('title','')}", expanded=True):
                    if need.get('context_quote'):
                        st.markdown(f'<div class="quote-text">🗣 "{need["context_quote"]}"</div>',
                                    unsafe_allow_html=True)
                    col_info, col_links = st.columns([1, 1])
                    with col_info:
                        kw_ko = need.get('search_keywords_ko', [])
                        if kw_ko:
                            st.markdown("**🔍 한국어 검색어:** " + "  /  ".join(kw_ko))
                        if kw_en:
                            st.markdown("**🔍 영어 검색어:** " + "  /  ".join(kw_en))
                        st.markdown(f'<span class="tag-purple">🏷 {need.get("material_type","")}</span>',
                                    unsafe_allow_html=True)
                    with col_links:
                        st.markdown("**🔗 바로가기**")
                        st.markdown(
                            f"[🔍 구글 이미지](https://www.google.com/search?q={q}&tbm=isch&hl=ko)  \n"
                            f"[🟢 네이버 이미지](https://search.naver.com/search.naver?where=image&query={q})  \n"
                            f"[🎬 Envato](https://app.envato.com/search?itemType=photos&term={q_en})"
                        )

        with res_tab2:
            for nid, data in news_results.items():
                need    = data['need']
                results = data['results']
                with st.expander(
                    f"{'✅' if results else '❌'} #{nid}  {need.get('title','')}",
                    expanded=bool(results)
                ):
                    if not results:
                        st.warning("검색 결과 없음.")
                        kw = need.get('search_keywords_ko', [])
                        if kw:
                            q = urllib.parse.quote(' '.join(kw[:2]))
                            st.markdown(f"[🔍 직접 검색](https://search.naver.com/search.naver?where=news&query={q})")
                    for i, r in enumerate(results, 1):
                        st.markdown(f"""**{i}. {r['title']}**

{r.get('description','') or ''}

📅 {r.get('pub_date','-')}  |  출처: **{r.get('source','-')}**
🔗 [{r.get('link','')}]({r.get('link','')})

---""")

# ════════════════════════════════════════════════════
# 탭 2 — 제목 & 썸네일 (채팅)
# ════════════════════════════════════════════════════
STYLE_PATH = os.path.join(os.path.dirname(__file__), 'channel_style.json')

def load_style():
    if os.path.exists(STYLE_PATH):
        with open(STYLE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_style(style: dict):
    with open(STYLE_PATH, 'w', encoding='utf-8') as f:
        json.dump(style, f, ensure_ascii=False)

with main_tab2:
    # ── 채널 스타일 등록 ──────────────────────────────
    saved_style = load_style()
    with st.expander("📚 채널 스타일 등록 (클릭해서 열기)", expanded=not bool(saved_style)):
        st.caption("과거 예시를 등록하면 내 채널 톤앤매너에 맞게 만들어드려요.")
        col_a, col_b = st.columns(2)
        with col_a:
            past_copies = st.text_area(
                "썸네일 카피 예시 (한 줄에 하나씩)",
                value=saved_style.get('copies', ''),
                height=180,
                placeholder="예)\n만 원짜리 eSIM으로 연매출 300억\n코로나에 창업했습니다\n3년 만에 업계 1위"
            )
        with col_b:
            past_titles = st.text_area(
                "제목 예시 (한 줄에 하나씩)",
                value=saved_style.get('titles', ''),
                height=180,
                placeholder="예)\n한국 최초 해외 여행 eSIM 유심사가 업계 1위가 되기까지 | 스몰톡라운지\neSIM 몰랐던 분들 이거 보세요\n창업 3년만에 매출 100억 달성한 스타트업 대표 인터뷰"
            )
        if st.button("💾 스타일 저장", use_container_width=True):
            save_style({'copies': past_copies, 'titles': past_titles})
            st.success("✅ 저장됐어요!")

    # ── 트렌드 참고 영상 검색 ──────────────────────────
    st.markdown("---")
    st.markdown("#### 📊 트렌드 참고 영상")
    st.caption("키워드를 입력하면 요즘 잘나가는 유사 영상 제목을 가져와 제목/썸네일 생성에 자동으로 반영돼요.")

    trend_col1, trend_col2 = st.columns([3, 1])
    with trend_col1:
        trend_query = st.text_input(
            "트렌드 검색 키워드",
            placeholder="예) eSIM 스타트업, 창업 성공, 해외여행 유심",
            label_visibility="collapsed",
            key="trend_query_input"
        )
    with trend_col2:
        trend_search_btn = st.button("🔍 검색", use_container_width=True, key="trend_search_btn")

    if trend_search_btn and trend_query.strip():
        with st.spinner("트렌드 영상 검색 중..."):
            naver_for_trend = NaverSearcher(naver_id, naver_secret) if (naver_id and naver_secret) else None
            trends = search_youtube_trends(trend_query.strip(), naver=naver_for_trend, num=8)
        st.session_state['trend_results'] = trends
        st.session_state['trend_query']   = trend_query.strip()

    if st.session_state.get('trend_results'):
        trends = st.session_state['trend_results']
        tq     = st.session_state.get('trend_query', '')
        with st.expander(f"📺 '{tq}' YouTube 영상 {len(trends)}개 — 클릭해서 보기", expanded=True):
            for i, t in enumerate(trends, 1):
                link  = t.get('link', '')
                title = t.get('title', '')
                desc  = t.get('description', '')   # 채널명 · 조회수
                src   = t.get('source', '')
                sub   = f"<span style='color:#64748b;font-size:0.82em'>{desc}</span>" if desc else ""
                badge = f"<span style='color:#94a3b8;font-size:0.78em'> [{src}]</span>"
                if link:
                    st.markdown(
                        f"**{i}.** [{title}]({link}) {badge}  \n{sub}",
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        f"**{i}.** {title} {badge}  \n{sub}",
                        unsafe_allow_html=True
                    )
        if st.button("🗑️ 트렌드 초기화", key="trend_clear_btn"):
            st.session_state.pop('trend_results', None)
            st.session_state.pop('trend_query', None)
            st.rerun()
        st.caption("✅ 위 제목들이 Claude에게 트렌드 참고 자료로 전달됩니다.")

    st.markdown("---")

    # ── 세션 초기화 ────────────────────────────────────
    if 'tt_chat' not in st.session_state:
        st.session_state['tt_chat'] = []
    if 'tt_thinking' not in st.session_state:
        st.session_state['tt_thinking'] = False

    # ── 채팅 초기화 버튼 ──────────────────────────────
    if st.button("🔄 대화 초기화", use_container_width=False):
        st.session_state['tt_chat'] = []
        st.session_state['tt_thinking'] = False
        st.rerun()

    # ── 메시지 컨테이너 (입력창보다 먼저 선언 → 입력창 위에 고정) ──
    chat_container = st.container()

    with chat_container:
        for msg in st.session_state['tt_chat']:
            with st.chat_message(msg['role']):
                st.markdown(msg['content'])

        # AI 응답 생성 중일 때 스피너를 컨테이너 안에 표시
        if st.session_state['tt_thinking']:
            with st.chat_message('assistant'):
                with st.spinner("생각 중..."):
                    style        = load_style()
                    trend_titles = [
                        t['title'] for t in st.session_state.get('trend_results', [])
                        if t.get('title')
                    ]
                    reply = chat_title_thumbnail(
                        st.session_state['tt_chat'], style, anthropic_key,
                        trend_titles=trend_titles if trend_titles else None
                    )
                st.markdown(reply)
            st.session_state['tt_chat'].append({'role': 'assistant', 'content': reply})
            st.session_state['tt_thinking'] = False
            st.rerun()

    # ── 채팅 입력 (컨테이너 아래에 고정) ──────────────
    if prompt := st.chat_input("영상 내용을 입력하거나 수정 요청을 해보세요 (예: 더 자극적으로, 짧게, 5개 더)"):
        st.session_state['tt_chat'].append({'role': 'user', 'content': prompt})
        st.session_state['tt_thinking'] = True
        st.rerun()
