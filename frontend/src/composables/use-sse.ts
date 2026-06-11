import { ref, type Ref } from 'vue';

export function useAutoScroll(containerRef: Ref<HTMLElement | null>) {
  const isAtBottom = ref(true);

  function onScroll() {
    const el = containerRef.value;
    if (!el) return;
    const threshold = 4;
    isAtBottom.value = el.scrollTop + el.clientHeight >= el.scrollHeight - threshold;
  }

  function scrollToBottom() {
    const el = containerRef.value;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }

  return { isAtBottom, onScroll, scrollToBottom };
}
