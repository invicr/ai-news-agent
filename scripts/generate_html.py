#!/usr/bin/env python3
"""AI 뉴스 JSON을 편집 가능한 이메일 에디터 HTML로 변환하는 스크립트.

- result_editor.html 기반: 드래그&드롭 순서 변경, 이메일 미리보기, HTML 복사
- result_card.html 기반: 이메일용 카드 레이아웃 (XHTML Transitional 테이블)
- 백엔드 없이 standalone으로 동작
"""

import json
import sys
from datetime import datetime
from pathlib import Path

EDITOR_CSS = """\
body {
    margin: 0;
    padding: 24px;
    font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif;
    background: #f3f6fb;
    color: #0f172a;
}
.layout {
    max-width: 1200px;
    margin: 0 auto;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
}
.panel {
    background: #ffffff;
    border: 1px solid #dbe3f0;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 4px 14px rgba(15, 23, 42, 0.05);
}
.panel-header {
    padding: 14px 16px;
    border-bottom: 1px solid #e6edf7;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    background: #f8fbff;
}
.panel-title {
    margin: 0;
    font-size: 18px;
}
.panel-body {
    padding: 14px;
}
.actions {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
}
.btn {
    border: 1px solid #1d4ed8;
    background: #1d4ed8;
    color: #fff;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 14px;
    cursor: pointer;
}
.btn.secondary {
    background: #fff;
    color: #1d4ed8;
}
.btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
}
.meta {
    font-size: 13px;
    color: #475569;
    margin-top: 8px;
}
.article-item {
    border: 1px solid #d9e2f2;
    border-radius: 10px;
    padding: 12px;
    margin-bottom: 10px;
    background: #ffffff;
    cursor: grab;
    transition: border-color 0.15s ease, background-color 0.15s ease;
    position: relative;
    overflow: hidden;
}
.article-item.dragging {
    opacity: 0.45;
    cursor: grabbing;
}
.article-item.drag-over {
    border-color: #2563eb;
    background: #eff6ff;
}
.article-row {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 10px;
}
.article-title {
    margin: 0;
    font-size: 14px;
    line-height: 1.4;
}
.article-date {
    font-size: 12px;
    background: #eaf2ff;
    color: #1e40af;
    border-radius: 999px;
    padding: 2px 8px;
    white-space: nowrap;
}
.article-url {
    display: block;
    margin-top: 6px;
    font-size: 12px;
    color: #2563eb;
    text-decoration: none;
    word-break: break-all;
}
.article-actions {
    display: flex;
    gap: 6px;
    margin-top: 10px;
}
.move-btn {
    border: 1px solid #c7d2fe;
    background: #eef2ff;
    color: #1e3a8a;
    border-radius: 6px;
    font-size: 12px;
    padding: 4px 8px;
    cursor: pointer;
}
.delete-btn {
    border: 1px solid #fecaca;
    background: #fff7f7;
    color: #b91c1c;
    border-radius: 6px;
    font-size: 12px;
    padding: 4px 8px;
    cursor: pointer;
}
.preview-frame {
    width: 100%;
    min-height: 720px;
    height: 720px;
    border: 0;
    background: #fff;
}
.status {
    font-size: 13px;
    color: #0f766e;
    min-height: 20px;
}
@media (max-width: 980px) {
    .layout {
        grid-template-columns: 1fr;
    }
    .preview-frame {
        min-height: 500px;
    }
}
"""

