<script setup lang="ts">
import { nextTick, ref, watch } from "vue";

const props = defineProps<{ open: boolean }>();
const emit = defineEmits<{ close: [] }>();

const email = ref("");
const password = ref("");
const emailInput = ref<HTMLInputElement | null>(null);

watch(
  () => props.open,
  async (isOpen) => {
    if (isOpen) {
      await nextTick();
      emailInput.value?.focus();
    } else {
      password.value = "";
    }
  },
);

// Authentication is not implemented yet; these handlers are placeholders.
function signInWithEmail() {
  emit("close");
}

function signInWithProvider() {
  emit("close");
}
</script>

<template>
  <div
    v-if="open"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
    @click.self="emit('close')"
    @keydown.esc="emit('close')"
  >
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="signin-title"
      class="relative w-full max-w-sm rounded-xl border border-slate-700 bg-slate-900 p-6 text-slate-100 shadow-2xl"
    >
      <button
        type="button"
        class="absolute right-3 top-3 text-2xl leading-none text-slate-400 hover:text-slate-100"
        aria-label="Close"
        @click="emit('close')"
      >
        &times;
      </button>
      <h2 id="signin-title" class="text-xl font-semibold">Sign in</h2>

      <form class="mt-5 space-y-4" @submit.prevent="signInWithEmail">
        <div>
          <label class="block text-sm" for="signin-email">Email</label>
          <input
            id="signin-email"
            ref="emailInput"
            v-model="email"
            type="email"
            required
            autocomplete="email"
            class="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 p-2"
          />
        </div>
        <div>
          <label class="block text-sm" for="signin-password">Password</label>
          <input
            id="signin-password"
            v-model="password"
            type="password"
            required
            autocomplete="current-password"
            class="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 p-2"
          />
        </div>
        <button
          class="w-full rounded-lg bg-amber-300 px-4 py-2 font-semibold text-slate-950"
        >
          Sign in
        </button>
      </form>

      <div class="my-5 flex items-center gap-3 text-xs text-slate-400">
        <span class="h-px flex-1 bg-slate-700"></span>
        or
        <span class="h-px flex-1 bg-slate-700"></span>
      </div>

      <div class="space-y-3">
        <button
          type="button"
          class="flex w-full items-center justify-center gap-3 rounded-lg bg-white px-4 py-2 font-medium text-slate-800 hover:bg-slate-100"
          @click="signInWithProvider()"
        >
          <svg viewBox="0 0 48 48" class="h-5 w-5" aria-hidden="true">
            <path
              fill="#EA4335"
              d="M24 9.5c3.5 0 6.6 1.2 9.1 3.6l6.8-6.8C35.8 2.4 30.3 0 24 0 14.6 0 6.5 5.4 2.6 13.2l7.9 6.1C12.4 13.6 17.7 9.5 24 9.5z"
            />
            <path
              fill="#4285F4"
              d="M46.5 24.5c0-1.6-.1-3.1-.4-4.5H24v9h12.7c-.6 3-2.3 5.5-4.8 7.2l7.5 5.8c4.4-4.1 7.1-10.1 7.1-17.5z"
            />
            <path
              fill="#FBBC05"
              d="M10.5 28.7c-.5-1.5-.8-3-.8-4.7s.3-3.2.8-4.7l-7.9-6.1C.9 16.4 0 20.1 0 24s.9 7.6 2.6 10.8l7.9-6.1z"
            />
            <path
              fill="#34A853"
              d="M24 48c6.5 0 11.9-2.1 15.9-5.8l-7.5-5.8c-2.1 1.4-4.9 2.3-8.4 2.3-6.3 0-11.6-4.1-13.5-9.8l-7.9 6.1C6.5 42.6 14.6 48 24 48z"
            />
          </svg>
          Continue with Google
        </button>
        <button
          type="button"
          class="flex w-full items-center justify-center gap-3 rounded-lg bg-[#1877F2] px-4 py-2 font-medium text-white hover:bg-[#166fe0]"
          @click="signInWithProvider()"
        >
          <svg
            viewBox="0 0 24 24"
            class="h-5 w-5"
            fill="currentColor"
            aria-hidden="true"
          >
            <path
              d="M24 12a12 12 0 1 0-13.9 11.9v-8.4H7.1V12h3V9.4c0-3 1.8-4.7 4.5-4.7 1.3 0 2.7.2 2.7.2v3h-1.5c-1.5 0-2 .9-2 1.9V12h3.4l-.5 3.5h-2.9v8.4A12 12 0 0 0 24 12z"
            />
          </svg>
          Continue with Facebook
        </button>
      </div>
    </div>
  </div>
</template>
