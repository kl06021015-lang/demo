import { createApp } from 'vue'
import { createRouter, createWebHashHistory } from 'vue-router'
import naive from 'naive-ui'
import App from './App.vue'
import { routes } from './router'

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

const app = createApp(App)
app.use(naive)
app.use(router)
app.mount('#app')
