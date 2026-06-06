/**
 * Theme composable — manages dark/light mode state, localStorage persistence,
 * and Naive UI theme integration.
 */
import { ref, computed, watch, onMounted } from 'vue'
import { darkTheme } from 'naive-ui'
import type { GlobalThemeOverrides } from 'naive-ui'

// ---------------------------------------------------------------------------
// Reactive state
// ---------------------------------------------------------------------------

const isDark = ref(false)

// ---------------------------------------------------------------------------
// CSS class / data-attr
// ---------------------------------------------------------------------------

const themeClass = computed<'light' | 'dark'>(() => (isDark.value ? 'dark' : 'light'))

// ---------------------------------------------------------------------------
// Naive UI theme
// ---------------------------------------------------------------------------

const naiveTheme = computed(() => (isDark.value ? darkTheme : null))

const naiveThemeOverrides = computed<GlobalThemeOverrides>(() => {
  if (isDark.value) {
    return {
      common: {
        primaryColor: '#6AE033',
        primaryColorHover: '#7DE84A',
        primaryColorPressed: '#58CC02',
        primaryColorSuppl: '#6AE033',
        infoColor: '#6AE033',
        infoColorHover: '#7DE84A',
        infoColorPressed: '#58CC02',
        infoColorSuppl: '#6AE033',
        successColor: '#34C759',
        successColorHover: '#4CD964',
        successColorPressed: '#30B350',
        warningColor: '#FFB340',
        warningColorHover: '#FFB84D',
        warningColorPressed: '#F0A020',
        errorColor: '#FF5252',
        errorColorHover: '#FF6E6E',
        errorColorPressed: '#E04848',
        bodyColor: '#121212',
        cardColor: '#1E1E1E',
        modalColor: '#1E1E1E',
        popoverColor: '#1E1E1E',
        inputColor: '#2A2A2A',
        dividerColor: '#333333',
        borderColor: '#333333',
        textColor1: '#FFFFFF',
        textColor2: '#B3B3B3',
        textColor3: '#808080',
        borderRadius: '8px',
      },
    }
  }
  return {
    common: {
      primaryColor: '#58CC02',
      primaryColorHover: '#4CAF00',
      primaryColorPressed: '#3D8B00',
      primaryColorSuppl: '#58CC02',
      infoColor: '#58CC02',
      infoColorHover: '#4CAF00',
      infoColorPressed: '#3D8B00',
      infoColorSuppl: '#58CC02',
      successColor: '#18a058',
      warningColor: '#f0a020',
      errorColor: '#d03050',
      borderRadius: '8px',
    },
  }
})

// ---------------------------------------------------------------------------
// Toggle
// ---------------------------------------------------------------------------

function toggleTheme(): void {
  isDark.value = !isDark.value
}

// ---------------------------------------------------------------------------
// Init — read from localStorage, apply data-theme
// ---------------------------------------------------------------------------

let _initialized = false

export function initTheme(): void {
  if (_initialized) return
  _initialized = true

  const saved = localStorage.getItem('theme')
  isDark.value = saved === 'dark'

  // Apply data-theme attribute reactively
  watch(
    isDark,
    (val) => {
      document.documentElement.dataset.theme = val ? 'dark' : 'light'
      localStorage.setItem('theme', val ? 'dark' : 'light')
    },
    { immediate: true }
  )

  // Prevent transition flash on page load
  document.documentElement.classList.add('no-transitions')
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      document.documentElement.classList.remove('no-transitions')
    })
  })
}

// ---------------------------------------------------------------------------
// Export
// ---------------------------------------------------------------------------

export function useTheme() {
  initTheme()
  return {
    isDark,
    themeClass,
    naiveTheme,
    naiveThemeOverrides,
    toggleTheme,
  }
}
