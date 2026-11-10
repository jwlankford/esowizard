<script setup lang="ts">
import { nextTick, onMounted, ref, watch } from "vue";
import { getCategories } from "../services/api";
import { useAskStore } from "../stores/ask";

const question = ref("");
const category = ref("");
const categories = ref<string[]>([]);
const categoriesError = ref("");
const store = useAskStore();
const scroller = ref<HTMLElement | null>(null);

onMounted(async () => {
  try {
    categories.value = await getCategories();
  } catch {
    categoriesError.value =
      "Categories are unavailable. Check that the API is running.";
  }
});

watch(
  () => [store.active?.messages.length, store.loading, store.activeId],
  async () => {
    await nextTick();
    scroller.value?.scrollTo({ top: scroller.value.scrollHeight });
  },
);

function submit() {
  const text = question.value.trim();
  if (!text || store.loading) return;
  question.value = "";
  void store.ask(text, category.value || null);
}

function onEnter(event: KeyboardEvent) {
  if (event.shiftKey) {
    question.value += "\n";
  } else if (!event.isComposing) {
    submit();
  }
}

function safeUrl(url: string): string | undefined {
  try {
    const parsed = new URL(url);
    return ["http:", "https:"].includes(parsed.protocol)
      ? parsed.href
      : undefined;
  } catch {
    return undefined;
  }
}
</script>

<template>
  <div class="flex min-h-0 flex-1 flex-col">
    <div ref="scroller" class="flex-1 overflow-y-auto px-4" aria-live="polite">
      <div class="mx-auto max-w-3xl space-y-6 py-6">
        <div
          v-if="!store.active"
          class="mt-24 rounded-2xl bg-slate-950/70 p-8 text-center backdrop-blur"
        >
          <h1 class="text-3xl font-bold">Ask about Tamriel</h1>
          <p class="mt-3 text-slate-300">
            Ask an ESO question and explore answers grounded in the knowledge
            base.
          </p>
        </div>
        <template v-else>
          <div
            v-for="message in store.active.messages"
            :key="message.id"
            class="flex"
            :class="message.role === 'user' ? 'justify-end' : 'justify-start'"
          >
            <div
              class="max-w-[85%] rounded-2xl px-4 py-3 backdrop-blur"
              :class="
                message.role === 'user'
                  ? 'bg-amber-300 text-slate-950'
                  : message.isError
                    ? 'bg-slate-950/80 text-red-300'
                    : 'bg-slate-950/80 text-slate-100'
              "
              :role="message.isError ? 'alert' : undefined"
            >
              <p class="whitespace-pre-wrap">{{ message.content }}</p>
              <div v-if="message.sources?.length" class="mt-4">
                <h3 class="text-sm font-semibold">Sources</h3>
                <ol class="mt-2 list-decimal space-y-1 pl-5 text-sm">
                  <li v-for="(source, index) in message.sources" :key="index">
                    <a
                      v-if="safeUrl(source.source_url)"
                      :href="safeUrl(source.source_url)"
                      target="_blank"
                      rel="noopener noreferrer"
                      class="text-amber-300 underline"
                      >{{ source.title }}</a
                    >
                    <span v-else>{{ source.title }}</span>
                    <span class="text-slate-400">
                      — {{ source.source_name }}</span
                    >
                  </li>
                </ol>
              </div>
            </div>
          </div>
          <div v-if="store.loading" class="flex">
            <div class="rounded-2xl bg-slate-950/80 px-4 py-3 text-slate-300">
              Searching…
            </div>
          </div>
        </template>
      </div>
    </div>

    <form class="px-4 pb-4" @submit.prevent="submit">
      <div
        class="mx-auto max-w-3xl rounded-2xl border border-slate-700 bg-slate-950/90 p-3 backdrop-blur"
      >
        <label class="sr-only" for="question">Your question</label>
        <textarea
          id="question"
          v-model="question"
          class="w-full resize-none bg-transparent p-1 outline-none"
          rows="2"
          maxlength="2000"
          placeholder="How do I make Psijic Ambrosia?"
          @keydown.enter.prevent="onEnter"
        />
        <div class="mt-2 flex items-center justify-between gap-3">
          <div class="flex items-center gap-2">
            <label class="sr-only" for="category">Category (optional)</label>
            <select
              id="category"
              v-model="category"
              class="rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 text-sm"
            >
              <option value="">All categories</option>
              <option v-for="item in categories" :key="item" :value="item">
                {{ item }}
              </option>
            </select>
            <span
              v-if="categoriesError"
              class="text-xs text-amber-300"
              role="status"
            >
              {{ categoriesError }}
            </span>
          </div>
          <button
            class="rounded-lg bg-amber-300 px-4 py-2 font-semibold text-slate-950 disabled:opacity-50"
            :disabled="store.loading || !question.trim()"
          >
            {{ store.loading ? "Searching…" : "Send" }}
          </button>
        </div>
      </div>
    </form>
  </div>
</template>
