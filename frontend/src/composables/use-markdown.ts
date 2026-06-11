function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function renderInline(text: string): string {
  return text
    // 行内代码 `code` — 先处理，内部不再替换
    .replace(/`([^`]+)`/g, (_, code) => `<code>${escapeHtml(code)}</code>`)
    // 删除线 ~~text~~
    .replace(/~~(.+?)~~/g, '<del>$1</del>')
    // 粗体 **text** 或 __text__
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/__(.+?)__/g, '<strong>$1</strong>')
    // 斜体 *text* 或 _text_
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/(?<!\w)_(.+?)_(?!\w)/g, '<em>$1</em>')
    // 链接 [text](url)
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
}

export function renderMarkdown(raw: string): string {
  if (!raw) return '';

  const parts = raw.split(/(```[\s\S]*?```)/g);

  return parts.map(part => {
    if (part.startsWith('```')) {
      const match = part.match(/^```(\w*)\n?([\s\S]*?)```$/);
      if (match) {
        const lang = match[1] ? ` class="language-${match[1]}"` : '';
        const code = escapeHtml(match[2].replace(/\n$/, ''));
        return `<pre><code${lang}>${code}</code></pre>`;
      }
      const incomplete = part.replace(/^```(\w*)\n?/, '');
      return `<pre><code>${escapeHtml(incomplete)}</code></pre>`;
    }

    const lines = part.split('\n');
    const htmlLines: string[] = [];
    let inUl = false, inOl = false;

    for (const line of lines) {
      const trimmed = line.trimStart();

      // 标题
      const headingMatch = trimmed.match(/^(#{1,6})\s+(.+)$/);
      if (headingMatch) {
        closeLists();
        const level = headingMatch[1].length;
        htmlLines.push(`<h${level}>${renderInline(headingMatch[2])}</h${level}>`);
        continue;
      }

      // 无序列表
      if (/^[-*+]\s+/.test(trimmed)) {
        if (!inUl) { closeLists(); htmlLines.push('<ul>'); inUl = true; }
        htmlLines.push(`<li>${renderInline(trimmed.replace(/^[-*+]\s+/, ''))}</li>`);
        continue;
      }

      // 有序列表
      if (/^\d+\.\s+/.test(trimmed)) {
        if (!inOl) { closeLists(); htmlLines.push('<ol>'); inOl = true; }
        htmlLines.push(`<li>${renderInline(trimmed.replace(/^\d+\.\s+/, ''))}</li>`);
        continue;
      }

      // 分割线
      if (/^---+$/.test(trimmed)) {
        closeLists();
        htmlLines.push('<hr />');
        continue;
      }

      // 空行
      if (trimmed === '') {
        closeLists();
        continue;
      }

      // 普通文本段落
      closeLists();
      htmlLines.push(`<p>${renderInline(trimmed)}</p>`);
    }

    closeLists();
    return htmlLines.join('\n');

    function closeLists() {
      if (inUl) { htmlLines.push('</ul>'); inUl = false; }
      if (inOl) { htmlLines.push('</ol>'); inOl = false; }
    }
  }).join('\n');
}