<script setup>
import { ref, reactive, computed, watch, onBeforeUnmount } from "vue";

const props = defineProps({
  docenteActual: { type: String, default: "" },
});

// ───────────── Helpers de fecha / formato ─────────────
const pad = (n) => String(n).padStart(2, "0");
const hoyISO = () => {
  const d = new Date();
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
};
const horaActual = () => {
  const d = new Date();
  return `${pad(d.getHours())}:${pad(d.getMinutes())}`;
};
const mesActual = () => hoyISO().slice(0, 7);
const fmtFecha = (iso) => iso.split("-").reverse().join("/");
const fmtCedula = (c) => "V-" + c.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
const nombreCompleto = (e) => `${e.nombre} ${e.apellido}`;

// ───────────── Catálogos ─────────────
const tipos = ["Entrada", "Salida"];
const motivos = [
  "Retardo",
  "Malestar de salud",
  "Retirado por representante",
  "Permiso por uniforme (zapatos)",
];
const LIMITE_RETARDOS = 3;

// ─────────────────────────────────────────────────────────────
// DATOS DE EJEMPLO REDUCIDOS (Solo 3 registros limpios)
// ─────────────────────────────────────────────────────────────
const estudiantes = [
  {
    id: 1,
    cedula: "31458920",
    nombre: "Santiago",
    apellido: "Morales Vega",
    anio: "4to Año",
    representante: { nombre: "Elena Vega de Morales", parentesco: "Madre", cedula: "12345678", telefono: "0414-555-0192" },
  },
  {
    id: 2,
    cedula: "32102391",
    nombre: "Gabriel",
    apellido: "Rivas Peña",
    anio: "2do Año",
    representante: { nombre: "Luis Rivas", parentesco: "Padre", cedula: "14222333", telefono: "0412-555-0148" },
  },
  {
    id: 3,
    cedula: "30884102",
    nombre: "Valentina",
    apellido: "Gómez Ruiz",
    anio: "5to Año",
    representante: { nombre: "Marta Ruiz", parentesco: "Madre", cedula: "13555666", telefono: "0424-555-0177" },
  }
];

const m = mesActual();
const pases = ref([
  { id: 1, estudianteId: 1, fecha: `${m}-02`, hora: "07:38", tipo: "Entrada", motivo: "Retardo", autorizadoPor: "Coordinación", docente: "Prof. Miriam Soto", anio: "4to Año" },
  { id: 2, estudianteId: 1, fecha: `${m}-03`, hora: "11:20", tipo: "Salida", motivo: "Malestar de salud", autorizadoPor: "Dirección", docente: "Lic. Carlos Méndez", anio: "4to Año" },
  { id: 3, estudianteId: 2, fecha: `${m}-02`, hora: "07:41", tipo: "Entrada", motivo: "Retardo", autorizadoPor: "Coordinación", docente: "Prof. Luis Pérez", anio: "2do Año" }
]);
const nextId = () => Math.max(0, ...pases.value.map((p) => p.id)) + 1;
const estudiantePorId = (id) => estudiantes.find((e) => e.id === id);

// ═════════════ SECCIÓN 1: Búsqueda y formulario ═════════════
const cedulaBusqueda = ref("");
const estudiante = ref(null);
const error = ref("");
const exito = ref("");
let temporizador = null;

const form = reactive({
  tipo: "Entrada",
  motivo: "",
  autorizadoPor: "",
  docente: props.docenteActual,
  fecha: hoyISO(),
  hora: horaActual(),
});
watch(() => props.docenteActual, (v) => { if (!form.docente) form.docente = v; });

const ahora = () => {
  form.fecha = hoyISO();
  form.hora = horaActual();
};

const buscar = () => {
  error.value = "";
  exito.value = "";
  const q = cedulaBusqueda.value.replace(/\D/g, "");
  if (!q) {
    error.value = "Escribe la cédula del estudiante.";
    return;
  }
  const e = estudiantes.find((x) => x.cedula === q);
  if (!e) {
    estudiante.value = null;
    error.value = "No se encontró ningún estudiante con esa cédula.";
    return;
  }
  estudiante.value = e;
  ahora();
};

