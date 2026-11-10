<script setup lang="ts">
import { ref } from "vue";
import UserMenu from "./components/UserMenu.vue";
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
</script>

<template>
  <div class="relative h-dvh overflow-hidden bg-slate-950 text-slate-100">
    <img
      src="/cover.png"
      alt=""
      class="fixed inset-0 h-full w-full object-cover"
    />
    <div class="fixed inset-0 bg-slate-950/50"></div>
    <div class="relative flex h-full">
      <div
        v-if="open"
        class="absolute inset-0 z-10 bg-black/50 md:hidden"
        @click="open = false"
      />
      <aside
        class="absolute inset-y-0 left-0 z-20 flex w-72 flex-col border-r border-slate-800 bg-slate-950/90 backdrop-blur transition-transform duration-300 md:static md:shrink-0 md:transition-[margin]"
        :class="open ? 'translate-x-0 md:ml-0' : '-translate-x-full md:-ml-72'"
        :inert="!open"
        aria-label="Chat history"
      >
        <div class="flex items-center justify-between p-3">
          <RouterLink to="/" class="inline-block">
            <img
              src="/medieval-shield.svg"
              alt="ESO Wizard home"
              class="h-10 w-10"
            />
          </RouterLink>
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
        <div class="border-t border-slate-800 p-3">
          <UserMenu drop-up />
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
        </header>
        <RouterView />
      </div>
    </div>
  </div>
</template>
