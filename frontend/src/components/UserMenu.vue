<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import SignInModal from "./SignInModal.vue";

defineProps<{ dropUp?: boolean }>();

const open = ref(false);
const signInOpen = ref(false);
const root = ref<HTMLElement | null>(null);
const trigger = ref<HTMLButtonElement | null>(null);

const items = ["Sign in", "Create account", "Profile", "Settings", "Sign out"];

function select(item: string) {
  open.value = false;
  if (item === "Sign in") signInOpen.value = true;
}

async function closeSignIn() {
  signInOpen.value = false;
  await nextTick();
  trigger.value?.focus();
}

function onDocumentClick(event: MouseEvent) {
  if (root.value && !root.value.contains(event.target as Node)) {
    open.value = false;
  }
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === "Escape" && open.value) {
    open.value = false;
    trigger.value?.focus();
  }
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
  <div ref="root" class="relative">
    <button
      ref="trigger"
      type="button"
      class="flex h-10 w-10 items-center justify-center rounded-full border border-amber-300 bg-slate-900/80 text-amber-300 hover:bg-slate-800"
      aria-label="User menu"
      :aria-expanded="open"
      @click="open = !open"
    >
      <svg
        viewBox="0 0 24 24"
        class="h-6 w-6"
        fill="currentColor"
        aria-hidden="true"
      >
        <circle cx="12" cy="8" r="4" />
        <path d="M4 21c0-4.4 3.6-8 8-8s8 3.6 8 8z" />
      </svg>
    </button>
    <ul
      v-if="open"
      class="absolute z-20 w-48 overflow-hidden rounded-lg border border-slate-700 bg-slate-900 py-1 shadow-lg"
      :class="dropUp ? 'bottom-12 left-0' : 'right-0 top-12'"
    >
      <li v-for="item in items" :key="item">
        <button
          type="button"
          class="block w-full px-4 py-2 text-left text-sm hover:bg-slate-800"
          @click="select(item)"
        >
          {{ item }}
        </button>
      </li>
    </ul>
    <SignInModal :open="signInOpen" @close="closeSignIn" />
  </div>
</template>
