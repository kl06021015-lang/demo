import type { RouteRecordRaw } from 'vue-router'
import Home from './views/Home.vue'

export const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'home',
    component: Home,
  },
  {
    path: '/practice/:sceneId',
    name: 'practice',
    component: () => import('./views/Practice.vue'),
  },
  {
    path: '/summary/:sessionId',
    name: 'summary',
    component: () => import('./views/Summary.vue'),
  },
  {
    path: '/history',
    name: 'history',
    component: () => import('./views/History.vue'),
  },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: () => import('./views/Dashboard.vue'),
  },
  {
    path: '/replay/:sessionId',
    name: 'replay',
    component: () => import('./views/Replay.vue'),
  },
  {
    path: '/vocabulary',
    name: 'vocabulary',
    component: () => import('./views/Vocabulary.vue'),
  },
  {
    path: '/pronunciation',
    name: 'pronunciation',
    component: () => import('./views/Pronunciation.vue'),
  },
]
