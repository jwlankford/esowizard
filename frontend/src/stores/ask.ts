import { defineStore } from "pinia";
import { ref } from "vue";
import { askQuestion } from "../services/api";
import type { Answer } from "../types/api";

export const useAskStore = defineStore("ask", () => {
  const result = ref<Answer | null>(null);
  const error = ref("");
  const loading = ref(false);

  async function ask(question: string, category: string | null) {
    loading.value = true;
    error.value = "";
    result.value = null;
    try {
      result.value = await askQuestion(question, category);
    } catch (reason) {
      error.value =
        reason instanceof Error ? reason.message : "Something went wrong.";
    } finally {
      loading.value = false;
    }
  }

  return { result, error, loading, ask };
});
