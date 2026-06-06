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
]