const reiniciarFormulario = () => {
  form.tipo = "Entrada";
  form.motivo = "";
  form.autorizadoPor = "";
  ahora();
};

const nuevaBusqueda = () => {
  cedulaBusqueda.value = "";
  estudiante.value = null;
  error.value = "";
  exito.value = "";
  reiniciarFormulario();
};

const registrar = () => {
  if (!estudiante.value) return;
  const nuevo = {
    id: nextId(),
    estudianteId: estudiante.value.id,
    fecha: form.fecha,
    hora: form.hora,
    tipo: form.tipo,
    motivo: form.motivo,
    autorizadoPor: form.autorizadoPor.trim(),
    docente: form.docente.trim(),
    anio: estudiante.value.anio,
  };
  pases.value.unshift(nuevo);
  exito.value = `Pase registrado para ${nombreCompleto(estudiante.value)}.`;
  clearTimeout(temporizador);
  temporizador = setTimeout(() => (exito.value = ""), 5000);
  reiniciarFormulario();
};
onBeforeUnmount(() => clearTimeout(temporizador));

// ═════════════ SECCIÓN 2: Lógica ═════════════
const ordenarReciente = (a, b) => (b.fecha + b.hora).localeCompare(a.fecha + a.hora);
const pasesEstudiante = computed(() => estudiante.value ? pases.value.filter((p) => p.estudianteId === estudiante.value.id).sort(ordenarReciente) : []);
const retardosMes = computed(() => pasesEstudiante.value.filter((p) => p.tipo === "Entrada" && p.motivo === "Retardo" && p.fecha.startsWith(mesActual())).length);
const nivel = computed(() => retardosMes.value >= LIMITE_RETARDOS ? "bad" : retardosMes.value === LIMITE_RETARDOS - 1 ? "warn" : "ok");
const nivelCls = { ok: "bg-[#ccd5ae] text-[#233E47]", warn: "bg-[#fdebc0] text-[#6b4200]", bad: "bg-[#fbd5d2] text-[#8a1c14]" };

// ═════════════ SECCIÓN 3: Historial ═════════════
const q = ref("");
const fTipo = ref("");
const fMotivo = ref("");
const pagina = ref(1);
const porPagina = 8;

const historial = computed(() => {
  const t = q.value.trim().toLowerCase();
  return pases.value
    .filter((p) => {
      const e = estudiantePorId(p.estudianteId);
      const texto = `${nombreCompleto(e)} ${e.cedula}`.toLowerCase();
      return ((!t || texto.includes(t)) && (!fTipo.value || p.tipo === fTipo.value) && (!fMotivo.value || p.motivo === fMotivo.value));
    }).sort(ordenarReciente);
});
const totalPaginas = computed(() => Math.max(1, Math.ceil(historial.value.length / porPagina)));
const historialPagina = computed(() => historial.value.slice((pagina.value - 1) * porPagina, pagina.value * porPagina));
watch([q, fTipo, fMotivo], () => (pagina.value = 1));

