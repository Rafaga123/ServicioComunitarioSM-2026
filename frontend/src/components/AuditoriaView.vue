<script>
</script>

<template>
    <div class="p-6 bg-white w-full h-full  ">
        <div class="border-2 border-slate-800 rounded-3xl p-6">
            <div class="flex flex-wrap items-end gap-4 mb-6">
                <div class="flex-1 min-w-[120px]">
                    <label class="block text-xs font-semibold text-slate-600 mb-1">Usuario</label>
                    <input type="text" class="w-full px-3 py-1.5 border-2 border-slate-800 rounded-lg outline-none">
                </div>

                <div class="flex-1 min-w-[120px]">
                    <label class="block text-xs font-semibold text-slate-600 mb-1">Acción</label>
                    <input type="text" class="w-full px-3 py-1.5 border-2 border-slate-800 rounded-lg outline-none">
                </div>
                <div class="flex-1 min-w-[120px]">
                    <label class="block text-xs font-semibold text-slate-600 mb-1">Módulo</label>
                    <input type="text" class="w-full px-3 py-1.5 border-2 border-slate-800 rounded-lg outline-none">
                </div>
                <div class="flex-[2] min-w-[200px]">
                    <label class="block text-xs font-semibold text-slate-600 mb-1">Rango de fechas</label>
                    <input type="text" class="w-full px-3 py-1.5 border-2 border-slate-800 rounded-lg outline-none">
                </div>
                <button class="px-6 py-1.5 bg-white border-2 border-slate-800 rounded-lg font-semibold
                hover:bg-slate-50 transition-colors">Exportar</button>
            </div>

            <div class="w-full border-t-2 border-slate-800 pt-4">
                <table class="w-full text-left text-sm">
                    <thead>
                        <tr class="text-slate-500 border-b-2 border-slate-200">
                            <th class="py-2 px-2">Fecha</th>
                            <th class="py-2 px-2">Usuario</th>
                            <th class="py-2 px-2">Acción</th>
                            <th class="py-2 px-2">Módulo</th>
                            <th class="py-2 px-2">Detalle</th>
                        </tr>
                    </thead>

                    <tbody>
                        <tr class="border-b border-slate-100 last:border-0">
                            <td class="py-3 px-2 font-medium"></td> <!--Fecha de realizacion de Accion-->
                            <td class="py-3 px-2"></td> <!--Nombre de Usuario-->
                            <td class="py-3 px-2"></td> <!--Accion realizada por el usuario-->
                            <td class="py-3 px-2"></td> <!--Modulo afectado en el cambio-->
                            <td class="py-3 px-2 text-slate-600 text-xs"></td> <!--Detalles del cambio Realizado-->
                        </tr>
                    </tbody>
                </table>

            </div>
        </div>
    </div>
</template>