import { createRouter, createWebHistory } from 'vue-router'

const APP_NAME = 'Control de Pases'

// Comprueba si el token guardado es un JWT expirado sin llamar al backend
const isTokenExpired = (token) => {
  try {
    const payload = JSON.parse(
      atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')),
    )
    return typeof payload.exp === 'number' && payload.exp * 1000 <= Date.now()
  } catch {
    // Si el token no es un JWT legible, lo dejamos pasar y que el backend decida
    return false
  }
}

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/components/LoginView.vue'),
      meta: { public: true, title: 'Iniciar sesión' },
    },
    {
      path: '/',
      component: () => import('@/components/MainLayout.vue'),
      children: [
        { path: '', redirect: { name: 'dashboard' } },
        {
          path: 'dashboard',
          name: 'dashboard',
          component: () => import('@/components/UserDashboard.vue'),
          meta: { title: 'Dashboard' },
        },
        {
          path: 'pases',
          name: 'pases',
          component: () => import('@/components/PasesView.vue'),
          meta: { title: 'Pases' },
        },
        {
          path: 'reportes',
          name: 'reportes',
          component: () => import('@/components/ReportesView.vue'),
          meta: { title: 'Reportes' },
        },
        {
          path: 'usuarios',
          name: 'usuarios',
          component: () => import('@/components/UsuariosView.vue'),
          meta: { title: 'Usuarios' },
        },
        {
          path: 'auditorias',
          name: 'auditorias',
          component: () => import('@/components/AuditoriaView.vue'),
          meta: { title: 'Auditoría' },
        },
        {
          path: 'gestion-academica',
          name: 'gestion-academica',
          component: () => import('@/components/GestionAcademicaView.vue'),
          meta: { title: 'Gestión Académica' },
        },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
  ],
})

router.beforeEach((to) => {
  const token = localStorage.getItem('token')
  const hasValidToken = Boolean(token) && !isTokenExpired(token)

  // Token vencido: lo limpiamos para no dejar una sesión inválida
  if (token && !hasValidToken) {
    localStorage.removeItem('token')
  }

  // Si la ruta no es pública y no hay token → al login
  if (!to.meta.public && !hasValidToken) {
    return { name: 'Login', query: { redirect: to.fullPath } }
  }

  // Si ya está logueado y va a /login → al dashboard
  if (to.meta.public && hasValidToken) {
    return { name: 'dashboard' }
  }
})

router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} · ${APP_NAME}` : APP_NAME
})

export default router
