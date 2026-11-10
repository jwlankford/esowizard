<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import { useAskStore } from "./stores/ask";

const store = useAskStore();
const open = ref(window.innerWidth >= 768);

function closeOnMobile() {
  if (window.innerWidth < 768) open.value = false;
}

function newChat() {
  store.newChat();
  closeOnMobile();
}

function select(id: number) {
  store.select(id);
  closeOnMobile();
}

const menuOpen = ref(false);
const userMenu = ref<HTMLElement | null>(null);

function clearChats() {
  store.clearAll();
  menuOpen.value = false;
}

function onDocumentClick(event: MouseEvent) {
  if (menuOpen.value && !userMenu.value?.contains(event.target as Node)) {
    menuOpen.value = false;
  }
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === "Escape") menuOpen.value = false;
}

onMounted(() => {
  document.addEventListener("click", onDocumentClick);
  document.addEventListener("keydown", onKeydown);
});

onBeforeUnmount(() => {
  document.removeEventListener("click", onDocumentClick);
  document.removeEventListener("keydown", onKeydown);
});
</script>

<template>
  <div
    class="relative flex h-screen overflow-hidden bg-slate-950 bg-cover bg-center bg-no-repeat text-slate-100"
    style="background-image: url(&quot;/cover.png&quot;)"
  >
    <div
      v-if="open"
      class="absolute inset-0 z-10 bg-black/50 md:hidden"
      @click="open = false"
    />
    <aside
      class="absolute inset-y-0 left-0 z-20 flex w-72 flex-col border-r border-slate-800 bg-slate-950/90 backdrop-blur transition-transform duration-300 md:static md:shrink-0 md:transition-[margin]"
      :class="open ? 'translate-x-0 md:ml-0' : '-translate-x-full md:-ml-72'"
      aria-label="Chat history"
    >
      <div class="flex items-center justify-between p-3">
        <span class="px-2 text-lg font-semibold text-amber-300"
          >ESO Wizard</span
        >
        <button
          class="rounded-lg p-2 hover:bg-slate-800"
          aria-label="Close menu"
          @click="open = false"
        >
          ✕
        </button>
      </div>
      <div class="px-3">
        <button
          class="w-full rounded-lg border border-slate-700 px-3 py-2 text-left hover:bg-slate-800"
          @click="newChat"
        >
          + New chat
        </button>
      </div>
      <nav class="mt-4 flex-1 overflow-y-auto px-3 pb-3">
        <p
          v-if="!store.conversations.length"
          class="px-2 text-sm text-slate-500"
        >
          No conversations yet.
        </p>
        <button
          v-for="chat in store.conversations"
          :key="chat.id"
          class="mb-1 block w-full truncate rounded-lg px-3 py-2 text-left text-sm hover:bg-slate-800"
          :class="{ 'bg-slate-800': chat.id === store.activeId }"
          @click="select(chat.id)"
        >
          {{ chat.title }}
        </button>
      </nav>
      <div ref="userMenu" class="relative border-t border-slate-800 p-3">
        <div
          v-if="menuOpen"
          class="absolute inset-x-3 bottom-full mb-2 rounded-xl border border-slate-700 bg-slate-900 p-1 shadow-lg"
          role="menu"
        >
          <button
            class="block w-full rounded-lg px-3 py-2 text-left text-sm text-slate-500"
            role="menuitem"
            disabled
          >
            Settings (coming soon)
          </button>
          <button
            class="block w-full rounded-lg px-3 py-2 text-left text-sm hover:bg-slate-800"
            role="menuitem"
            @click="clearChats"
          >
            Clear chats
          </button>
          <hr class="my-1 border-slate-700" />
          <button
            class="block w-full rounded-lg px-3 py-2 text-left text-sm text-slate-500"
            role="menuitem"
            disabled
          >
            Sign in (coming soon)
          </button>
        </div>
        <button
          class="flex w-full items-center gap-3 rounded-lg p-2 text-left hover:bg-slate-800"
          aria-haspopup="menu"
          :aria-expanded="menuOpen"
          @click="menuOpen = !menuOpen"
        >
          <span
            class="flex h-8 w-8 items-center justify-center rounded-full bg-amber-300 font-semibold text-slate-950"
            aria-hidden="true"
            >G</span
          >
          <span class="flex-1 truncate text-sm">Guest</span>
          <span aria-hidden="true" class="text-slate-400">⋯</span>
        </button>
      </div>
    </aside>

    <div class="flex min-w-0 flex-1 flex-col">
      <header class="flex items-center gap-3 p-3">
        <button
          v-if="!open"
          class="rounded-lg bg-slate-950/70 p-2 hover:bg-slate-800"
          aria-label="Open menu"
          @click="open = true"
        >
          ☰
        </button>
        <span v-if="!open" class="font-semibold text-amber-300"
          >ESO Wizard</span
        >
      </header>
      <RouterView />
    </div>
  </div>
</template>
