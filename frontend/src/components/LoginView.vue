<script setup>
import { ref } from 'vue'
// Las imágenes se importan para que Vite resuelva bien la ruta (src/assets/)
import fondo from '../assets/fachada.jpg'
import logo from '../assets/logo santa marta.png'

// 1. Declaración del estado reactivo del componente
const username = ref('')
const password = ref('')

// Variable para controlar la visibilidad de la contraseña
const showPassword = ref(false)

// 2. Función que intercepta el envío del formulario
const handleLogin = () => {
  console.log('Datos listos para enviar a FastAPI:', {
    usuario: username.value,
    clave: password.value,
  })
}
</script>

<template>
  <div class="relative min-h-screen overflow-hidden bg-[#13264d]">
    <!-- Foto de fondo -->
    <img :src="fondo" alt="" class="absolute inset-0 h-full w-full object-cover" />

    <!-- Capa oscura azulada para que la tarjeta y el texto resalten -->
    <div
      aria-hidden="true"
      class="absolute inset-0 bg-gradient-to-b from-[#0b1633]/80 via-[#13264d]/60 to-[#13264d]/70"
    ></div>

    <!-- Logo + nombre (esquina superior izquierda) -->
    <header class="absolute left-0 top-0 z-10 flex items-center gap-3 p-5 md:p-8">
      <img
        :src="logo"
        alt="Escudo de la Unidad Educativa Santa Marta"
        class="h-14 w-14 object-contain drop-shadow-[0_4px_12px_rgba(0,0,0,0.5)] md:h-16 md:w-16"
      />
      <div class="leading-tight text-white drop-shadow-[0_2px_8px_rgba(0,0,0,0.6)]">
        <p class="text-xs font-medium uppercase tracking-[0.18em] text-white/90">
          Unidad Educativa Privada
        </p>
        <p class="text-xl font-bold md:text-2xl">Santa Marta</p>
      </div>
    </header>

    <!-- Tarjeta central -->
    <main
      class="relative z-10 flex min-h-screen flex-col items-center justify-center px-4 pb-10 pt-28"
    >
      <section
        class="relative w-full max-w-[420px] overflow-hidden rounded-3xl bg-white px-7 py-10 shadow-[0_30px_80px_rgba(8,21,65,0.5)] ring-1 ring-white/40 sm:px-10"
      >
        <!-- Franja de color con la paleta -->
        <div
          aria-hidden="true"
          class="absolute inset-x-0 top-0 h-1.5 bg-gradient-to-r from-[#ccd5ae] via-[#91a5c9] to-[#b4d0f8]"
        ></div>

        <form @submit.prevent="handleLogin" class="flex flex-col gap-5">
          <div class="flex flex-col items-center text-center">
            <h1 class="text-[28px] font-bold text-[#1b2a47]">Iniciar sesión</h1>
            <p class="mt-1 text-[15px] text-[#4a5876]">Ingresa con tu usuario asignado</p>
          </div>

          <!-- Usuario -->
          <div class="flex flex-col gap-1.5">
            <label for="usuario" class="text-sm font-semibold text-[#2c4a7a]">Usuario</label>
            <div class="relative">
              <svg
                aria-hidden="true"
                class="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-[#6b7a99]"
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="1.8"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <circle cx="12" cy="8" r="4" />
                <path d="M4 21c0-4 4-6 8-6s8 2 8 6" />
              </svg>
              <input
                v-model="username"
                id="usuario"
                type="text"
                placeholder="Tu usuario"
                autocomplete="username"
                required
                class="h-12 w-full rounded-xl border border-[#c5cee0] bg-[#f5f8fd] pl-11 pr-4 text-base font-medium text-[#1b2a47] transition placeholder:text-[#5b6882] focus:border-[#2c4a7a] focus:bg-white focus:outline-none focus:ring-4 focus:ring-[#b4d0f8]/70"
              />
            </div>
          </div>

          <!-- Contraseña -->
          <div class="flex flex-col gap-1.5">
            <label for="clave" class="text-sm font-semibold text-[#2c4a7a]">Contraseña</label>
            <div class="relative">
              <svg
                aria-hidden="true"
                class="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-[#6b7a99]"
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="1.8"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <rect x="4" y="11" width="16" height="10" rx="2" />
                <path d="M8 11V8a4 4 0 0 1 8 0v3" />
              </svg>
              <input
                v-model="password"
                id="clave"
                :type="showPassword ? 'text' : 'password'"
                placeholder="••••••••"
                autocomplete="current-password"
                required
                class="h-12 w-full rounded-xl border border-[#c5cee0] bg-[#f5f8fd] pl-11 pr-12 text-base font-medium text-[#1b2a47] transition placeholder:text-[#5b6882] focus:border-[#2c4a7a] focus:bg-white focus:outline-none focus:ring-4 focus:ring-[#b4d0f8]/70"
              />

              <!-- Botón para alternar visibilidad -->
              <button
                type="button"
                @click="showPassword = !showPassword"
                :aria-label="showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'"
                :aria-pressed="showPassword"
                class="absolute right-1.5 top-1/2 grid h-10 w-10 -translate-y-1/2 place-items-center rounded-lg text-[#6b7a99] hover:text-[#2c4a7a] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#2c4a7a]"
              >
                <svg
                  v-if="!showPassword"
                  aria-hidden="true"
                  width="22"
                  height="22"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                  <circle cx="12" cy="12" r="3" />
                </svg>
                <svg
                  v-else
                  aria-hidden="true"
                  width="22"
                  height="22"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <path
                    d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"
                  />
                  <line x1="1" y1="1" x2="23" y2="23" />
                </svg>
              </button>
            </div>
          </div>

          <button
            type="submit"
            class="mt-1 h-[52px] rounded-xl bg-[#2c4a7a] text-[17px] font-bold text-white shadow-[0_8px_20px_rgba(44,74,122,0.35)] transition hover:bg-[#233d68] active:scale-[0.99] focus-visible:outline focus-visible:outline-[3px] focus-visible:outline-offset-[3px] focus-visible:outline-[#91a5c9]"
          >
            Ingresar
          </button>

          <p class="text-center text-[13.5px] leading-relaxed text-[#4a5876]">
            ¿Olvidaste tu contraseña?
            <a href="#" class="font-bold text-[#2c4a7a] hover:underline"
              >Contacta al administrador</a
            >
          </p>
        </form>
      </section>

      <!-- <p class="mt-6 text-center text-sm text-white/90 drop-shadow-[0_1px_4px_rgba(0,0,0,0.6)]">Acceso solo desde la red del colegio</p> -->
    </main>
  </div>
</template>
