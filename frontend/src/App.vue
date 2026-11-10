<template>
  <div class="min-h-screen bg-slate-950 text-slate-100">
    <header class="border-b border-slate-800">
      <div class="mx-auto max-w-4xl px-6 py-5">
        <RouterLink to="/" class="text-xl font-semibold text-amber-300"
          >ESO Wizard</RouterLink
        >
      </div>
    </header>
    <main class="mx-auto max-w-4xl px-6 py-12">
      <RouterView />
    </main>
  </div>
</template>