// ───────────── Clases reutilizables ─────────────
const inp = "h-11 w-full rounded-xl border border-[#b8c2d3] bg-white px-3 text-[15px] text-[#1b2a2f] placeholder:text-[#5b6a72] transition focus:border-[#233E47] focus:outline-none focus:ring-4 focus:ring-[#b4d0f8]/70 disabled:cursor-not-allowed disabled:bg-[#f1f4f0]";
const ro = "h-11 w-full rounded-xl border border-[#dbe2d0] bg-[#f1f4f0] px-3 text-[15px] font-semibold text-[#233E47]";
const chip = "flex min-h-11 cursor-pointer items-center justify-center rounded-xl border border-[#b8c2d3] bg-white px-4 py-2 text-center text-sm font-semibold text-[#233E47] transition hover:bg-[#eef3fb] peer-checked:border-[#233E47] peer-checked:bg-[#233E47] peer-checked:text-white peer-focus-visible:ring-4 peer-focus-visible:ring-[#b4d0f8]";
const lbl = "text-sm font-semibold text-[#233E47]";
const card = "rounded-2xl border border-[#d5dbe6] bg-white p-5 shadow-sm md:p-6 w-full";
const btnP = "inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-[#233E47] px-5 text-[15px] font-bold text-white transition hover:bg-[#1a2f36] focus-visible:outline focus-visible:outline-[3px] focus-visible:outline-offset-2 focus-visible:outline-[#91a5c9] disabled:cursor-not-allowed disabled:opacity-50";
const btnS = "inline-flex h-11 items-center justify-center gap-2 rounded-xl border border-[#233E47] bg-white px-5 text-[15px] font-bold text-[#233E47] transition hover:bg-[#eef3fb] focus-visible:outline focus-visible:outline-[3px] focus-visible:outline-offset-2 focus-visible:outline-[#91a5c9]";
const th = "whitespace-nowrap bg-[#eef2f6] px-3 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-[#4a5a63]";
const td = "whitespace-nowrap border-t border-[#e3e8ee] px-3 py-2.5 text-sm text-[#1b2a2f]";
const tipoCls = (t) => t === "Entrada" ? "bg-[#ccd5ae] text-[#233E47]" : "bg-[#b4d0f8] text-[#233E47]";
</script>