# result_card.html 이메일 카드 템플릿을 JS 템플릿 리터럴로 변환
# 백틱 내부이므로 따옴표 이스케이프 불필요
EDITOR_JS = r"""
(function() {
    var currentDate = CURRENT_DATE_PLACEHOLDER;
    var articles = ARTICLES_PLACEHOLDER;

    var articleListEl = document.getElementById('articleList');
    var previewFrame = document.getElementById('previewFrame');
    var statusText = document.getElementById('statusText');
    var metaText = document.getElementById('metaText');
    var copyHtmlBtn = document.getElementById('copyHtmlBtn');
    var refreshPreviewBtn = document.getElementById('refreshPreviewBtn');
    var previewUpdateTimer = null;

    function setStatus(message, isError) {
        statusText.textContent = message;
        statusText.style.color = isError ? '#b91c1c' : '#0f766e';
    }

    function escapeHtml(value) {
        var div = document.createElement('div');
        div.textContent = value == null ? '' : value;
        return div.innerHTML;
    }

    function updateMetaText() {
        metaText.textContent = currentDate + ' / 총 ' + articles.length + '건';
    }

    /* ── result_card.html 포맷 렌더링 ── */
    function renderCardRow(article) {
        var lines = (article.content || '').split('\n').filter(function(l) { return l.trim(); });
        var contentHtml = '';
        for (var i = 0; i < lines.length; i++) {
            contentHtml += '<p style="margin: 0 0 8px 0; text-align: left;">' + escapeHtml(lines[i]) + '</p>\n';
        }

        return '<tr>\n'
            + '<td style="padding: 10px 15px; background-color: #F6F8FC;">\n'
            + '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border: 1px solid #D9E2F2; border-radius: 10px; overflow: hidden; background-color: #ffffff;">\n'
            + '<tr>\n'
            + '<td style="background-color: #EAF2FF; padding: 12px 15px; border-bottom: 1px solid #D9E2F2; border-top-left-radius: 10px; border-top-right-radius: 10px;">\n'
            + '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">\n'
            /* 제목만 */
            + '<tr>\n'
            + '<td style="text-align: left;">\n'
            + "<h2 style=\"margin: 0; font-size: 16px; font-weight: 700; color: #0F172A; line-height: 1.45; word-break: break-word; overflow-wrap: anywhere; font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif; text-align: left;\">" + escapeHtml(article.title) + '</h2>\n'
            + '</td>\n'
            + '</tr>\n'
            + '</table>\n'
            + '</td>\n'
            + '</tr>\n'
            /* 본문 영역 */
            + '<tr>\n'
            + '<td style="padding: 15px; background-color: #ffffff;">\n'
            /* 매체명 | 날짜 + 원문 보기 */
            + '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">\n'
            + '<tr>\n'
            + '<td style="text-align: left;" valign="middle">\n'
            + "<span style=\"font-size: 12px; color: #475569; font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif;\">" + escapeHtml(article.source) + ' | ' + escapeHtml(article.date) + '</span>\n'
            + '</td>\n'
            + '<td align="right" valign="middle" style="white-space: nowrap;">\n'
            + '<a href="' + escapeHtml(article.url) + '" target="_blank" rel="noopener noreferrer" aria-label="' + escapeHtml(article.title) + " 원문 보기\" style=\"display: inline-block; color: #2563EB; text-decoration: none; font-size: 12px; line-height: 1.4; font-weight: bold; font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif; border: 1px solid #2563EB; border-radius: 14px; padding: 4px 10px;\">원문 보기</a>\n"
            + '</td>\n'
            + '</tr>\n'
            + '</table>\n'
            /* 구분선 */
            + '<div style="border-top: 1px solid #E6EDF7; margin: 10px 0;"></div>\n'
            /* 요약문 */
            + "<div style=\"color: #333333; font-size: 14px; line-height: 1.5; margin: 0; font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif; text-align: left;\">\n"
            + contentHtml
            + '</div>\n'
            + '</td>\n'
            + '</tr>\n'
            + '</table>\n'
            + '</td>\n'
            + '</tr>\n';
    }

    function renderEmailHtml() {
        var rows = '';
        for (var i = 0; i < articles.length; i++) {
            rows += renderCardRow(articles[i]);
        }

        return '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">\n'
            + '<html xmlns="http://www.w3.org/1999/xhtml">\n'
            + '<head>\n'
            + '    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />\n'
            + '    <meta name="viewport" content="width=device-width, initial-scale=1.0"/>\n'
            + '    <title>\uc774\uba54\uc77c\uc6a9 \ub274\uc2a4 \uce74\ub4dc</title>\n'
            + '</head>\n'
            + '<body style="margin: 0; padding: 0;">\n'
            + '    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">\n'
            + '        <tr>\n'
            + '            <td align="center" style="padding: 0;">\n'
            + '                <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="width: 100%; max-width: 600px; margin: 0 auto; background-color: #ffffff;">\n'
            + '                    <tr>\n'
            + '                        <td align="center" style="background-color: #0B1220; padding: 30px 20px 28px 20px; border-bottom: 3px solid #2563EB;">\n'
            + '                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">\n'
            + '                                <tr>\n'
            + '                                    <td>\n'
            + "                                        <h1 style=\"color: #ffffff !important; margin: 0; font-size: 32px; line-height: 1.25; font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif; text-align: center;\">AI \ub3d9\ud5a5 \ube0c\ub9ac\ud551 " + escapeHtml(currentDate) + '</h1>\n'
            + '                                    </td>\n'
            + '                                </tr>\n'
            + '                            </table>\n'
            + '                        </td>\n'
            + '                    </tr>\n'
            + rows
            + '                    <tr>\n'
            + '                        <td style="padding: 10px; background-color: #F6F8FC; text-align: center;">\n'
            + "                            <p style=\"font-size: 12px; line-height: 1.5; font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif; color: #000000;\">\n"
            + '                                \u2709\uFE0F \uc804\uc0ac AX\ud300 (<a href="mailto:dx.ax@samsung.com" style="color: #2563EB; text-decoration: none;">dx.ax@samsung.com</a>)\n'
            + '                            </p>\n'
            + '                        </td>\n'
            + '                    </tr>\n'
            + '                </table>\n'
            + '            </td>\n'
            + '        </tr>\n'
            + '    </table>\n'
            + '</body>\n'
            + '</html>';
    }

    /* ── 에디터 목록 렌더링 (result_editor.html 포맷) ── */
    function renderList() {
        articleListEl.innerHTML = '';
        for (var idx = 0; idx < articles.length; idx++) {
            var article = articles[idx];
            var item = document.createElement('article');
            item.className = 'article-item';
            item.draggable = true;
            item.dataset.index = String(idx);
            item.innerHTML = '<div class="article-row">'
                + '<h3 class="article-title">' + (idx + 1) + '. ' + escapeHtml(article.title) + '</h3>'
                + '<span class="article-date">' + escapeHtml((article.source || '') + ' | ' + (article.date || '')) + '</span>'
                + '</div>'
                + '<a class="article-url" href="' + escapeHtml(article.url) + '" target="_blank" rel="noopener noreferrer">' + escapeHtml(article.url) + '</a>'
                + '<div class="article-actions">'
                + '<button class="move-btn" type="button" data-action="up" data-index="' + idx + '">위로</button>'
                + '<button class="move-btn" type="button" data-action="down" data-index="' + idx + '">아래로</button>'
                + '<button class="delete-btn" type="button" data-action="delete" data-index="' + idx + '">삭제</button>'
                + '</div>';
            articleListEl.appendChild(item);
        }
    }

    function swapArticles(fromIndex, toIndex) {
        if (toIndex < 0 || toIndex >= articles.length) return;
        var temp = articles[fromIndex];
        articles[fromIndex] = articles[toIndex];
        articles[toIndex] = temp;
        renderList();
        updateMetaText();
        setStatus('순서를 변경했습니다. 미리보기를 갱신하거나 바로 복사할 수 있습니다.');
        schedulePreviewRefresh();
    }

    function moveArticle(fromIndex, toIndex) {
        if (fromIndex === toIndex || fromIndex < 0 || toIndex < 0 || fromIndex >= articles.length || toIndex >= articles.length) return;
        var moved = articles.splice(fromIndex, 1)[0];
        articles.splice(toIndex, 0, moved);
        renderList();
        updateMetaText();
        setStatus('순서를 변경했습니다. 미리보기를 갱신하거나 바로 복사할 수 있습니다.');
        schedulePreviewRefresh();
    }

    function deleteArticle(index) {
        articles.splice(index, 1);
        renderList();
        updateMetaText();
        setStatus('기사를 삭제했습니다.');
        schedulePreviewRefresh();
    }

    function schedulePreviewRefresh() {
        if (previewUpdateTimer) clearTimeout(previewUpdateTimer);
        previewUpdateTimer = setTimeout(function() {
            previewUpdateTimer = null;
            refreshPreview();
        }, 400);
    }

    function refreshPreview() {
        var html = renderEmailHtml();
        previewFrame.srcdoc = html;
        setStatus('미리보기를 갱신했습니다.');
    }

    function resizePreviewFrame() {
        try {
            var doc = previewFrame.contentDocument;
            if (!doc || !doc.body || !doc.documentElement) return;
            var nextHeight = Math.max(doc.body.scrollHeight, doc.documentElement.scrollHeight, 720);
            previewFrame.style.height = (nextHeight + 8) + 'px';
        } catch (e) {}
    }

    function copyEmailHtml() {
        copyHtmlBtn.disabled = true;
        setStatus('복사용 HTML 생성 중...');
        var html = renderEmailHtml();

        if (navigator.clipboard && window.ClipboardItem && navigator.clipboard.write) {
            var item = new ClipboardItem({
                'text/html': new Blob([html], { type: 'text/html' }),
                'text/plain': new Blob([html], { type: 'text/plain' })
            });
            navigator.clipboard.write([item]).then(function() {
                setStatus('이메일용 HTML을 복사했습니다. 메일 작성창에 바로 붙여넣으세요.');
                copyHtmlBtn.disabled = false;
            }).catch(function(err) {
                setStatus('복사 실패: ' + err.message, true);
                copyHtmlBtn.disabled = false;
            });
            return;
        }

        navigator.clipboard.writeText(html).then(function() {
            setStatus('클립보드에 HTML 텍스트를 복사했습니다.');
            copyHtmlBtn.disabled = false;
        }).catch(function(err) {
            setStatus('복사 실패: ' + err.message, true);
            copyHtmlBtn.disabled = false;
        });
    }

    /* ── 이벤트 바인딩 (result_editor.html과 동일) ── */
    articleListEl.addEventListener('click', function(event) {
        var target = event.target;
        if (!(target instanceof HTMLButtonElement)) return;
        var action = target.dataset.action;
        var index = Number(target.dataset.index);
        if (isNaN(index)) return;
        if (action === 'up') swapArticles(index, index - 1);
        else if (action === 'down') swapArticles(index, index + 1);
        else if (action === 'delete') deleteArticle(index);
    });

    articleListEl.addEventListener('dragstart', function(event) {
        var item = event.target.closest('.article-item');
        if (!item) return;
        item.classList.add('dragging');
        event.dataTransfer.effectAllowed = 'move';
        event.dataTransfer.setData('text/plain', item.dataset.index || '');
    });

    articleListEl.addEventListener('dragover', function(event) {
        event.preventDefault();
        var dropItem = event.target.closest('.article-item');
        if (!dropItem || dropItem.classList.contains('dragging')) return;
        dropItem.classList.add('drag-over');
        event.dataTransfer.dropEffect = 'move';
    });

    articleListEl.addEventListener('dragleave', function(event) {
        var item = event.target.closest('.article-item');
        if (item) item.classList.remove('drag-over');
    });

    articleListEl.addEventListener('drop', function(event) {
        event.preventDefault();
        var dropItem = event.target.closest('.article-item');
        if (!dropItem) return;
        dropItem.classList.remove('drag-over');
        var fromIndex = Number(event.dataTransfer.getData('text/plain'));
        var toIndex = Number(dropItem.dataset.index);
        if (isNaN(fromIndex) || isNaN(toIndex)) return;
        moveArticle(fromIndex, toIndex);
    });

    articleListEl.addEventListener('dragend', function() {
        var items = articleListEl.querySelectorAll('.article-item');
        for (var i = 0; i < items.length; i++) {
            items[i].classList.remove('dragging', 'drag-over');
        }
    });

    refreshPreviewBtn.addEventListener('click', refreshPreview);
    copyHtmlBtn.addEventListener('click', copyEmailHtml);
    previewFrame.addEventListener('load', resizePreviewFrame);

    /* ── 초기화 ── */
    updateMetaText();
    renderList();
    previewFrame.srcdoc = renderEmailHtml();
    setStatus('순서를 조정한 뒤 "이메일용 HTML 복사"를 누르세요.');
})();
"""


