import { createRouter, createWebHistory } from 'vue-router'
import {
  sincronizarSesion,
  puedeAccederRuta,
  rutaInicio,
} from '@/services/auth'

const APP_NAME = 'Control de Pases'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/LoginView.vue'),
      meta: { public: true, title: 'Iniciar sesión' },
    },
    {
      path: '/',
      component: () => import('@/components/layout/MainLayout.vue'),
      children: [
        { path: '', redirect: { name: 'dashboard' } },
        {
          path: 'dashboard',
          name: 'dashboard',
          component: () => import('@/views/UserDashboard.vue'),
          meta: { title: 'Dashboard' },
        },
        {
          path: 'pases',
          name: 'pases',
          component: () => import('@/views/PasesView.vue'),
          meta: { title: 'Pases' },
        },
        {
          path: 'reportes',
          name: 'reportes',
          component: () => import('@/views/ReportesView.vue'),
          meta: { title: 'Reportes' },
        },
        {
          path: 'usuarios',
          name: 'usuarios',
          component: () => import('@/views/UsuariosView.vue'),
          meta: { title: 'Usuarios' },
        },
        {
          path: 'auditorias',
          name: 'auditorias',
          component: () => import('@/views/AuditoriaView.vue'),
          meta: { title: 'Auditoría' },
        },
        {
          path: 'gestion-academica',
          name: 'gestion-academica',
          component: () => import('@/views/GestionAcademicaView.vue'),
          meta: { title: 'Gestión Académica' },
        },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
  ],
})

router.beforeEach((to) => {
  // Lee el JWT (rol y nivel) y descarta tokens vencidos.
  const usuario = sincronizarSesion()

  // Si la ruta no es pública y no hay sesión válida → al login
  if (!to.meta.public && !usuario) {
    return { name: 'Login', query: { redirect: to.fullPath } }
  }

  // Si ya está logueado y va a /login → a su inicio
  if (to.meta.public && usuario) {
    return { name: rutaInicio() }
  }

  // Enlaces ocultos para el rol tampoco se pueden abrir escribiendo la URL.
  if (!to.meta.public && !puedeAccederRuta(to.name)) {
    return { name: rutaInicio() }
  }
})

router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} · ${APP_NAME}` : APP_NAME
})

export default router