<template>
  <div class="mx-auto flex w-full max-w-[1320px] flex-col gap-6 font-sans text-[#1b2a2f]">
    
    <!-- CONTENEDOR FLEX CORREGIDO: flex-col en móviles, xl:flex-row en escritorio grande, y items-start para evitar el estiramiento vertical -->
    <div class="flex flex-col gap-6 xl:flex-row xl:items-start">
      
      <!-- ═══════════ SECCIÓN 1: Buscar estudiante y registrar pase ═══════════ -->
      <section :class="[card, 'xl:w-1/2']" aria-labelledby="t1">
        <header class="mb-5 flex items-center gap-3">
          <span class="grid h-9 w-9 place-items-center rounded-full bg-[#233E47] text-sm font-bold text-white">1</span>
          <div>
            <h2 id="t1" class="text-xl font-bold text-[#233E47]">Registrar pase</h2>
            <p class="text-sm text-[#4a5a63]">Busca al estudiante por cédula y completa los datos del pase.</p>
          </div>
        </header>

        <form @submit.prevent="buscar" class="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div class="flex-1">
            <label for="cedula" :class="lbl">Cédula del estudiante</label>
            <div class="relative mt-1.5">
              <svg aria-hidden="true" class="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-[#5b6a72]" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="11" cy="11" r="7" /><path d="M20 20l-3.5-3.5" />
              </svg>
              <input v-model="cedulaBusqueda" id="cedula" type="text" inputmode="numeric" autocomplete="off" autofocus placeholder="Ej. 31458920" class="h-12 w-full rounded-xl border-2 border-[#233E47] bg-white pl-11 pr-4 text-lg font-medium placeholder:text-[#5b6a72] focus:outline-none focus:ring-4 focus:ring-[#b4d0f8]/70"/>
            </div>
          </div>
          <div class="flex gap-2">
            <button type="submit" :class="btnP" class="!h-12">Buscar</button>
            <button v-if="estudiante || cedulaBusqueda" type="button" @click="nuevaBusqueda" :class="btnS" class="!h-12">Limpiar</button>
          </div>
        </form>

        <p v-if="error" role="alert" class="mt-3 rounded-xl bg-[#fbd5d2] px-4 py-3 text-sm font-semibold text-[#8a1c14]">{{ error }}</p>
        <p v-if="exito" role="status" class="mt-3 rounded-xl bg-[#ccd5ae] px-4 py-3 text-sm font-semibold text-[#233E47]">✔ {{ exito }}</p>

        <div v-if="estudiante && nivel === 'bad'" role="alert" class="mt-3 flex items-center gap-3 rounded-xl bg-[#b42318] px-4 py-3 text-white">
          <svg aria-hidden="true" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="9" /><path d="M5.6 5.6l12.8 12.8" />
          </svg>
          <p><b class="block text-lg">NO PUEDE INGRESAR</b><span class="text-sm">Acumula {{ retardosMes }} retardos este mes. Remitir a coordinación.</span></p>
        </div>
        <div v-else-if="estudiante && nivel === 'warn'" class="mt-3 rounded-xl bg-[#fdebc0] px-4 py-3 text-sm font-semibold text-[#6b4200]">
          Advertencia: lleva {{ retardosMes }} retardos este mes. Con el próximo alcanzará el límite de {{ LIMITE_RETARDOS }}.
        </div>

        <form @submit.prevent="registrar" class="mt-6">
          <fieldset :disabled="!estudiante" class="flex flex-col gap-5 disabled:opacity-60">
            <legend class="sr-only">Datos del pase</legend>
            <div class="grid gap-4 md:grid-cols-2">
              <div>
                <label for="nombre" :class="lbl">Nombre y apellido del estudiante</label>
                <input id="nombre" :value="estudiante ? nombreCompleto(estudiante) : ''" placeholder="Se completa al buscar" readonly :class="[ro, 'mt-1.5']"/>
              </div>
              <div>
                <label for="anio" :class="lbl">Año (grado)</label>
                <input id="anio" :value="estudiante ? estudiante.anio : ''" placeholder="—" readonly :class="[ro, 'mt-1.5']"/>
              </div>
            </div>

            <div class="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
              <fieldset>
                <legend :class="lbl">Tipo</legend>
                <div class="mt-1.5 grid grid-cols-2 gap-2">
                  <label v-for="t in tipos" :key="t" class="relative">
                    <input type="radio" name="tipo" :value="t" v-model="form.tipo" class="peer sr-only" required/>
                    <span :class="chip">{{ t }}</span>
                  </label>
                </div>
              </fieldset>
              <fieldset>
                <legend :class="lbl">Motivo</legend>
                <div class="mt-1.5 grid grid-cols-1 gap-2 sm:grid-cols-2">
                  <label v-for="mo in motivos" :key="mo" class="relative">
                    <input type="radio" name="motivo" :value="mo" v-model="form.motivo" class="peer sr-only" required/>
                    <span :class="chip">{{ mo }}</span>
                  </label>
                </div>
              </fieldset>
            </div>

            <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <div>
                <label for="autoriza" :class="lbl">Autorizado por</label>
                <input v-model="form.autorizadoPor" id="autoriza" list="autoridades" placeholder="Ej. Coordinación" required :class="[inp, 'mt-1.5']"/>
                <datalist id="autoridades"><option value="Coordinación" /><option value="Dirección" /><option value="Control de estudios" /></datalist>
              </div>
              <div>
                <label for="docente" :class="lbl">Docente</label>
                <input v-model="form.docente" id="docente" placeholder="Nombre del docente" required :class="[inp, 'mt-1.5']"/>
              </div>
              <div>
                <label for="fecha" :class="lbl">Fecha</label>
                <input v-model="form.fecha" id="fecha" type="date" required :class="[inp, 'mt-1.5']"/>
              </div>
              <div>
                <label for="hora" :class="lbl">Hora</label>
                <input v-model="form.hora" id="hora" type="time" required :class="[inp, 'mt-1.5']"/>
              </div>
            </div>

            <div class="flex flex-wrap gap-3">
              <button type="submit" :class="btnP">
                <svg aria-hidden="true" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M5 12l5 5L20 7" />
                </svg>
                Registrar pase
              </button>
              <button type="button" @click="reiniciarFormulario" :class="btnS">Limpiar datos</button>
            </div>
          </fieldset>
        </form>
      </section>

      <!-- ═══════════ SECCIÓN 2: Pases del estudiante + representante ═══════════ -->
      <section :class="[card, 'xl:w-1/2']" aria-labelledby="t2">
        <header class="mb-5 flex flex-wrap items-center justify-between gap-3">
          <div class="flex items-center gap-3">
            <span class="grid h-9 w-9 place-items-center rounded-full bg-[#233E47] text-sm font-bold text-white">2</span>
            <div>
              <h2 id="t2" class="text-xl font-bold text-[#233E47]">Pases del estudiante y representante</h2>
              <p v-if="estudiante" class="text-sm text-[#4a5a63]">{{ nombreCompleto(estudiante) }} · {{ fmtCedula(estudiante.cedula) }} · {{ estudiante.anio }}</p>
            </div>
          </div>
          <span v-if="estudiante" :class="['rounded-full px-3 py-1 text-sm font-bold', nivelCls[nivel]]">
            Retardos este mes: {{ retardosMes }} de {{ LIMITE_RETARDOS }}
          </span>
        </header>

        <div v-if="!estudiante" class="flex flex-col items-center gap-2 rounded-xl bg-[#f3f6f1] px-4 py-12 text-center text-[#4a5a63]">
          <svg aria-hidden="true" width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="#91a5c9" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="8" r="4" /><path d="M4 21c0-4 4-6 8-6s8 2 8 6" />
          </svg>
          <p class="font-semibold text-[#233E47]">Aún no hay un estudiante seleccionado</p>
          <p class="text-sm">Busca por cédula para ver sus pases y los datos de su representante.</p>
        </div>

        <div v-else class="flex flex-col gap-5">
          <!-- Pases del estudiante -->
          <div class="min-w-0">
            <h3 class="mb-2 text-base font-bold text-[#233E47]">Pases registrados ({{ pasesEstudiante.length }})</h3>
            <div v-if="pasesEstudiante.length" class="max-h-[220px] overflow-auto rounded-xl border border-[#e3e8ee]">
              <table class="w-full border-collapse">
                <thead class="sticky top-0 z-10">
                  <tr>
                    <th :class="th">Fecha</th><th :class="th">Hora</th><th :class="th">Tipo</th><th :class="th">Motivo</th><th :class="th">Docente</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="p in pasesEstudiante" :key="p.id">
                    <td :class="td">{{ fmtFecha(p.fecha) }}</td>
                    <td :class="td">{{ p.hora }}</td>
                    <td :class="td"><span :class="['rounded-full px-2.5 py-0.5 text-xs font-bold', tipoCls(p.tipo)]">{{ p.tipo }}</span></td>
                    <td :class="td">{{ p.motivo }}</td>
                    <td :class="td">{{ p.docente }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p v-else class="rounded-xl bg-[#f3f6f1] px-4 py-8 text-center text-sm text-[#4a5a63]">Este estudiante aún no tiene pases registrados.</p>
          </div>

          <!-- Representante: Limpiado a solo Cédula y Teléfono -->
          <aside class="rounded-xl border border-[#d5dbe6] bg-[#f6f9fe] p-5">
            <h3 class="mb-3 text-base font-bold text-[#233E47]">Representante</h3>
            <div class="flex items-center gap-3">
              <span class="grid h-14 w-14 flex-none place-items-center rounded-full bg-[#b4d0f8] text-lg font-bold text-[#233E47]">
                {{ estudiante.representante.nombre.split(" ").slice(0, 2).map((x) => x[0]).join("") }}
              </span>
              <div>
                <p class="font-bold text-[#1b2a2f]">{{ estudiante.representante.nombre }}</p>
                <span class="mt-0.5 inline-block rounded-full bg-[#ccd5ae] px-2.5 py-0.5 text-xs font-bold text-[#233E47]">{{ estudiante.representante.parentesco }}</span>
              </div>
            </div>
            <dl class="mt-4 grid grid-cols-2 gap-4 text-sm">
              <div>
                <dt class="text-xs font-semibold uppercase tracking-wide text-[#4a5a63]">Cédula</dt>
                <dd class="mt-1">{{ fmtCedula(estudiante.representante.cedula) }}</dd>
              </div>
              <div>
                <dt class="text-xs font-semibold uppercase tracking-wide text-[#4a5a63]">Teléfono</dt>
                <dd class="mt-1">{{ estudiante.representante.telefono }}</dd>
              </div>
            </dl>
            <a :href="'tel:' + estudiante.representante.telefono" :class="[btnS, 'mt-4 w-full']">
              <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 1.9.7 2.8a2 2 0 0 1-.5 2.1L8 9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.8.7a2 2 0 0 1 1.7 2z" />
              </svg>
              Llamar
            </a>
          </aside>
        </div>
      </section>
    </div>

    <!-- ═══════════ SECCIÓN 3: Historial completo ═══════════ -->
    <section :class="card" aria-labelledby="t3">
      <header class="mb-5 flex items-center gap-3">
        <span class="grid h-9 w-9 place-items-center rounded-full bg-[#233E47] text-sm font-bold text-white">3</span>
        <div>
          <h2 id="t3" class="text-xl font-bold text-[#233E47]">Historial de pases</h2>
          <p class="text-sm text-[#4a5a63]">{{ historial.length }} pases registrados</p>
        </div>
      </header>

      <div class="mb-4 grid gap-3 md:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_minmax(0,1.3fr)]">
        <input v-model="q" type="search" aria-label="Buscar por estudiante o cédula" placeholder="Buscar por estudiante o cédula" :class="inp" />
        <select v-model="fTipo" aria-label="Filtrar por tipo" :class="inp">
          <option value="">Todos los tipos</option>
          <option v-for="t in tipos" :key="t" :value="t">{{ t }}</option>
        </select>
        <select v-model="fMotivo" aria-label="Filtrar por motivo" :class="inp">
          <option value="">Todos los motivos</option>
          <option v-for="mo in motivos" :key="mo" :value="mo">{{ mo }}</option>
        </select>
      </div>

      <div class="overflow-x-auto rounded-xl border border-[#e3e8ee]">
        <table class="w-full border-collapse">
          <thead>
            <tr>
              <th :class="th">Fecha</th><th :class="th">Hora</th><th :class="th">Estudiante</th><th :class="th">Año</th><th :class="th">Motivo</th><th :class="th">Registrado por (docente)</th><th :class="th">Tipo</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in historialPagina" :key="p.id" class="hover:bg-[#f6f9fe]">
              <td :class="td">{{ fmtFecha(p.fecha) }}</td>
              <td :class="td">{{ p.hora }}</td>
              <td :class="[td, 'font-semibold']">{{ nombreCompleto(estudiantePorId(p.estudianteId)) }}</td>
              <td :class="td">{{ p.anio }}</td>
              <td :class="td">{{ p.motivo }}</td>
              <td :class="td">{{ p.docente }}</td>
              <td :class="td"><span :class="['rounded-full px-2.5 py-0.5 text-xs font-bold', tipoCls(p.tipo)]">{{ p.tipo }}</span></td>
            </tr>
            <tr v-if="!historialPagina.length">
              <td colspan="7" class="px-4 py-10 text-center text-sm text-[#4a5a63]">No hay pases que coincidan con los filtros.</td>
            </tr>
          </tbody>
        </table>
      </div>
      <footer class="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm text-[#4a5a63]">
        <span>Página {{ pagina }} de {{ totalPaginas }}</span>
        <div class="flex gap-2">
          <button type="button" :class="btnS" class="!h-10 !px-4" :disabled="pagina === 1" @click="pagina--">Anterior</button>
          <button type="button" :class="btnS" class="!h-10 !px-4" :disabled="pagina === totalPaginas" @click="pagina++">Siguiente</button>
        </div>
      </footer>
    </section>
  </div>
</template>