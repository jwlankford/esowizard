<script setup lang="ts">
import { onMounted, ref } from "vue";
import { getCategories } from "../services/api";
import { useAskStore } from "../stores/ask";

const question = ref("");
const category = ref("");
const categories = ref<string[]>([]);
const categoriesError = ref("");
const store = useAskStore();

onMounted(async () => {
  try {
    categories.value = await getCategories();
  } catch {
    categoriesError.value =
      "Categories are unavailable. Check that the API is running.";
  }
});

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
  <h1 class="text-3xl font-bold">Ask about Tamriel</h1>
  <p class="mt-3 text-slate-300">
    Ask an ESO question and explore answers grounded in the knowledge base.
  </p>
  <form
    class="mt-8 space-y-4"
    @submit.prevent="store.ask(question.trim(), category || null)"
  >
    <label class="block" for="question">Your question</label>
    <textarea
      id="question"
      v-model="question"
      class="w-full rounded-lg border border-slate-700 bg-slate-900 p-3"
      rows="3"
      maxlength="2000"
      required
      placeholder="How do I make Psijic Ambrosia?"
    />
    <label class="block" for="category">Category (optional)</label>
    <select
      id="category"
      v-model="category"
      class="rounded-lg border border-slate-700 bg-slate-900 p-3"
    >
      <option value="">All categories</option>
      <option v-for="item in categories" :key="item" :value="item">
        {{ item }}
      </option>
    </select>
    <p v-if="categoriesError" class="text-amber-300" role="status">
      {{ categoriesError }}
    </p>
    <div>
      <button
        class="rounded-lg bg-amber-300 px-5 py-3 font-semibold text-slate-950 disabled:opacity-50"
        :disabled="store.loading || !question.trim()"
      >
        {{ store.loading ? "Searching…" : "Ask ESO Wizard" }}
      </button>
    </div>
  </form>
  <p v-if="store.error" class="mt-8 text-red-300" role="alert">
    {{ store.error }}
  </p>
  <section v-if="store.result" class="mt-10" aria-live="polite">
    <h2 class="text-xl font-semibold">Answer</h2>
    <p class="mt-3 whitespace-pre-wrap text-slate-200">
      {{ store.result.answer }}
    </p>
    <div v-if="store.result.sources.length" class="mt-8">
      <h3 class="font-semibold">Sources</h3>
      <ol class="mt-3 list-decimal space-y-2 pl-6">
        <li v-for="(source, index) in store.result.sources" :key="index">
          <a
            v-if="safeUrl(source.source_url)"
            :href="safeUrl(source.source_url)"
            target="_blank"
            rel="noopener noreferrer"
            class="text-amber-300 underline"
            >{{ source.title }}</a
          >
          <span v-else>{{ source.title }}</span>
          <span class="text-slate-400"> — {{ source.source_name }}</span>
        </li>
      </ol>
    </div>
  </section>
</template>
