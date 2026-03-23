import re
from typing import Dict, List


def parse_srt(content: str) -> Dict:
    """SRT 파일을 파싱해서 텍스트와 타임스탬프를 추출"""
    # 인코딩 정리
    content = content.strip()

    # SRT 블록 파싱 (번호 → 타임스탬프 → 텍스트)
    pattern = r'\d+\s*\n(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*\n(.*?)(?=\n\s*\n\d+\s*\n|\Z)'
    blocks = re.findall(pattern, content, re.DOTALL)

    subtitles = []
    for start, end, text in blocks:
        clean_text = re.sub(r'<[^>]+>', '', text)  # HTML 태그 제거
        clean_text = clean_text.strip().replace('\n', ' ')
        if clean_text:
            subtitles.append({
                'start': start,
                'end': end,
                'text': clean_text
            })

    full_text = ' '.join([s['text'] for s in subtitles])

    # 총 길이 추출
    duration = "알 수 없음"
    if subtitles:
        duration = subtitles[-1]['end']

    return {
        'subtitles': subtitles,
        'full_text': full_text,
        'total_count': len(subtitles),
        'duration': duration,
        'char_count': len(full_text)
    }


def format_with_timestamps(subtitles: List[Dict], interval_seconds: int = 30) -> str:
    """Claude에게 보낼 타임스탬프 포함 텍스트 생성

    30초마다 타임스탬프를 찍어서 Claude가 '몇 분에 어떤 내용인지' 알 수 있게 함
    예시:
    [00:00:05] 안녕하세요 오늘은 eSIM에 대해 이야기해볼게요
    [00:00:35] eSIM이 처음 등장한 건 2018년이었습니다
    """
    if not subtitles:
        return ""

    lines = []
    last_stamped_seconds = -interval_seconds  # 첫 줄은 무조건 타임스탬프

    for sub in subtitles:
        # "HH:MM:SS,mmm" → 초로 변환
        t = sub['start'].replace(',', '.').split('.')[0]  # "HH:MM:SS"
        parts = t.split(':')
        try:
            total_sec = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        except (ValueError, IndexError):
            total_sec = 0

        if total_sec - last_stamped_seconds >= interval_seconds:
            # HH:MM:SS 형식으로 타임스탬프 표시
            ts = sub['start'].split(',')[0]  # milliseconds 제거
            lines.append(f"\n[{ts}]")
            last_stamped_seconds = total_sec

        lines.append(sub['text'])

    return ' '.join(lines)


def get_srt_segments(subtitles: List[Dict], segment_minutes: int = 3) -> List[Dict]:
    """자막을 시간대별 세그먼트로 나눔 (긴 영상 분석용)"""
    segments = []
    current_segment = []
    segment_start = None

    for sub in subtitles:
        time_parts = sub['start'].split(':')
        minutes = int(time_parts[0]) * 60 + int(time_parts[1])

        if segment_start is None:
            segment_start = minutes

        if minutes - segment_start >= segment_minutes and current_segment:
            segments.append({
                'start_time': subtitles[len(segments) * segment_minutes]['start'] if len(segments) * segment_minutes < len(subtitles) else current_segment[0]['start'],
                'text': ' '.join([s['text'] for s in current_segment])
            })
            current_segment = []
            segment_start = minutes

        current_segment.append(sub)

    if current_segment:
        segments.append({
            'start_time': current_segment[0]['start'],
            'text': ' '.join([s['text'] for s in current_segment])
        })

    return segments
