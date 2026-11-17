<script setup>
import {ref} from 'vue'
//Constante que permita mostrar u ocultar el formulario para agregar un nuevo usuario
const mostrarForm=ref(false)

</script>

<template>
    <div class="p-6 bg-white w-full h-full">

    </div>

    <!--Contenedor de la Informacion de los usuarios en el sistema-->
    <div class="flex-1 border-2 border-slate-800 rounded-3xl p-6">
        <div class="flex flex-wrap items-end gap-4 mb-6">
                <div class="flex-1 min-w-[150px]">
                    <label class="block text-xs font-semibold text-slate-600 mb-1">Buscar</label>
                    <input type="text" class="w-full- px-3 py-1.5 border-2 border-slate-800 
                    rounded-lg outline-none focus:bg-slate-50">
                </div>

                <div class="flex-1 min-w-[120px]">
                    <label class="block text-xs font-semibold text-slate-600 mb-1">Rol</label>
                    <select class="w-full px-3 py-1.5 border-2 border-slate-800
                    rounded-lg outline-none bg-white">
                    
                    <option value=""></option>
                    <option value="Admin">Administrador</option>
                    <option value="Control">Control de Estudio</option>
                    <option value="Secretaria">Secretaría</option>
                    </select>
                    
                </div>
                <button @click="mostrarForm=true"
                 class="px-4 py-1.5 bg-blue-400 text-white font-semibold border-2 border-slate-800
                rounded-lg">Agregar Usuario</button>
        </div>
        
        <div class="w-full border-t-2 border-slate-800 pt-4">
            <table class="w-full text-left text-sm">
                <thead>
                <tr class="text-slate-500 border-b-2 border-slate-200">
                    <th class="py-2 px-2">Usuario</th>
                    <th class="py-2 px-2">Rol</th>
                    <th class="py-2 px-2">Ultima Conexion</th>
                    <th class="py-2 px-2">Acciones</th>
                </tr>
                </thead>

                <tbody>
                    <tr class="border-b border-slate-100 last:border-0">
                        <td class="py-3 px-2 font-medium"></td> <!--Usuarios-->
                        <td class="py-3 px-2"></td> <!--Rol del Usuario-->
                        <td class="py-3 px-2"></td> <!--Ultima Conexion del usuario-->
                        <td class="py-3 px-2">
                            <button class="font-semibold text-slate-700 hover:text-blue-600">Editar</button> 
                            <button class="font-semibold text-slate-700 hover:text-blue-600">Cambiar Clave</button>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>

    <!--Formulario para Agregar un Nuevo Usuario-->
    <div v-if="mostrarForm" class="w-full xl:w-[350px] border-2 border-slate-800 rounded-3xl p-6 h-fit
    animate-fade-in">
    <h3 class="text-md font-semibold text-slate-800 mb-4">Nuevo Usuario</h3>

    <form class="space-y-4">
        <div>
            <label class="block text-xs font-semibold text-slate-600 mb-1">Usuario</label>
            <input type="text" class="w-full px-3 py-1.5 border-2 border-slate-800 rounded-lg outline-none"/>
        </div>
        <div>
            <label class="block text-xs font-semibold text-slate-600 mb-1">Rol</label>
            <select class="w-full px-3 py-1.5 border-2 border-slate-800 rounded-lg- outline-none bg-white">
                <option value="Admin">Administrador</option>
                <option value="Control">Control de Estudio</option>
                <option value="Secretaria">Secretaría</option>
            </select>
        </div>
        <div>
            <label class="block text-xs font-semibold text-slate-600 mb-1">Contraseña</label>
            <input type="password" class="w-full px-3 py-1.5 border-2 border-slate-800 rounded-lg outline-none">
        </div>
        <div>
            <label class="block text-xs font-semibold text-slate-600 mb-1">Verificar Contraseña</label>
            <input type="password" class="w-full px-3 py-1.5 border-2 border-slate-800 rounded-lg outline-none">
        </div>

        <div class="flex gap-3 pt-2">
            <button type="button"
            @click="mostrarForm=false"
            class="flex-1 py-1.5 bg-white border-2 border-slate-800 rounded-lg font-semibold
            hover:bg-slate50">Cancelar</button>

            <button type="button" class="flex-1 py-1.5 bg-blue-400 text-white border-2 border-slate-800 
            rounded-lg font-semibold">Guardar</button>
        </div>
    </form>

    </div>
</template>

<style scoped>
.animate-fade-in{
    animation: fadeIn 0.3s ease-in-out;
}
@keyframes fadeIn{
    from {opacity:0; transform: translateX(10px);}
    to {opacity:1; transform: translateX(0);}
}

</style>