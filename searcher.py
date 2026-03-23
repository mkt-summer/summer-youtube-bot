import requests
import re
import xml.etree.ElementTree as ET
import urllib.parse
from typing import List, Dict, Optional
from datetime import datetime


# ── 네이버 검색 ─────────────────────────────────────────────

class NaverSearcher:
    BASE_URL = "https://openapi.naver.com/v1/search"

    def __init__(self, client_id: str, client_secret: str):
        self.headers = {
            "X-Naver-Client-Id": client_id,
            "X-Naver-Client-Secret": client_secret
        }

    def _get(self, endpoint: str, params: dict) -> Optional[dict]:
        try:
            r = requests.get(
                f"{self.BASE_URL}/{endpoint}",
                headers=self.headers,
                params=params,
                timeout=10
            )
            if r.status_code == 200:
                return r.json()
            return None
        except Exception:
            return None

    def search_news(self, query: str, display: int = 5) -> List[Dict]:
        data = self._get("news.json", {"query": query, "display": display, "sort": "date"})
        if not data:
            return []
        items = []
        for item in data.get('items', []):
            items.append({
                'title': re.sub(r'<[^>]+>', '', item.get('title', '')),
                'description': re.sub(r'<[^>]+>', '', item.get('description', '')),
                'link': item.get('originallink') or item.get('link', ''),
                'pub_date': item.get('pubDate', ''),
                'source': '네이버 뉴스',
                'query': query
            })
        return items

    def search_images(self, query: str, display: int = 6) -> List[Dict]:
        data = self._get("image", {"query": query, "display": display, "filter": "all"})
        if not data:
            return []
        items = []
        for item in data.get('items', []):
            items.append({
                'title': re.sub(r'<[^>]+>', '', item.get('title', '')),
                'thumbnail': item.get('thumbnail', ''),
                'link': item.get('link', ''),
                'source_url': item.get('sizeheight', ''),
                'source': '네이버 이미지',
                'query': query
            })
        return items


# ── 구글 뉴스 RSS (API 키 불필요) ────────────────────────────

def search_google_news(query: str, num: int = 5) -> List[Dict]:
    encoded = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded}&hl=ko&gl=KR&ceid=KR:ko"
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            return []
        root = ET.fromstring(r.content)
        items = []
        for item in root.findall('.//item')[:num]:
            title_el = item.find('title')
            link_el = item.find('link')
            date_el = item.find('pubDate')
            source_el = item.find('source')
            title = title_el.text if title_el is not None else ''
            # 구글 뉴스 제목에서 매체명 제거
            title_clean = re.sub(r'\s*-\s*[^-]+$', '', title).strip()
            items.append({
                'title': title_clean,
                'description': '',
                'link': link_el.text if link_el is not None else '',
                'pub_date': date_el.text if date_el is not None else '',
                'source': source_el.text if source_el is not None else '구글 뉴스',
                'query': query
            })
        return items
    except Exception:
        return []


# ── Unsplash 이미지 (API 키 필요, 무료) ─────────────────────

def search_unsplash(query: str, access_key: str, num: int = 6) -> List[Dict]:
    url = "https://api.unsplash.com/search/photos"
    params = {"query": query, "per_page": num, "lang": "ko"}
    headers = {"Authorization": f"Client-ID {access_key}"}
    try:
        r = requests.get(url, params=params, headers=headers, timeout=10)
        if r.status_code != 200:
            return []
        data = r.json()
        items = []
        for photo in data.get('results', []):
            items.append({
                'title': photo.get('alt_description') or photo.get('description') or query,
                'thumbnail': photo['urls']['small'],
                'link': photo['links']['html'],
                'source': f"Unsplash / {photo['user']['name']}",
                'query': query,
                'license': 'Unsplash 라이선스 (상업적 사용 가능)'
            })
        return items
    except Exception:
        return []


# ── 통합 검색 함수 ────────────────────────────────────────────

def search_all_news(
    query: str,
    naver: Optional[NaverSearcher] = None,
    num: int = 4
) -> List[Dict]:
    """네이버 우선, 없으면 구글 뉴스로 폴백"""
    results = []
    if naver:
        results = naver.search_news(query, display=num)
    if not results:
        results = search_google_news(query, num=num)
    return results


def search_youtube_trends(
    query: str,
    naver: Optional[NaverSearcher] = None,
    num: int = 8
) -> List[Dict]:
    """실제 YouTube 검색 결과에서 영상 제목 가져오기 (ytInitialData 파싱)"""
    import json as _json

    results = _scrape_youtube_search(query, num)

    # 유튜브 스크래핑 실패 시 네이버 vclip 폴백
    if not results and naver:
        data = naver._get("vclip.json", {"query": query, "display": num, "sort": "sim"})
        if data:
            for item in data.get('items', []):
                title = re.sub(r'<[^>]+>', '', item.get('title', ''))
                link  = item.get('link', '')
                results.append({
                    'title':  title,
                    'link':   link,
                    'description': '',
                    'source': '네이버 동영상'
                })

    return results


def _scrape_youtube_search(query: str, num: int = 8) -> List[Dict]:
    """YouTube 검색 페이지의 ytInitialData JSON에서 영상 제목 파싱"""
    import json as _json

    encoded = urllib.parse.quote(query)
    url = f"https://www.youtube.com/results?search_query={encoded}&hl=ko"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8",
    }

    try:
        r = requests.get(url, headers=headers, timeout=12)
        if r.status_code != 200:
            return []

        # ytInitialData = {...}; 패턴 추출
        match = re.search(r'var ytInitialData\s*=\s*(\{.*?\});\s*</script>', r.text, re.DOTALL)
        if not match:
            # 대안 패턴
            match = re.search(r'ytInitialData"\s*:\s*(\{.*?\})\s*,\s*"ytInitialPlayerResponse', r.text, re.DOTALL)
        if not match:
            return []

        data = _json.loads(match.group(1))

        # JSON 경로: contents → twoColumnSearchResultsRenderer → ...
        sections = (
            data
            .get('contents', {})
            .get('twoColumnSearchResultsRenderer', {})
            .get('primaryContents', {})
            .get('sectionListRenderer', {})
            .get('contents', [])
        )

        results = []
        for section in sections:
            items = section.get('itemSectionRenderer', {}).get('contents', [])
            for item in items:
                vr = item.get('videoRenderer', {})
                if not vr:
                    continue
                title_runs = vr.get('title', {}).get('runs', [])
                title = ''.join(r.get('text', '') for r in title_runs)
                video_id = vr.get('videoId', '')
                channel_runs = vr.get('ownerText', {}).get('runs', [])
                channel = ''.join(r.get('text', '') for r in channel_runs)
                view_text = ''
                for vl in vr.get('viewCountText', {}).get('runs', []):
                    view_text += vl.get('text', '')
                if not view_text:
                    view_text = vr.get('viewCountText', {}).get('simpleText', '')

                if title and video_id:
                    results.append({
                        'title':       title,
                        'link':        f"https://www.youtube.com/watch?v={video_id}",
                        'description': f"{channel} · {view_text}".strip(' ·'),
                        'source':      'YouTube'
                    })
                if len(results) >= num:
                    break
            if len(results) >= num:
                break

        return results

    except Exception:
        return []


def search_all_images(
    query: str,
    naver: Optional[NaverSearcher] = None,
    unsplash_key: Optional[str] = None,
    num: int = 4
) -> List[Dict]:
    """네이버 → Unsplash 순으로 이미지 검색"""
    results = []
    if naver:
        results = naver.search_images(query, display=num)
    if not results and unsplash_key:
        results = search_unsplash(query, unsplash_key, num=num)
    return results
