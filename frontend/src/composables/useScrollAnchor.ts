/**
 * useScrollAnchor.ts — Smart scroll-to-bottom behavior
 * Inspired by Slack: auto-scrolls on new messages, shows a floating
 * "New messages" button when the user has scrolled up to read history.
 */
import { ref, type Ref } from 'vue'

export function useScrollAnchor(containerRef: Ref<HTMLElement | null>) {
  const isNearBottom = ref(true)
  const showScrollButton = ref(false)

  function onScroll() {
    const el = containerRef.value
    if (!el) return
    const threshold = 80 // pixels from bottom
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < threshold
    isNearBottom.value = atBottom
    showScrollButton.value = !atBottom
  }

  function scrollToBottom() {
    const el = containerRef.value
    if (!el) return
    el.scrollTop = el.scrollHeight
    showScrollButton.value = false
  }

  function smartScrollToBottom() {
    if (isNearBottom.value) {
      scrollToBottom()
    } else {
      showScrollButton.value = true
    }
  }

  return {
    isNearBottom,
    showScrollButton,
    onScroll,
    scrollToBottom,
    smartScrollToBottom,
  }
}