def transform_articles(raw_articles: list) -> list:
    """JSON 스키마를 에디터 형식 {title, source, date, content, url}로 변환."""
    result = []
    for a in raw_articles:
        lines = []
        why = a.get("why_relevant", "")
        if why:
            lines.append(why)
        for s in a.get("summary", []):
            # summary가 이미 '- '로 시작하면 그대로, 아니면 추가
            text = s.strip()
            if not text.startswith("- "):
                text = "- " + text
            lines.append(text)

        result.append({
            "title": a.get("title", ""),
            "source": a.get("source", ""),
            "date": a.get("published_date", ""),
            "content": "\n".join(lines),
            "url": a.get("url", ""),
        })
    return result


def generate_editor_html(articles: list, date_str: str) -> str:
    articles_json = json.dumps(articles, ensure_ascii=False)
    date_json = json.dumps(date_str, ensure_ascii=False)

    js_code = EDITOR_JS.replace("CURRENT_DATE_PLACEHOLDER", date_json).replace(
        "ARTICLES_PLACEHOLDER", articles_json
    )

    return (
        '<!DOCTYPE html>\n'
        '<html lang="ko">\n'
        '<head>\n'
        '    <meta charset="UTF-8">\n'
        '    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        f'    <title>AI 동향 브리핑 편집</title>\n'
        f'    <style>\n{EDITOR_CSS}    </style>\n'
        '</head>\n'
        '<body>\n'
        '    <div class="layout">\n'
        '        <section class="panel">\n'
        '            <div class="panel-header">\n'
        '                <h1 class="panel-title">기사 순서 조정</h1>\n'
        '                <div class="actions">\n'
        '                    <button id="refreshPreviewBtn" class="btn secondary" type="button">미리보기 갱신</button>\n'
        '                    <button id="copyHtmlBtn" class="btn" type="button">이메일용 HTML 복사</button>\n'
        '                </div>\n'
        '            </div>\n'
        '            <div class="panel-body">\n'
        '                <div class="meta" id="metaText"></div>\n'
        '                <p class="meta">복사된 내용은 스크립트 없는 정적 HTML이라 메일 붙여넣기에 적합합니다.</p>\n'
        '                <div class="status" id="statusText"></div>\n'
        '                <div id="articleList"></div>\n'
        '            </div>\n'
        '        </section>\n'
        '\n'
        '        <section class="panel">\n'
        '            <div class="panel-header">\n'
        '                <h2 class="panel-title">이메일 미리보기</h2>\n'
        '            </div>\n'
        '            <iframe id="previewFrame" class="preview-frame" title="email-preview"></iframe>\n'
        '        </section>\n'
        '    </div>\n'
        f'    <script>\n{js_code}\n    </script>\n'
        '</body>\n'
        '</html>\n'
    )


def main():
    if len(sys.argv) > 1:
        json_path = Path(sys.argv[1])
    else:
        today = datetime.now().strftime("%Y-%m-%d")
        json_path = Path(__file__).resolve().parent.parent / "output" / f"ai-news-{today}.json"

    if not json_path.exists():
        print(f"파일을 찾을 수 없습니다: {json_path}", file=sys.stderr)
        sys.exit(1)

    raw_articles = json.loads(json_path.read_text(encoding="utf-8"))
    date_str = json_path.stem.replace("ai-news-", "")
    articles = transform_articles(raw_articles)

    html = generate_editor_html(articles, date_str)

    output_path = json_path.with_suffix(".html")
    output_path.write_text(html, encoding="utf-8")
    print(f"HTML 생성 완료: {output_path}")
    print(f"총 {len(articles)}건의 기사가 포함되었습니다.")


if __name__ == "__main__":
    main()
