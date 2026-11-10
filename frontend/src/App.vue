<script setup lang="ts">
import UserMenu from "./components/UserMenu.vue";
</script>

<template>
  <div class="relative min-h-screen bg-slate-950 text-slate-100">
    <img
      src="/cover.png"
      alt=""
      class="fixed inset-0 h-full w-full object-cover"
    />
    <div class="fixed inset-0 bg-slate-950/50"></div>
    <div class="relative flex min-h-screen flex-col">
      <header class="flex items-start justify-between px-6 py-5">
        <RouterLink to="/" class="inline-block">
          <img src="/medieval-shield.svg" alt="ESO Wizard home" class="h-12 w-12" />
        </RouterLink>
        <UserMenu />
      </header>
      <main class="mx-auto w-full max-w-4xl flex-1 px-6 py-12">
        <RouterView />
      </main>
    </div>
  </div>
</template>
